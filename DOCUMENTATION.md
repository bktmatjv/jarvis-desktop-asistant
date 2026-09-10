# Documentación Técnica de JARVIS v2.5.0

Esta documentación explica las entrañas del sistema y la arquitectura asíncrona modular sobre la que está construido.

---

## 1. Topología del Sistema

JARVIS es un sistema desacoplado. El cerebro (razonamiento y enrutamiento) está separado de los brazos/ojos (entorno cliente/desktop).

- **El Backend (Cerebro):** Impulsado por `FastAPI`. Tiene conexión constante con `MongoDB` para la retención histórica de conversaciones. Incorpora servicios modulares (`skill_service`, `router_service`, `llm_service`) para delegar lógicas complejas sin inflar el enrutador principal de WebSockets.
- **El Cliente (Cuerpo):** Interfaz en Python usando `PyWebView` con dos ventanas simultáneas (HUD Panel + Orbe 3D). Escucha al usuario mediante el motor de reconocimiento local (`Vosk` a través de `wake_word.py`) y transcribe con `stt_engine.py` (Groq Whisper). Ejecuta Skills locales delegadas por el Backend.

---

## 2. Loop Engineering — Pipeline de Procesamiento

El flujo completo de un mensaje del usuario pasa por estas etapas:

```
Usuario habla
     │
     ▼
[Wake Word — Vosk] ──► Despierta el Orbe
     │
     ▼
[STT — Groq Whisper] ──► Texto transcrito
     │
     ▼
[WebSocket ──► Backend]
     │
     ├─ 1. INGESTION:  Prompt recibido y verificado
     ├─ 2. ROUTER:     gpt-oss-20b clasifica dominio (<300ms) + stalling phrase
     ├─ 3. PRUNING:    Context Pruner filtra solo skills del dominio
     ├─ 4a. FAST PATH: Si domain="chat" → stream directo sin tools
     │   └─ 4b. REASONING: Si domain!="chat" → qwen3.6-27b con tools
     ├─ 5. SKILL RUNNER: Ejecuta skill en cliente o backend
     └─ 6. SYNTHESIZER: TTS (pyttsx3) + render HUD
```

El HUD muestra este pipeline en tiempo real mediante `loopVisualizer.js`.

---

## 3. Segregación de API Keys (Anti Rate-Limit)

Para evitar interrupciones por límites de cuota de Groq, el sistema usa **tres pools de claves separados**:

| Variable | Uso |
| :--- | :--- |
| `GROQ_API_KEYS_VOICE` | Transcripción STT con Groq Whisper |
| `GROQ_API_KEYS_FAST` | Router de intenciones + respuestas conversacionales |
| `GROQ_API_KEYS_REASONING` | Razonamiento complejo y Tool Calling |
| `GROQ_API_KEYS` | Pool de fallback global |

Cada pool rota automáticamente sus claves ante un error HTTP 429.

---

## 4. Ejecución de Skills (Tool Calling)

Cuando el LLM decide ejecutar una acción, el flujo es:
1. El Reasoning model (`qwen3.6-27b`) emite un `tool_call` con nombre de skill y parámetros JSON.
2. El Backend (`chat.py`) serializa la llamada como un `ToolCallResponse` y la envía al cliente vía WebSocket.
3. El Cliente (`executor.py`) recibe la acción, valida su seguridad y lanza el script de la skill como subproceso.
4. El script lee sus parámetros de un archivo JSON temporal y devuelve el resultado por `stdout`.
5. El resultado se retorna al backend como `tool_result` para que el LLM genere la respuesta final.

**Capa OS:** Cada skill detecta automáticamente el sistema operativo y usa las APIs nativas correspondientes (pycaw/amixer para volumen, pywinauto/wmctrl para ventanas, etc.).

---

## 5. Autonomía Proactiva (APScheduler)

JARVIS cuenta con autonomía proactiva mediante la integración de `APScheduler` y el módulo `ConnectionManager`, lo que permite al servidor iniciar comunicaciones (Push messages) sin que el usuario lo solicite.

Al solicitar la calendarización de una tarea, el sistema registra el evento en el `AsyncIOScheduler`. Una vez expira el tiempo, el proceso secundario envía un payload al cliente vía WebSocket que renderiza alertas visuales en el HUD.

