# Documentación Técnica de JARVIS

Esta documentación explica las entrañas del sistema y la arquitectura asíncrona modular sobre la que está construido.

## 1. Topología del Sistema
JARVIS es un sistema desacoplado. El cerebro (razonamiento y enrutamiento) está separado de los brazos/ojos (entorno cliente/desktop).

- **El Backend (Cerebro):** Impulsado por `FastAPI`. Tiene conexión constante con `MongoDB` para la retención histórica de conversaciones y herramientas ejecutadas (Tool Calls). Incorpora servicios modulares (`voice_service`, `skill_service`, `router_service`) para delegar lógicas complejas sin inflar el enrutador principal de WebSockets.
- **El Cliente (Cuerpo):** Interfaz en Python usando `PyWebView`. Escucha al usuario mediante el motor de reconocimiento local (`Vosk` a través de `wake_word.py` y `stt_engine.py`) y transmite texto al backend. También ejecuta scripts seguros (Herramientas OS) que el backend instruye.

## 2. Ejecución de Comandos (Tool Calling y Abstracción de OS)

Para garantizar compatibilidad entre sistemas, las Herramientas Locales en el cliente se han modularizado.

Cuando el usuario pide una acción local (ej. "sube el volumen" o "abre la consola"), el flujo es:
1. El Cliente capta el audio (STT) y envía el string al Backend.
2. El Backend consulta al LLM con las definiciones de herramientas (`tools schema`).
3. El LLM responde con una llamada a la herramienta `system_media_control` o similar.
4. El Backend instruye al Cliente ejecutar la herramienta pasándole parámetros neutros.
5. **Capa OS:** El Cliente determina en qué OS está corriendo (`sys.platform`) y delega la ejecución al módulo correspondiente dentro de `client/tools/system/`.
   - *En Linux:* Usaría ALSA o PulseAudio.
   - *En Windows:* Usaría pycaw / NirCmd.
6. El Cliente devuelve el `STDOUT` de la ejecución al Backend para que el LLM lo procese.

## 3. Autonomía y Proactividad (APScheduler)
JARVIS cuenta con autonomía proactiva mediante la integración de `APScheduler` y el módulo `ConnectionManager`, lo que permite al servidor iniciar comunicaciones (Push messages).
Al solicitar la calendarización de una tarea, el sistema registra el evento en el `AsyncIOScheduler`. Una vez expira el tiempo, el proceso secundario envía un payload al cliente vía WebSocket que renderiza alertas visuales en el HUD.

## 4. Estructura de Directorios (v2.1)

```
jarvis/
├── backend/
│   ├── app/
│   │   ├── api/websockets/chat.py      # Gestor WS y delegación al LLM
│   │   ├── core/config.py              # Variables de entorno y DB config
│   │   ├── models/schemas.py           # Modelos Pydantic para APIs
│   │   ├── services/
│   │   │   ├── connection_manager.py   # Registro de WS
│   │   │   ├── llm_service.py          # Groq LLM logic y Rate Limits
│   │   │   ├── memory_service.py       # MongoDB Chat History
│   │   │   ├── router_service.py       # Orquestador del Agentic Loop
│   │   │   ├── skill_service.py        # Gestión de Habilidades Remotas
│   │   │   ├── voice_service.py        # Síntesis TTS y procesado
│   │   │   └── scheduler_service.py    # APScheduler Background tasks
│   │   └── main.py                     # Entry point (Uvicorn)
│   └── skills/                         # Módulos LLM enchufables al Backend
├── client/
│   ├── memory/                         # Archivos de caché del SO local (ignorados en Git)
│   ├── model/                          # Modelo Vosk descargado localmente
│   ├── tools/
│   │   ├── system/
│   │   │   ├── linux/                  # Operaciones puras de Bash/Linux
│   │   │   └── windows/                # Operaciones puras de CMD/PowerShell
│   │   ├── input_tool.py               # Emulación de teclado/mouse
│   │   └── system_info_tool.py         # Telemetría de sensores (CPU/RAM)
│   ├── web/                            # Frontend assets (HTML, JS, CSS) sin Emojis
│   ├── connection.py                   # Motor WS cliente
│   ├── executor/executor.py            # Validador y parser de herramientas (Interceptador de Peligro)
│   ├── stt_engine.py                   # Speech to Text local
│   ├── wake_word.py                    # Escucha en bucle infinito (offline)
│   ├── main.py                         # UI, Atajos globales y PyWebView container
│   └── repl.py                         # Bash/Terminal asíncrono
├── .env.example
├── .gitignore
├── DOCUMENTATION.md
└── README.md
```
