# JARVIS — Guía de Ingeniería & Preguntas de Entrevista

Este documento cubre en profundidad cada decisión de ingeniería tomada durante el desarrollo de JARVIS, con referencias directas al código. Está estructurado para preparar una validación técnica.

---

## 1. Arquitectura General: Por qué Cliente-Servidor

### La Decisión
JARVIS está dividido en un **Backend FastAPI** (Python) y un **Cliente PyWebView** (Python + JS), comunicados en tiempo real por **WebSocket**.

### Por Qué Se Tomó Esta Decisión

El asistente necesita acceso a dos dominios que no pueden compartir un solo proceso con seguridad:

1. **El Backend** necesita conexión a internet, acceso a la API de Groq (LLM), MongoDB, y puede correr en cualquier máquina o servidor. No debe tener acceso directo al sistema operativo del usuario.
2. **El Cliente** necesita acceso directo al OS del usuario (controlar ventanas, simular teclado, ejecutar procesos, medir CPU/RAM). Si el LLM cometiera un error, los daños quedan acotados al cliente, no al servidor.

Esta separación respeta el **principio de mínimo privilegio**: el servidor no puede abrir aplicaciones, y el cliente no puede hacer peticiones a las APIs directamente.

> **Referencia directa:** `backend/app/api/websockets/chat.py` orquesta el flujo del servidor. `client/connection.py` maneja la conexión desde el cliente.

---

## 2. WebSocket: Por Qué No HTTP/REST

### La Decisión
La comunicación se hace exclusivamente por **WebSocket persistente**, no por REST.

### Por Qué

Un flujo conversacional con herramientas tiene múltiples intercambios asincrónicos en una sola "conversación":

```
User → Server  (mensaje de usuario)
Server → Client (ThinkingResponse — stalling phrase)
Server → Client (ToolCallResponse — "ejecuta esta skill")
Client → Server (ToolResultRequest — resultado de la skill)
Server → Client (SpeakResponse — respuesta final)
```

Con HTTP/REST, cada uno de esos intercambios requeriría una petición nueva, con el overhead de establecer conexión, cabeceras y autenticación. El WebSocket es una **conexión TCP persistente** — el canal ya está abierto y cualquiera de los dos extremos puede escribir en cualquier momento sin pedir permiso.

Esto además permite **Server Push** (proactividad): el `scheduler_service.py` puede enviar una notificación de recordatorio al cliente sin que el usuario haya preguntado nada.

> **Referencia directa:** `backend/app/services/connection_manager.py` líneas 26-30 — `send_personal_message()` hace un push directo al WebSocket de un cliente registrado.

---

## 3. El Protocolo de Mensajes: Typed Discriminated Union

### La Decisión
Todos los mensajes WebSocket siguen un **protocolo tipado** basado en Pydantic. Cada mensaje tiene un campo `type` que actúa como discriminador.

```python
class SpeakResponse(BaseModel):
    type: Literal["speak"] = "speak"
    message: str

class ThinkingResponse(BaseModel):
    type: Literal["thinking"] = "thinking"
    message: str

class ToolCallResponse(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    tool_call_id: str
    ...
```

### Por Qué

Tanto el cliente (`executor.py`) como el servidor hacen un `data.get("type")` y ramifican con `if/elif`. Esto implementa el patrón de diseño **Command** — cada tipo de mensaje es un comando auto-descriptivo con todos sus datos encapsulados. La ventaja es que **agregar un nuevo tipo de mensaje no rompe ningún código existente** (los `elif` que no coincidan simplemente no se ejecutan).

Pydantic valida automáticamente que los campos obligatorios existan y tengan el tipo correcto, y genera el JSON serializado con un solo `.model_dump_json()`.

> **Referencia directa:** `backend/app/models/schemas.py` — define todo el protocolo.

---

## 4. Loop Engineering: Arquitectura Dual-Model

### La Decisión
En lugar de usar un solo LLM para todo, JARVIS usa **dos modelos con roles diferentes** que trabajan en paralelo:

| Modelo | Rol | Tiempo |
| :--- | :--- | :--- |
| `groq/compound-mini` | **Fast Router** — Clasifica intención y genera stalling phrase | < 300 ms |
| `qwen/qwen3.6-27b` | **Reasoning Model** — Razonamiento complejo y Tool Calling | 2–8 s |

### Por Qué — El Problema de la Latencia Percibida

Un LLM grande tarda 3-8 segundos en responder. Si el usuario pregunta "pon la canción de Spotify" y el sistema tarda 6 segundos en silencio, la experiencia parece rota.