---

## 6. Interceptor de Seguridad de Ejecución

Como salvaguarda ante operaciones destructivas generadas por el LLM, el cliente evalúa todos los comandos del sistema contra una lista heurística de operaciones de alto riesgo. Si se detecta una coincidencia, el hilo de ejecución se pausa y renderiza un modal en el HUD solicitando autorización explícita humana.

Palabras bloqueadas por defecto: `rm -rf`, `chmod`, `chown`, `mkfs`, `dd`, `mkpasswd`, `passwd`.

---

## 7. Estructura de Directorios (v2.5.0)

```
jarvis/
├── backend/
│   ├── app/
│   │   ├── api/websockets/chat.py      # Gestor WS, Loop Engineering pipeline
│   │   ├── core/
│   │   │   ├── config.py               # Variables de entorno y pools de API keys
│   │   │   └── logger.py               # Logger centralizado
│   │   ├── models/schemas.py           # Modelos Pydantic (Handshake, Speak, ToolCall...)
│   │   └── services/
│   │       ├── connection_manager.py   # Registro de WebSockets activos
│   │       ├── llm_service.py          # Groq Dual-Model (Fast + Reasoning)
│   │       ├── memory_service.py       # MongoDB Chat History
│   │       ├── router_service.py       # Clasificador de intenciones (<300ms)
│   │       ├── skill_service.py        # Carga y filtrado de Skills por dominio
│   │       └── scheduler_service.py    # APScheduler — Autonomía proactiva
│   ├── skills/                         # Skills ejecutadas en el servidor
│   │   ├── math_skill/
│   │   ├── web_fetch/
│   │   └── web_search/
│   ├── clean_db.py                     # Utilidad para limpiar el historial de MongoDB
│   └── requirements.txt
├── client/
│   ├── executor/executor.py            # Validador, interceptor y despachador de Skills
│   ├── memory/                         # Caché local del OS (ignorado en Git)
│   ├── model/                          # Modelo Vosk offline (ignorado en Git)
│   ├── skills/                         # Skills ejecutadas en el cliente
│   │   ├── input_controller/           # Simulación de teclado, mouse y atajos
│   │   ├── media_control/              # Control multimedia (play/pause/next/vol)
│   │   ├── play_ytmusic/               # Búsqueda y reproducción en YouTube Music
│   │   ├── system_control/             # Open app, volumen, shutdown/restart/lock
│   │   ├── system_telemetry/           # CPU, RAM, batería, procesos, screenshot
│   │   └── window_manager/             # Listar/enfocar/minimizar/cerrar ventanas
│   ├── web/                            # Panel de Control (Vanilla HTML/JS/CSS)
│   │   ├── animation/                  # Animación cinemática de boot (GSAP + Canvas)
│   │   ├── index.html
│   │   ├── script.js
│   │   ├── styles.css
│   │   ├── loopVisualizer.js           # Visualizador del pipeline en tiempo real
│   │   └── navigation.js              # Navegación horizontal entre slides
│   ├── frontend/                       # Orbe 3D flotante (React + Three.js)
│   │   ├── dist/                       # Bundle compilado — no requiere Node.js para ejecutar
│   │   └── src/                        # Código fuente (para modificar el Orbe)
│   ├── connection.py                   # Motor WebSocket cliente
│   ├── download_model.py               # Descarga el modelo Vosk para Wake Word
│   ├── main.py                         # UI, atajos globales y PyWebView container
│   ├── repl.py                         # Terminal asíncrono (PowerShell/Bash)
│   ├── stt_engine.py                   # Speech-to-Text (Groq Whisper)
│   ├── voice_engine.py                 # TTS local (pyttsx3 con streaming por oraciones)
│   ├── wake_word.py                    # Wake Word offline (Vosk + sounddevice)
│   └── requirements.txt
├── .env.example                        # Plantilla de variables de entorno
├── .gitignore
├── DATABASE_DESIGN.md                  # Diseño de datos y modelo multidispositivo
├── DOCUMENTATION.md                    # Este archivo
├── README.md
├── setup_env.bat                       # Instalador automático (Windows)
└── start_jarvis.bat                    # Launcher de 1 clic (Windows)
```
