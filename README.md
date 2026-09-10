# JARVIS: Asistente de Escritorio Autónomo

JARVIS es un sistema de asistencia e inteligencia artificial de escritorio con una arquitectura robusta **Cliente-Servidor** y capacidades autónomas avanzadas. Puede controlar tu entorno de escritorio, agendar tareas de forma proactiva, interactuar mediante reconocimiento de voz offline (Wake Word) y proveer automatización a nivel de sistema tanto en Windows como en Linux.

---

## Features Principales

### Loop Engineering — Arquitectura Dual-Model
El corazón del sistema utiliza dos modelos LLM especializados trabajando en tándem:
- **Fast Router (`openai/gpt-oss-20b`)**: Clasifica la intención del usuario en menos de 300ms y genera una *frase de stalling* humana e inmediata mientras el razonamiento trabaja en background. Minimiza la latencia percibida.
- **Reasoning Model (`qwen/qwen3.6-27b`)**: Modelo de razonamiento complejo que ejecuta el Tool Calling (skills, comandos de terminal) y devuelve respuestas elaboradas.

El HUD Panel muestra en tiempo real cada paso del pipeline: Ingestion → Router → Context Pruner → Reasoning → Skill Runner → Synthesizer.

### Sistema de Skills Modulares
Las capacidades de acción están empaquetadas como Skills independientes (archivos `main.py` + `skill.json`), cargadas dinámicamente por el backend. El motor filtra por dominio para no saturar el contexto del LLM:
- **`system_control`** — Abrir programas, ajustar volumen, apagar/reiniciar/bloquear
- **`window_manager`** — Listar, enfocar, minimizar, maximizar y cerrar ventanas
- **`system_telemetry`** — CPU, RAM, batería, procesos activos y capturas de pantalla
- **`input_controller`** — Simular teclado, atajos y movimiento/clic de mouse
- **`media_control`** — Control de reproducción multimedia (play/pause, siguiente, anterior)
- **`play_ytmusic`** — Buscar y reproducir canciones en YouTube Music
- **`web_search`** / **`web_fetch`** — Búsqueda y lectura de contenido web en tiempo real

### Interfaz de Usuario Dual (HUD)
El cliente ejecuta **dos ventanas simultáneas** gestionadas por PyWebView:
1. **Panel de Control** (`client/web/`) — HUD holográfico de escritorio completo con chat, telemetría, consola de procesos y visualizador del Loop Engineering en tiempo real.
2. **Orbe Flotante** (`client/frontend/`) — Esfera 3D translúcida y animada (React + Three.js) que flota sobre el escritorio y reacciona visualmente al estado del sistema (dormido, activo, escuchando).

![HUD Captura 1](client/img/cap1.png)
*El Panel de Control con telemetría en tiempo real y chat activo.*

![HUD Captura 2](client/img/cap2.png)
*El visualizador de Loop Engineering muestra cada etapa del pipeline de IA.*

### Reconocimiento de Voz Offline (Wake Word)
El cliente incorpora un motor Wake Word impulsado por **Vosk** que escucha constantemente en background sin conexión a internet. Al detectar "Jarvis", activa el flujo de grabación con **Groq Whisper** para transcribir el comando con alta precisión.

### Autonomía Proactiva (APScheduler)
El backend puede programar eventos en el futuro mediante APScheduler. Al expirar el temporizador, el servidor envía un Push Event vía WebSocket directamente al HUD del usuario sin intervención manual.

### Interceptor de Seguridad
Antes de ejecutar comandos de terminal potencialmente peligrosos (`rm -rf`, `chmod`, etc.), el sistema pausa el flujo y muestra un modal de confirmación en el HUD solicitando autorización explícita.

### Arquitectura de Alta Disponibilidad (Anti Rate-Limit)
Acepta múltiples API Keys de Groq segregadas por rol (`GROQ_API_KEYS_VOICE`, `GROQ_API_KEYS_FAST`, `GROQ_API_KEYS_REASONING`). Ante un error HTTP 429, rota automáticamente al siguiente cliente disponible sin interrumpir la conversación.

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────┐
│                  JARVIS SYSTEM                      │
│                                                     │
│  ┌─────────────┐         ┌───────────────────────┐  │
│  │   CLIENT    │◄───WS──►│       BACKEND         │  │
│  │ (PyWebView) │         │     (FastAPI)         │  │
│  │             │         │                       │  │
│  │ • Wake Word │         │ • Intent Router       │  │
│  │ • STT/TTS   │         │ • Reasoning Model     │  │
│  │ • HUD Panel │         │ • Skill Service       │  │
│  │ • Orb 3D    │         │ • Memory (MongoDB)    │  │
│  │ • Skills    │         │ • Scheduler           │  │
│  └─────────────┘         └───────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

El Backend (cerebro) está separado del Cliente (cuerpo) para garantizar seguridad y escalabilidad. Ver [DOCUMENTATION.md](DOCUMENTATION.md) para la arquitectura técnica detallada y [DATABASE_DESIGN.md](DATABASE_DESIGN.md) para el diseño de datos y modelo multidispositivo.

---

## Instalación y Despliegue

### Requisitos
- Python 3.10+
- Node.js 18+ *(solo si quieres modificar el Orbe 3D — el bundle compilado viene incluido)*
- Cuenta en [Groq Cloud](https://console.groq.com) con al menos una API Key
- URI de conexión a MongoDB Atlas

### 1. Variables de Entorno
```bash
cp .env.example .env
```
Edita `.env` con tus credenciales:
```ini
GROQ_API_KEYS_VOICE=gsk_...
GROQ_API_KEYS_FAST=gsk_...
GROQ_API_KEYS_REASONING=gsk_...
MONGO_URI=mongodb+srv://user:password@cluster...
USER_NAME=TU NOMBRE
USER_ROLE=admin
```

### 2. Instalación Automática (Windows — Recomendado)
Ejecuta este archivo una sola vez para configurar todo el entorno:
```
setup_env.bat
```
Esto creará el virtualenv, instalará todas las dependencias de backend y cliente, y descargará el modelo de Vosk.

### 3. Iniciar JARVIS
```
start_jarvis.bat
```
El launcher inicia el servidor FastAPI en background, espera a que esté disponible y luego lanza el cliente HUD.

Presiona `Ctrl + Espacio` para el Orbe 3D, y `Ctrl + ↑` para el Panel de Control.

### Instalación Manual (Linux / avanzado)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Cliente:**
```bash
cd client
pip install -r requirements.txt
python download_model.py   # Solo la primera vez
python main.py
```

---

## Historial de Versiones

| Versión | Fecha | Descripción |
| :--- | :--- | :--- |
| **v2.5.0** | Septiembre 2026 | Loop Engineering con Dual-Model (Router + Reasoning). Visualizador de pipeline en HUD. Orbe 3D con Three.js/React. Sistema de Skills modular con pruning de contexto por dominio. Instalación en 1 clic con `.bat`. |
| **v2.1.0** | Agosto 2026 | Arquitectura OS-Agnostic con herramientas para Windows/Linux. Integración de motores locales Vosk para Wake Word y STT. |
| **v2.0.0** | Agosto 2026 | Refactorización masiva a arquitectura Cliente-Servidor (FastAPI + PyWebview). Incorporación de Autonomía proactiva. |
| **v1.5.0** | Julio 2026 | Mejoras en el HUD Holográfico con Vanilla CSS. |