La solución es:
1. El Fast Router detecta en < 300ms que es una acción de media, genera la frase `"De acuerdo, buscando la canción..."` y la envía al cliente como `ThinkingResponse`.
2. El cliente habla esa frase por TTS **inmediatamente**, tapando perceptualmente el silencio.
3. Mientras el usuario escucha la frase de stalling, el Reasoning Model trabaja en background con `asyncio.create_task()`.

```python
# chat.py — exactamente así funciona el branching
if intent == "chat":
    await _stream_fast_and_save(...)   # Nodo 2A: respuesta rápida directa
else:
    if stalling_phrase:
        await websocket.send_text(ThinkingResponse(message=stalling_phrase).model_dump_json())
    asyncio.create_task(               # Nodo 4: background, no bloquea
        _run_reasoning_and_respond(...)
    )
```

> **Término de ingeniería:** Este patrón se llama **Optimistic UI** o **Speculative Execution** aplicado a pipelines de IA.

---

## 5. Context Pruner: Gestión de Tokens

### La Decisión
Antes de llamar al Reasoning Model, el sistema filtra las herramientas disponibles según el dominio clasificado. No le pasa las 15+ herramientas — solo las 3-5 relevantes.

```python
DOMAIN_SKILL_MAP = {
    "system": ["system_control", "window_manager", "system_telemetry", "input_controller", "execute_command"],
    "research": ["web_search", "web_fetch", "search_memory", "save_memory"],
    "media": ["play_ytmusic", "media_control", "system_control"],
    "chat": []  # Sin herramientas — respuesta directa
}
```

### Por Qué

Groq tiene **límites de tokens por minuto (TPM)** muy estrictos en sus endpoints de inferencia gratuita. Cada definición de herramienta en formato OpenAI Tool Calling ocupa 100-300 tokens. Con 15 skills, el prompt puede superar el límite de 6,000 tokens antes de añadir el historial o el prompt de sistema.

El Context Pruner reduce el uso de tokens en **≈ 84%** (como aparece en el HUD: `sub: "-84% Tokens"`). Esto permite al sistema funcionar con claves de Groq gratuitas sin alcanzar el límite.

> **Referencia directa:** `backend/app/services/skill_service.py` líneas 60-103 — `get_tools_for_domain()`.

---

## 6. Circuit Breaker: Protección Contra Tool Loops

### La Decisión
`_check_tool_loop()` en `llm_service.py` detecta cuando el modelo lleva >= 4 llamadas a herramientas consecutivas sin hablar al usuario, e inyecta una instrucción de sistema para forzarlo a responder.

```python
def _check_tool_loop(session_history: list) -> bool:
    consecutive = 0
    for msg in reversed(session_history):
        if msg.get("role") == "tool" or (
            msg.get("role") == "assistant" and msg.get("tool_calls")
        ):
            consecutive += 1
        elif msg.get("role") == "user":
            break
    return consecutive >= 4
```

### Por Qué

Los LLMs pueden entrar en **loops de Tool Calling**: el modelo llama a una herramienta, lee el resultado, llama a otra herramienta, y así indefinidamente sin generar una respuesta para el usuario. Esto agota cuota de API y bloquea el WebSocket. El circuit breaker rompe el ciclo preventivamente.

> **Término de ingeniería:** Patrón **Circuit Breaker** del libro "Release It!" de Michael Nygard, adaptado a pipelines de LLM.

---

## 7. Sistema de Skills: Plugin Architecture

### La Decisión
Cada capacidad de acción de JARVIS está empaquetada como una **Skill independiente**: un directorio con un `skill.json` (manifiesto) y un `main.py` (implementación). Se cargan dinámicamente en tiempo de ejecución.

```
client/skills/system_control/
    ├── skill.json    <- Manifiesto: nombre, descripción, parámetros (formato OpenAI Tool)
    └── main.py       <- Implementación: lee parámetros de un JSON temp, escribe en stdout
```

### El Flujo de Ejecución

```
1. Backend lee todos los skill.json al arrancar.
2. Los convierte en Tool Definitions (formato OpenAI) y los pasa al LLM.
3. El LLM devuelve un tool_call con nombre de skill y parámetros JSON.
4. El Backend serializa como ToolCallResponse y lo manda al Cliente por WS.
5. El Cliente (executor.py) escribe los parámetros en un archivo JSON temporal.
6. El Cliente lanza el script como subproceso aislado con asyncio.create_subprocess_exec().
7. El script lee el JSON, ejecuta la acción de OS, imprime el resultado en stdout.
8. El Cliente devuelve el stdout al Backend como ToolResultRequest.
```

