# JARVIS: Asistente de Escritorio Autónomo

JARVIS es un sistema de Asistencia e Inteligencia Artificial de grado AGI, diseñado con una arquitectura robusta de **Cliente-Servidor (Backend)** y capacidades autónomas. Puede controlar tu entorno de escritorio, agendar tareas por su cuenta, interactuar auditivamente mediante reconocimiento de voz offline (Wake Word) y proveer automatización a nivel de sistema tanto en Linux como en Windows.

---

## Features Principales

### Autonomía Proactiva y Calendarización Asíncrona
El núcleo del asistente incorpora un motor de tareas en segundo plano basado en `APScheduler`. Esto le otorga al LLM la capacidad de invocar llamadas a herramientas (Tool Calls) del lado del servidor para programar eventos en el futuro. Cuando el temporizador expira, el backend inicia una comunicación WebSocket (Push Event) hacia el cliente para notificar al usuario de forma autónoma.

### Compatibilidad Multiplataforma (Windows y Linux)
El sistema cliente detecta automáticamente el Sistema Operativo subyacente y utiliza las herramientas OS-Level correspondientes:
- Interactúa con APIs de Windows o gestores de Linux de forma transparente.
- Control avanzado de ventanas, multimedia y explorador de archivos.

### Reconocimiento de Voz Offline e Interacción Natural
El cliente cuenta con un motor STT (Speech-to-Text) y un "Wake Word" engine impulsado por **Vosk**. JARVIS escucha de fondo sin necesidad de conexión a internet para esta fase, despertando únicamente cuando lo nombras, ahorrando recursos computacionales y protegiendo la privacidad.

### Ejecución de Comandos a Nivel de Sistema (REPL)
El cliente local actúa como un puente de hardware y software, permitiendo la ejecución de comandos. Mediante subprocesos administrados por `asyncio`, el agente puede:
- Modificar el sistema de archivos.
- Iniciar aplicaciones de interfaz gráfica o herramientas CLI.
- Monitorear en tiempo real métricas vitales (uso de CPU y memoria RAM).

### Arquitectura de Redundancia y Manejo de Rate Limits
Para garantizar la operación continua sin interrupciones por límites de cuota, la capa de integración LLM acepta múltiples API Keys (ej. Groq). Ante una respuesta de limitación HTTP 429, el servicio rota automáticamente al siguiente cliente disponible.

### Interceptor de Seguridad de Ejecución
Como salvaguarda ante operaciones destructivas generadas por el LLM, el cliente evalúa todos los comandos del sistema contra una lista heurística de operaciones de alto riesgo (ej. `rm -rf`, `chmod`, formateos). Si se detecta una coincidencia, el hilo de ejecución se pausa y renderiza un modal en el HUD solicitando autorización explícita humana.

---

## Interfaz de Usuario (HUD)

El cliente de escritorio cuenta con un Head-Up Display (HUD) estilo holográfico que te muestra en tiempo real las acciones que JARVIS ejecuta en tu máquina.

![HUD Captura 1](client/img/cap1.png)
*El cliente listo para recibir órdenes, monitoreando el estado vital de la PC.*

![HUD Captura 2](client/img/cap2.png)
*Visualización de respuestas, notificaciones proactivas y comandos del sistema.*

---

## Arquitectura del Sistema

El sistema está dividido estrictamente en dos partes para garantizar máxima seguridad y escalabilidad:

1. **Backend**: Un servidor FastAPI que maneja la memoria, el LLM, el enrutamiento de peticiones (router_service), control de habilidades remotas (skill_service) y la rotación de API Keys. 
2. **Client**: Una aplicación de Python (PyWebView + HTML/JS/CSS) que reside en la estación de trabajo local, controla los sensores de voz y ejecuta las herramientas locales delegadas por el Backend.

Para mayor profundidad sobre la separación de herramientas OS y los nuevos servicios inyectados, referirse al documento: [DOCUMENTATION.md](DOCUMENTATION.md)

---

## Instalación y Despliegue

### 1. Variables de Entorno
Copia el archivo de ejemplo y complétalo:
```bash
cp .env.example .env
```
Añade tus API Keys de Groq (separadas por coma) y tu URI de conexión a MongoDB.

### 2. Preparar el Modelo de Voz Local
Descarga los modelos requeridos para el reconocimiento offline de Vosk en el cliente.
```bash
cd client
python download_model.py
```

### 3. Iniciar el Backend
En una terminal (con entorno virtual):
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 4. Iniciar el Cliente HUD
En otra terminal diferente:
```bash
cd client
pip install -r requirements.txt
python main.py
```

Presiona `Ctrl + Espacio` en cualquier momento en tu escritorio para invocar el HUD holográfico.

---

## Historial de Versiones

| Versión | Fecha | Descripción |
| :--- | :--- | :--- |
| **v2.1.0** | Agosto 2026 | Arquitectura OS-Agnostic con herramientas para Windows/Linux. Integración de motores locales Vosk para Wake Word y STT. UI purgada de emojis para un enfoque más sobrio. |
| **v2.0.0** | Agosto 2026 | Refactorización masiva a arquitectura Cliente-Servidor (FastAPI + PyWebview). Incorporación de Autonomía proactiva. |
| **v1.5.0** | Julio 2026 | Mejoras en el HUD Holográfico con Vanilla CSS. |
