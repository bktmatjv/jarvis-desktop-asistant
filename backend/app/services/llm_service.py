"""
LLM Service module — JARVIS 2.0 Dual-Model Architecture.

Two specialized functions:
  - chat_fast():      OSS 20B (Groq) — direct conversational responses, streaming.
  - chat_reasoning(): Qwen 27B (Groq) — full tool calling, complex reasoning.
  - chat_with_jarvis(): Orchestrator — routes between fast and reasoning based on intent.

Streaming is handled via async generators so the WebSocket can send sentences
to the client (and TTS) as soon as they are formed, without waiting for the full response.
"""
import json
import asyncio
import re
from groq import AsyncGroq, RateLimitError, APIStatusError
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("llm_service")
from app.services.skill_service import get_llm_tools, load_skills

# --- Client Pool (shared for both models via key rotation) ---
api_keys = [k.strip() for k in settings.GROQ_API_KEYS.split(",") if k.strip()]
if not api_keys:
    raise ValueError("Debes proveer al menos una GROQ_API_KEYS en el .env")

clients = [AsyncGroq(api_key=key) for key in api_keys]
current_client_idx = 0

# ---------------------------------------------------------------------------
# Tool Definitions (used exclusively by the Reasoning model)
# ---------------------------------------------------------------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Ejecuta un comando en la terminal del cliente (Usa PowerShell si es Windows, o Bash si es Linux). Útil para investigar, abrir archivos o explorar el sistema. Usa comandos no interactivos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "El comando a ejecutar según el OS del cliente. Ejemplo (Linux): ls -la. Ejemplo (Windows): Get-ChildItem, echo hello"
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_reminder",
            "description": "Agenda un recordatorio o notificación proactiva para el futuro en el lado del servidor. El servidor te despertará y te pedirá que le digas esto al usuario cuando el temporizador expire.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "El mensaje o recordatorio exacto que quieres decirle al usuario cuando el temporizador expire."
                    },
                    "delay_seconds": {
                        "type": "integer",
                        "description": "La cantidad de segundos a esperar antes de notificar al usuario. (ej. 60 para 1 minuto)"
                    }
                },
                "required": ["message", "delay_seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_plan",
            "description": "Crea un plan estructurado de pasos para resolver una tarea compleja. Usar antes de ejecutar múltiples comandos para mantener informado al usuario y hacer un seguimiento.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Título o descripción general de la tarea que vas a realizar."
                    },
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista secuencial de descripciones cortas de cada paso."
                    }
                },
                "required": ["title", "steps"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_plan_step",
            "description": "Actualiza el estado de un paso dentro del plan activo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "step_index": {
                        "type": "integer",
                        "description": "Índice (empezando desde 0) del paso que deseas actualizar."
                    },
                    "status": {
                        "type": "string",
                        "enum": ["in_progress", "completed", "failed"],
                        "description": "El nuevo estado de este paso."
                    }
                },
                "required": ["step_index", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Guarda permanentemente un hecho, preferencia o detalle importante sobre el usuario o el contexto en la base de datos de memoria a largo plazo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "El hecho o información a recordar de forma concisa."
                    }
                },
                "required": ["fact"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Busca en la memoria a largo plazo información, preferencias o hechos pasados del usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Término de búsqueda (palabra clave corta o expresión regular)."
                    }
                },
                "required": ["query"],
            },
        },
    }
]

# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------

def _build_fast_system_prompt(client_os: str, username: str) -> str:
    """Minimal system prompt for the fast OSS 20B model — personality only."""
    import datetime
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"""Eres JARVIS, el asistente de escritorio autónomo.
Fecha y Hora actual: {now}
OS del usuario: {client_os}
Usuario: {username}

ESTILO DE RESPUESTA:
- Habla en primera persona con extrema formalidad.
- Trata al usuario como 'señor'.
- Sin emojis bajo ninguna circunstancia.
- Respuestas breves, directas y al grano.
- Si el usuario pregunta algo que no sabes o requiere acciones en el sistema, dile que estás procesando la solicitud."""