### Por Qué Este Diseño

- **Aislamiento:** Si una skill falla o cuelga, el proceso muere sin afectar el proceso principal del cliente.
- **Extensibilidad:** Añadir una nueva capacidad = crear un directorio con 2 archivos. No requiere modificar el código del cliente ni del servidor.
- **OS-Agnostic:** Cada skill puede detectar el SO y usar las APIs nativas correctas (pycaw en Windows, amixer en Linux).
- **Seguridad:** El script nunca recibe un string de código arbitrario; recibe parámetros validados en JSON.

> **Término de ingeniería:** Patrón **Plugin / Extension Points** similar al sistema de plugins de VS Code o Pytest.

> **Referencia directa:** `client/executor/executor.py` líneas 120-186 — `execute_skill` con `asyncio.create_subprocess_exec`.

---

## 8. Memoria: Sliding Window Context

### La Decisión
El historial de conversación se persiste en **MongoDB** con `motor` (driver async). Al construir el prompt del LLM, solo se inyectan los últimos **6-10 mensajes** (configurable), no toda la historia.

```python
async def get_recent_history(session_id: str, limit: int = 10) -> list:
    session = await sessions_collection.find_one({"session_id": session_id})
    messages = session["messages"]
    return messages[-limit:] if limit > 0 else messages  # Sliding Window
```

### Por Qué

Los LLMs tienen un **context window** limitado (tokens). Si persistieras e inyectaras toda la historia de una conversación de un mes, superarías el límite del modelo. La ventana deslizante simula "memoria de corto plazo" — el modelo recuerda las últimas interacciones sin saturar el contexto.

MongoDB con `$push` + `upsert: True` garantiza que la sesión se crea automáticamente si no existe, y que los mensajes se acumulan en un array con un único documento por sesión.

> **Término de ingeniería:** Patrón **Sliding Window Context** para gestión de tokens en LLMs.

---

## 9. Anti Rate-Limit: Key Rotation Pool

### La Decisión
Las API Keys de Groq están segregadas en tres pools (Voice, Fast, Reasoning). Ante un error HTTP 429, el sistema rota a la siguiente clave del pool sin interrumpir la conversación.

```python
for attempt in range(len(reasoning_clients)):
    groq_client = _get_next_reasoning_client()
    try:
        response = await groq_client.chat.completions.create(...)
        return parse_llm_response(response_message, dynamic_skills)
    except RateLimitError:
        _rotate_reasoning_client()   # Rotación atómica
        await asyncio.sleep(0.5)
        continue
```

### Por Qué

Groq Free Tier tiene límites por key (~30 RPM, ~6,000 TPM). Un asistente de uso intensivo alcanzaría ese límite en minutos. Al tener N keys rotativas, el límite efectivo es N × 6,000 TPM. La segregación por rol (Voice/Fast/Reasoning) evita que las peticiones de transcripción compitan con las de razonamiento.

> **Término de ingeniería:** Patrón **Round-Robin Load Balancing** aplicado a pools de API Keys.

---

## 10. Wake Word: Motor Offline con Vocabulario Restringido

### La Decisión
El sistema usa **Vosk** con un `KaldiRecognizer` configurado con un **vocabulario de 4 palabras** (`["jarvis", "yarvis", "harvis", "[unk]"]`), corriendo en un **thread daemon** separado del proceso principal.

```python
recognizer = KaldiRecognizer(model, 16000, '["jarvis", "yarvis", "harvis", "[unk]"]')
```

### Por Qué

- **Offline:** No envía audio a ningún servidor externo. El modelo Vosk corre localmente.
- **Vocabulario restringido:** Cuando el recognizer tiene un vocabulario pequeño, el modelo ASR tiene menos candidatos que evaluar por cada frame de audio — menor CPU y mayor precisión.
- **Thread daemon:** Corre indefinidamente en background sin bloquear el event loop de asyncio. Se destruye automáticamente cuando el proceso principal termina.
- **Anti-doble disparo:** Después de detectar la wake word, limpia la cola de audio (`_q.queue.clear()`) para evitar que el ruido residual active el sistema dos veces.

> **Término de ingeniería:** **Keyword Spotting** con **Restricted Grammar** en ASR.

---

## 11. REPL Asíncrono: Ejecución de Comandos sin Bloquear

### La Decisión
El cliente usa `asyncio.create_subprocess_exec()` para ejecutar comandos de terminal. No usa `subprocess.run()`.

### Por Qué

`subprocess.run()` es **bloqueante** — congela el event loop de asyncio mientras el proceso corre, impidiendo que lleguen nuevos mensajes del servidor. `asyncio.create_subprocess_exec()` + `await process.communicate()` libera el event loop mientras el proceso trabaja, permitiendo que el sistema reciba mensajes de status o cancelación en paralelo.

---

## 12. Interceptor de Seguridad: asyncio.Event como Semáforo

### La Decisión
Ante un comando peligroso, el `executor.py` pausa el flujo de ejecución usando `asyncio.Event.wait()` y muestra un modal en el HUD. La ejecución no continúa hasta que el usuario haga clic en "Permitir" o "Denegar".

```python
security_event.clear()
main.panel_window.evaluate_js(f"showSecurityAlert('{safe_cmd}')")
await security_event.wait()   # El event loop NO se bloquea, sigue procesando

if not security_allowed:
    return {"type": "tool_result", "error": "Execution denied by user."}
```

Cuando el usuario hace clic en el modal JS, PyWebView llama a `pywebview.api.security_response(is_allowed)`, que ejecuta `ws_loop.call_soon_threadsafe(resolve_security, is_allowed)`, liberando el `await`.

### Por Qué

Un `threading.Event.wait()` **bloquearía el event loop** de asyncio. `asyncio.Event.wait()` es una **coroutine** — suspende solo esa tarea mientras el event loop sigue respondiendo. La sincronización entre el thread de PyWebView y el event loop de asyncio se hace con `call_soon_threadsafe()` — único método thread-safe de asyncio para planificar una llamada desde fuera del event loop.

> **Término de ingeniería:** Patrón **Producer-Consumer** con `asyncio.Event` como señal de sincronización cross-thread.

---

## 13. El Orbe 3D: GLSL Shader Custom + Fresnel Effect

### La Decisión
El Orbe flotante usa un **shader GLSL custom** en lugar de materiales estándar de Three.js. Implementa:

1. **Simplex 3D Noise** en el vertex shader para deformar la superficie.
2. **Efecto Fresnel** en el fragment shader para crear el brillo en los bordes.
3. **Estados reactivos** (sleep / awake / listening) que interpolan parámetros de shader vía `lerp()` en cada frame.

```glsl
// Fragment Shader — Efecto Fresnel
float fresnel = pow(1.0 - abs(dot(vNormal, vViewDir)), uFresnelPower);
vec3 color = mix(uColorCore, uColorRim, fresnel);
```

### Por Qué

El efecto Fresnel simula cómo los materiales translúcidos reales (vidrio, agua) tienen mayor reflectancia en los bordes que en el centro. Para una esfera holográfica, el borde brillante y el centro transparente son exactamente el aspecto correcto. No hay ningún material estándar de Three.js que lo logre con esa precisión.

**`premultipliedAlpha: false`** en el Canvas de R3F es una decisión de compatibilidad crítica: PyWebView usa Edge WebView2 (Chromium), cuyo compositor de ventanas transparentes (DWM) interpreta incorrectamente el alpha premultiplicado del WebGL, produciendo bordes negros. Con `false`, el alpha se propaga correctamente al compositor de Windows.

---

## 14. PyWebView: Ventana Frameless Dual

### La Decisión
El cliente lanza **dos ventanas independientes** de PyWebView: el Panel de Control (HUD HTML/JS) y el Orbe 3D (React/Three.js). Ambas son frameless (sin barra de título) y transparentes.

### Por Qué

- **Dos ventanas separadas** permite que el Orbe flote sobre cualquier otra ventana mientras el Panel puede estar minimizado. Con una sola ventana no sería posible posicionarlos independientemente.
- **Frameless + transparente** elimina los bordes del OS, esencial para el aspecto holográfico.
- **`evaluate_js()`** de PyWebView actúa como puente entre Python y el DOM, permitiendo que el backend Python actualice el HUD en tiempo real sin recargar la página.

---

## 15. Preguntas de Entrevista y Cómo Responderlas

### "¿Por qué usas WebSocket y no Server-Sent Events (SSE)?"

SSE es unidireccional (servidor → cliente). En JARVIS, el cliente necesita enviar resultados de herramientas **de vuelta al servidor** (`ToolResultRequest`). WebSocket es bidireccional por diseño. SSE habría requerido un canal REST adicional para las respuestas del cliente, complicando el sistema innecesariamente.

### "¿Cómo escala este sistema si hay múltiples usuarios simultáneos?"

El `ConnectionManager` mantiene un registro `dict[session_id → WebSocket]`. Cada usuario tiene su propia sesión aislada con su propio historial en MongoDB. El servidor puede manejar múltiples conexiones porque todo el procesamiento es `async/await` — una petición lenta (reasoning model tarda 5s) no bloquea a los demás usuarios.