def _build_reasoning_system_prompt(client_os: str, client_caps: list, username: str, role: str) -> str:
    """Full system prompt for the Reasoning Qwen model — tool calling enabled."""
    import datetime
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"""Eres JARVIS, el asistente de escritorio autónomo.
Fecha y Hora actual: {now}
Estás conectado al dispositivo del usuario con sistema operativo: {client_os}.
Capacidades del cliente: {client_caps}.
Identidad del usuario: {username}
Nivel de acceso: {role.upper()}

REGLA DE ORO ESTRICTA: ¡NO ERES UN CHATBOT DE AYUDA! Eres un asistente ejecutivo que DEBE usar sus herramientas integradas.
NUNCA le des instrucciones paso a paso al usuario sobre cómo hacer algo. DEBES hacerlo TÚ MISMO invocando directamente la herramienta 'execute_command'.
- Si el usuario dice "Abre chrome", usa la herramienta 'execute_command' con el comando: Start-Process chrome


REGLA DE EJECUCIÓN (LÍMITE):
- SOLO TIENES PERMITIDO ejecutar un máximo de UN (1) comando por cada petición del usuario. No lances múltiples comandos en ráfaga. Si tu comando falla, avísale al usuario y espera sus órdenes.
- Usa los comandos nativos más simples que conozcas de PowerShell (ej. `taskmgr`, `Start-Process explorer.exe`, etc).

REGLAS ANTI-ALUCINACIONES:
- NUNCA simules ni inventes la salida de la terminal. TÚ envías el comando por la herramienta, y el SISTEMA te enviará la respuesta real. Está terminantemente prohibido que escribas etiquetas como <tool_response> en tus mensajes.
- Si la herramienta falla, no inventes logs falsos.
- Usa SIEMPRE el formato de invocación JSON nativo de OpenAI/Groq para las herramientas. NUNCA respondas con etiquetas <tool_call> ni XML.

Si la tarea requiere múltiples pasos explícitos, usa SIEMPRE la herramienta 'create_plan'. Luego usa 'update_plan_step' para hacer seguimiento.

IMPORTANTE PARA COMANDOS: Usa comandos simples de UNA SOLA LÍNEA (separa con ';' en PowerShell).
Después de ejecutar exitosamente una herramienta, resume brevemente el resultado al usuario.

ESTILO DE RESPUESTA:
- Habla SIEMPRE en primera persona y con extrema formalidad y seriedad.
- Trata al usuario como 'señor' (ej. "Un momento, señor, ando ejecutando el escaneo...").
- ESTÁ ESTRICTAMENTE PROHIBIDO usar emojis (, , ️, , etc.) bajo CUALQUIER circunstancia.

MEMORIA A LARGO PLAZO:
- Si el usuario te menciona algún gusto, preferencia, nombre de alguien, dato personal, o hecho importante, DEBES invocar INMEDIATAMENTE la herramienta `save_memory` para que no se te olvide en el futuro.
- Si el usuario te pregunta por algo del pasado, o hace referencia a algo que deberías saber sobre él, DEBES usar la herramienta `search_memory` ANTES de decirle que no sabes la respuesta.
- Breve, directo y al grano.
- Si debes dar mucha información, resume los puntos clave.
- NUNCA te ofrezcas a "ayudar con la interpretación" o "indicar cómo hacerlo". Si te piden algo, EJECÚTALO mediante tus herramientas."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_clean_history(session_history: list) -> list:
    """Strips unknown keys and normalizes tool call names."""
    allowed_keys = {"role", "content", "name", "tool_call_id", "tool_calls"}
    # Keep last 8 messages (4 interactions)
    history = session_history[-8:]

    clean = []
    for msg in history:
        clean_msg = {k: v for k, v in msg.items() if k in allowed_keys}

        if clean_msg.get("name") == "execute_bash":
            clean_msg["name"] = "execute_command"

        if "tool_calls" in clean_msg and isinstance(clean_msg["tool_calls"], list):
            for tc in clean_msg["tool_calls"]:
                if tc.get("function", {}).get("name") == "execute_bash":
                    tc["function"]["name"] = "execute_command"

        # Truncate excessively long tool outputs
        if clean_msg.get("role") == "tool" and isinstance(clean_msg.get("content"), str):
            if len(clean_msg["content"]) > 8000:
                clean_msg["content"] = (
                    clean_msg["content"][:8000]
                    + "\n...[RESULTADO TRUNCADO. LÍMITE DE 8000 CARACTERES ALCANZADO PARA PROTEGER EL CONTEXTO]"
                )
        clean.append(clean_msg)

    return clean


def _check_tool_loop(session_history: list) -> bool:
    """Returns True if the circuit breaker should fire (>= 4 consecutive tool calls)."""
    consecutive = 0
    for msg in reversed(session_history):
        if msg.get("role") == "tool" or (
            msg.get("role") == "assistant" and msg.get("tool_calls")
        ):
            consecutive += 1
        elif msg.get("role") == "user":
            break
    return consecutive >= 4


def _get_next_client():
    """Round-robin client selector with rate-limit rotation."""
    global current_client_idx
    client = clients[current_client_idx]
    return client


def _rotate_client():
    global current_client_idx
    current_client_idx = (current_client_idx + 1) % len(clients)


# ---------------------------------------------------------------------------
# Streaming helpers
# ---------------------------------------------------------------------------

def _split_into_sentences(text: str) -> list[str]:
    """Splits text into sentences for incremental TTS delivery."""
    sentences = re.split(r'(?<=[.!?…])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


async def stream_fast_response(
    session_history: list,
    client_os: str,
    username: str,
) -> asyncio.Queue:
    """
    Calls the fast OSS 20B model with stream=True.
    Pushes complete sentences into a Queue as they arrive.
    Pushes None when done (sentinel).

    Usage:
        queue = await stream_fast_response(...)
        while True:
            sentence = await queue.get()
            if sentence is None:
                break
            await websocket.send_text(SpeakResponse(message=sentence).model_dump_json())
    """
    queue: asyncio.Queue = asyncio.Queue()

    async def _producer():
        global current_client_idx
        system_prompt = _build_fast_system_prompt(client_os, username)
        clean_history = _build_clean_history(session_history)
        # Keep only user/assistant messages for the fast model
        fast_history = [
            m for m in clean_history
            if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
        ]
        messages = [{"role": "system", "content": system_prompt}] + fast_history

        buffer = ""
        for attempt in range(len(clients)):
            client = _get_next_client()
            try:
                stream = await client.chat.completions.create(
                    model=settings.ROUTER_MODEL,
                    messages=messages,
                    max_tokens=512,
                    temperature=0.7,
                    stream=True,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    buffer += delta
                    # Flush complete sentences to the queue
                    parts = re.split(r'(?<=[.!?…])\s+', buffer)
                    if len(parts) > 1:
                        for sentence in parts[:-1]:
                            if sentence.strip():
                                await queue.put(sentence.strip())
                        buffer = parts[-1]

                # Flush remainder
                if buffer.strip():
                    await queue.put(buffer.strip())
                break  # Success

            except RateLimitError:
                logger.warning(f"[FAST] Rate limit key {current_client_idx}. Rotando...")
                _rotate_client()
                buffer = ""
                continue
            except Exception as e:
                logger.error(f"[FAST] Error en streaming: {e}", exc_info=True)
                await queue.put("Disculpe señor, ocurrió un error procesando su solicitud.")
                break

        await queue.put(None)  # Sentinel

    asyncio.create_task(_producer())
    return queue


# ---------------------------------------------------------------------------
# Reasoning model — non-streaming tool call, streaming final text
# ---------------------------------------------------------------------------

def parse_llm_response(response_message, dynamic_skills=None):
    """Parse a non-streaming LLM response into a JARVIS action dict."""
    if dynamic_skills is None:
        dynamic_skills = []
    # 1. Try official OpenAI / Groq tool_calls format
    if response_message.tool_calls:
        tool_call = response_message.tool_calls[0]
        name = tool_call.function.name
        args_str = tool_call.function.arguments
        call_id = tool_call.id
    else:
        # 2. Rescue mode (local LLMs that emit tool calls as text)
        content = (response_message.content or "").strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        if content.startswith("{") and "name" in content and "arguments" in content:
            try:
                parsed = json.loads(content)
                if "name" in parsed and "arguments" in parsed:
                    name = parsed["name"]
                    args_raw = parsed["arguments"]
                    args_str = json.dumps(args_raw) if isinstance(args_raw, dict) else str(args_raw)
                    call_id = "call_rescue"
                else:
                    return {"type": "speak", "message": response_message.content}
            except json.JSONDecodeError:
                return {"type": "speak", "message": response_message.content}
        else:
            if not response_message.content:
                reasoning = getattr(response_message, 'reasoning', None)
                if reasoning:
                    logger.warning("El LLM agotó los tokens durante el razonamiento.")
                    return {"type": "speak", "message": f"Mi proceso mental se interrumpió por límite de tokens, señor. Esto es lo que estaba pensando: {reasoning[-200:]}"}

                logger.error(f"El LLM devolvió una respuesta vacía: {response_message}")
                return {"type": "speak", "message": "Señor, ocurrió un error interno. Puede revisar el registro de errores para más detalles."}
            return {"type": "speak", "message": response_message.content}

    # 3. Dispatch tool calls
    if name == "execute_command":
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            args = {}
        cmd = args.get("command", "")
        if isinstance(cmd, dict):
            cmd = cmd.get("command", "")
        return {
            "type": "tool_call",
            "tool": "execute_command",
            "command": cmd or "echo 'Error: Comando vacío'",
            "tool_call_id": call_id
        }
    elif name == "schedule_reminder":
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            args = {}
        return {
            "type": "server_tool",
            "tool": "schedule_reminder",
            "message": args.get("message", "Recordatorio vacío"),
            "delay_seconds": args.get("delay_seconds", 60),
            "tool_call_id": call_id
        }
    elif name == "create_plan":
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            args = {}
        return {
            "type": "server_tool",
            "tool": "create_plan",
            "title": args.get("title", "Plan de acción"),
            "steps": args.get("steps", []),
            "tool_call_id": call_id
        }
    elif name == "update_plan_step":
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            args = {}
        return {
            "type": "server_tool",
            "tool": "update_plan_step",
            "step_index": args.get("step_index", 0),
            "status": args.get("status", "completed"),
            "tool_call_id": call_id
        }
    elif name == "save_memory":
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            args = {}
        return {
            "type": "server_tool",
            "tool": "save_memory",
            "fact": args.get("fact", ""),
            "tool_call_id": call_id
        }
    elif name == "search_memory":
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            args = {}
        return {
            "type": "server_tool",
            "tool": "search_memory",
            "query": args.get("query", ""),
            "tool_call_id": call_id
        }
    elif any(name == s.get("name") for s in dynamic_skills):
        skill = next(s for s in dynamic_skills if s.get("name") == name)
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            args = {}

        if skill.get("_execution_context") == "backend":
            return {
                "type": "server_skill",
                "skill_name": name,
                "params": args,
                "tool_call_id": call_id,
                "skill_path": skill.get("_path"),
                "executable": skill.get("executable"),
                "language": skill.get("language")
            }
        else:
            return {
                "type": "tool_call",
                "tool": "execute_skill",
                "skill_name": name,
                "params": args,
                "tool_call_id": call_id
            }

    return {"type": "speak", "message": response_message.content or "..."}


async def chat_reasoning(
    session_history: list,
    client_os: str,
    client_caps: list,
    username: str = "Invitado",
    role: str = "user",
) -> dict:
    """
    Calls the heavy Qwen reasoning model with full tool schema.
    Returns an action dict (speak | tool_call | server_tool | server_skill).
    Uses stream=False for tool calls (needs the full JSON), stream=True for plain text responses.
    """
    global current_client_idx

    system_prompt = _build_reasoning_system_prompt(client_os, client_caps, username, role)
    clean_history = _build_clean_history(session_history)

    if _check_tool_loop(session_history):
        system_prompt += "\n\n[SISTEMA INTERNO]: Has excedido el límite de herramientas consecutivas sin que el usuario hable. DEBES detenerte AHORA, no usar más herramientas y responder directamente al usuario con un resumen."

    dynamic_skills = load_skills()
    dynamic_llm_tools = get_llm_tools()
    all_tools = tools + dynamic_llm_tools

    messages = [{"role": "system", "content": system_prompt}] + clean_history

    for attempt in range(len(clients)):
        groq_client = clients[current_client_idx]
        try:
            logger.info(f"[REASONING] Llamando a {settings.REASONING_MODEL}")
            response = await groq_client.chat.completions.create(
                model=settings.REASONING_MODEL,
                messages=messages,
                tools=all_tools,
                tool_choice="auto",
                max_tokens=4096,
                stream=False,  # Must be False to reliably parse tool calls
            )

            response_message = response.choices[0].message
            return parse_llm_response(response_message, dynamic_skills)

        except (RateLimitError, APIStatusError) as e:
            if getattr(e, 'status_code', 0) == 429 or isinstance(e, RateLimitError):
                logger.warning(f"Rate Limit key {current_client_idx}. Rotando...")
                _rotate_client()
                await asyncio.sleep(1)
                continue
            else:
                logger.error(f"Groq API Error {getattr(e, 'status_code', 'Unknown')}: {e}", exc_info=True)
                error_str = str(e)
                if "failed_generation" in error_str and "<tool_call>" in error_str:
                    cmd_match = re.search(r"<parameter=command>\s*(.*?)(?:<|$)", error_str, re.DOTALL)
                    if cmd_match:
                        cmd = cmd_match.group(1).strip()
                        return {
                            "type": "tool_call",
                            "tool": "execute_command",
                            "command": cmd,
                            "tool_call_id": "call_groq_rescue"
                        }
                return {"type": "speak", "message": f"Error {getattr(e, 'status_code', '400')}: {str(e)}"}
        except Exception as e:
            logger.error(f"Excepción inesperada en Reasoning: {e}", exc_info=True)
            return {"type": "speak", "message": f"Error inesperado en el modelo de razonamiento: {e}"}

    return {"type": "speak", "message": "Error: Todos los clientes Groq han alcanzado su límite de velocidad."}


async def chat_with_jarvis(
    session_history: list,
    client_os: str,
    client_caps: list,
    username: str = "Invitado",
    role: str = "user",
) -> dict:
    """
    Orchestrator — kept for backward compatibility with the scheduler/reminder system.
    For the main WebSocket loop, use chat_reasoning() directly after the router classifies.
    This function defaults to the reasoning model (tool-capable path).
    """
    return await chat_reasoning(session_history, client_os, client_caps, username, role)