Para escalar horizontalmente (múltiples instancias del backend), se reemplazaría el `dict` en memoria por un **pub/sub distribuido** (Redis Pub/Sub) para que los push events del scheduler lleguen al cliente aunque esté conectado a una instancia diferente.

### "¿Cómo manejas los errores del LLM sin que el sistema se caiga?"

Tres capas de resiliencia:
1. **Key Rotation** ante 429 — transparente para el usuario.
2. **Circuit Breaker** ante tool loops — inyecta instrucción de ruptura.
3. **Try/except** global en `process_message()` con `SpeakResponse` de error para que el usuario siempre reciba feedback.

### "¿Por qué el ejecutor de skills corre como subproceso y no importa el módulo directamente?"

**Aislamiento de fallos.** Si una skill tiene un bug que causa una excepción no capturada, un `import` directo podría corromper el estado del proceso cliente. Como subproceso separado, el crash no afecta al proceso principal y el `ToolResultRequest` devuelve el error como texto. Además, el subproceso puede tener sus propias dependencias (pycaw, pywinauto) sin contaminar el entorno del cliente.

### "¿Qué es el efecto Fresnel y cómo lo implementaste?"

El efecto Fresnel describe cómo la reflectancia de un material aumenta cuando el ángulo de incidencia es rasante (cerca de los bordes). En el shader: `pow(1.0 - abs(dot(vNormal, vViewDir)), fresnelPower)` — el `dot` entre la normal y el vector de vista es 0 en los bordes (perpendicular al punto de vista) y 1 en el centro. Invertido y elevado a una potencia, da 1 en bordes y 0 en el centro. Se usa para mezclar el color del borde con el del núcleo.

### "¿Por qué MongoDB y no una base de datos relacional?"

El historial de conversación es naturalmente un documento JSON con un array de mensajes. En una DB relacional necesitaría una tabla `sessions` y una tabla `messages` con un JOIN para reconstruirla — dos operaciones para leer una sesión. Con MongoDB, toda la sesión es un solo documento con `$push` para añadir mensajes. La escritura es atómica a nivel de documento. El esquema puede evolucionar sin migraciones.

### "¿Cuál fue el mayor reto técnico del proyecto?"

La sincronización entre el event loop de asyncio y el thread de la UI de PyWebView. PyWebView ejecuta la ventana en su propio thread; cuando el usuario hace clic en el modal de seguridad, el callback llega en ese thread. Para notificar al event loop de asyncio sin race conditions, se usa `ws_loop.call_soon_threadsafe(resolve_security, is_allowed)` — único método thread-safe de asyncio para planificar una llamada desde fuera del event loop.

### "¿Cómo garantizas que no hay información personal expuesta en el repositorio?"

Mediante tres capas:
1. **`.gitignore`** con `.cache*` bloquea los tokens de Spotify/OAuth que Spotipy guarda en disco.
2. **`git rm --cached`** desvincula archivos del índice de Git retroactivamente sin borrar el archivo físico.
3. **Variables de entorno** vía `pydantic-settings` con `.env` ignorado en Git. Los valores por defecto en el código son genéricos — sin datos personales hardcodeados.

---

## 16. Stack Tecnológico Resumido

| Capa | Tecnología | Por Qué |
| :--- | :--- | :--- |
| Backend Web | FastAPI + Uvicorn | ASGI async, soporte nativo WebSocket |
| LLM | Groq Cloud (compound-mini + qwen3.6-27b) | Inferencia rápida, API OpenAI-compatible |
| DB | MongoDB + Motor (async) | Documento flexible, driver async nativo |
| Scheduler | APScheduler (AsyncIOScheduler) | Se integra directamente en el event loop de asyncio |
| Config | Pydantic-Settings | Validación tipada de env vars + carga de .env |
| Cliente UI | PyWebView | Ventana nativa desktop con renderer web (Chromium/WKWebView) |
| Frontend Panel | HTML + Vanilla CSS + JS | Sin framework = bundle cero, carga instantánea |
| Frontend Orbe | React + Three.js (R3F) + GLSL | Gráficos 3D en el navegador, separado del Panel |
| Wake Word | Vosk (offline) + sounddevice | No requiere internet, vocabulario restringido = baja latencia |
| STT | Groq Whisper (large-v3-turbo) | Alta precisión, baja latencia (< 1s) |
| TTS | pyttsx3 | Offline, cero latencia, funciona sin internet |
| Skills | Python + subprocess | Aislado, extensible, OS-agnostic |
