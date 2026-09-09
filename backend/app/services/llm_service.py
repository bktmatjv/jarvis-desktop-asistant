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
from app.services.skill_service import get_tools_for_domain, load_skills

# --- Segregated Client Pools ---
_fast_keys = settings.get_fast_keys()
_reasoning_keys = settings.get_reasoning_keys()

if not _fast_keys and not _reasoning_keys:
    raise ValueError("Debes proveer al menos una API Key de Groq en el .env")

fast_clients = [AsyncGroq(api_key=k) for k in (_fast_keys or _reasoning_keys)]
reasoning_clients = [AsyncGroq(api_key=k) for k in (_reasoning_keys or _fast_keys)]

current_fast_idx = 0
current_reasoning_idx = 0


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
    """Compact system prompt for fast conversational stream (< 100 tokens)."""
    import datetime
    now = datetime.datetime.now().strftime('%H:%M')
    return (
        f"Eres JARVIS, el asistente de escritorio para {username} ({client_os}). Hora: {now}.\n"
        "Estilo: Amigable, inteligente, conciso y natural. Sin emojis. Respuestas directas al grano."
    )


def _build_reasoning_system_prompt(client_os: str, client_caps: list, username: str, role: str) -> str:
    """Compact system prompt for the Reasoning model (< 200 tokens)."""
    import datetime
    now = datetime.datetime.now().strftime('%H:%M')
    return (
        f"Eres JARVIS, asistente ejecutivo para {username} en {client_os}. Hora: {now}.\n"
        "REGLAS OBLIGATORIAS:\n"
        "1. Usa las herramientas y skills disponibles para ejecutar las acciones pedidas.\n"
        "2. NUNCA des instrucciones manuales si tienes una herramienta para ejecutarlo tú mismo.\n"
        "3. Ejecuta solo las herramientas necesarias. Respuestas breves y al grano. Sin emojis.\n"
        "4. No inventes logs falsos ni uses etiquetas XML. Usa formato JSON nativo de tool_calls."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_clean_history(session_history: list) -> list:
    """Prunes history to the last 4 messages and limits message length to save TPM."""
    allowed_keys = {"role", "content", "name", "tool_call_id", "tool_calls"}
    # Keep only last 4 messages to stay well under TPM limits
    history = session_history[-4:]

    clean = []
    for msg in history:
        clean_msg = {k: v for k, v in msg.items() if k in allowed_keys}

        if clean_msg.get("name") == "execute_bash":
            clean_msg["name"] = "execute_command"

        if "tool_calls" in clean_msg and isinstance(clean_msg["tool_calls"], list):
            for tc in clean_msg["tool_calls"]:
                if tc.get("function", {}).get("name") == "execute_bash":
                    tc["function"]["name"] = "execute_command"

        # Truncate long tool outputs to 1500 chars (safe for TPM)
        if clean_msg.get("role") == "tool" and isinstance(clean_msg.get("content"), str):
            if len(clean_msg["content"]) > 1500:
                clean_msg["content"] = clean_msg["content"][:1500] + "\n...[OUTPUT TRUNCADO POR SEGURIDAD]"
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


def _get_next_fast_client():
    global current_fast_idx
    return fast_clients[current_fast_idx]

def _rotate_fast_client():
    global current_fast_idx
    current_fast_idx = (current_fast_idx + 1) % len(fast_clients)

def _get_next_reasoning_client():
    global current_reasoning_idx
    return reasoning_clients[current_reasoning_idx]

def _rotate_reasoning_client():
    global current_reasoning_idx
    current_reasoning_idx = (current_reasoning_idx + 1) % len(reasoning_clients)


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
    Calls the fast model with stream=True.
    Pushes complete sentences into a Queue as they arrive.
    """
    queue: asyncio.Queue = asyncio.Queue()

    async def _producer():
        system_prompt = _build_fast_system_prompt(client_os, username)
        clean_history = _build_clean_history(session_history)
        fast_history = [
            m for m in clean_history
            if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
        ]
        messages = [{"role": "system", "content": system_prompt}] + fast_history

        buffer = ""
        for attempt in range(len(fast_clients)):
            client = _get_next_fast_client()
            try:
                stream = await client.chat.completions.create(
                    model=settings.FAST_MODEL,
                    messages=messages,
                    max_tokens=512,
                    temperature=0.7,
                    stream=True,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    buffer += delta
                    parts = re.split(r'(?<=[.!?…])\s+', buffer)
                    if len(parts) > 1:
                        for sentence in parts[:-1]:
                            if sentence.strip():
                                await queue.put(sentence.strip())
                        buffer = parts[-1]

                if buffer.strip():
                    await queue.put(buffer.strip())
                break

            except (RateLimitError, APIStatusError) as e:
                status = getattr(e, 'status_code', 0)
                if status in (413, 429) or isinstance(e, RateLimitError):
                    logger.warning(f"[FAST] Cuota/Rate limit ({status}). Rotando key...")
                    _rotate_fast_client()
                    buffer = ""
                    continue
                else:
                    logger.error(f"[FAST] Error en streaming: {e}")
                    await queue.put("Disculpe señor, ocurrió un error procesando su solicitud.")
                    break
            except Exception as e:
                logger.error(f"[FAST] Error inesperado en streaming: {e}", exc_info=True)
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
    domain: str = None,
) -> dict:
    """
    Calls the Reasoning model with pruned domain tools to stay far below the 8000 TPM limit.
    """
    system_prompt = _build_reasoning_system_prompt(client_os, client_caps, username, role)
    clean_history = _build_clean_history(session_history)

    if _check_tool_loop(session_history):
        system_prompt += "\n\n[SISTEMA INTERNO]: Límite de herramientas consecutivas alcanzado. Detén el uso de herramientas y responde directamente al usuario."

    # Skill Pruner: Select only tools relevant to the domain (reduces tokens by 80%)
    active_tools = get_tools_for_domain(domain, tools)
    dynamic_skills = load_skills()

    messages = [{"role": "system", "content": system_prompt}] + clean_history

    for attempt in range(len(reasoning_clients)):
        groq_client = _get_next_reasoning_client()
        try:
            logger.info(f"[REASONING] Llamando a {settings.REASONING_MODEL} (Dominio: {domain}, Herramientas: {len(active_tools)})")
            call_kwargs = {
                "model": settings.REASONING_MODEL,
                "messages": messages,
                "max_tokens": 1024,
                "stream": False,
            }
            if active_tools:
                call_kwargs["tools"] = active_tools
                call_kwargs["tool_choice"] = "auto"

            response = await groq_client.chat.completions.create(**call_kwargs)
            response_message = response.choices[0].message
            return parse_llm_response(response_message, dynamic_skills)

        except (RateLimitError, APIStatusError) as e:
            status = getattr(e, 'status_code', 0)
            if status in (413, 429) or isinstance(e, RateLimitError):
                logger.warning(f"[REASONING] Cuota/Rate Limit ({status}) en key {current_reasoning_idx}. Rotando clave...")
                _rotate_reasoning_client()
                await asyncio.sleep(0.5)
                continue
            else:
                logger.error(f"[REASONING] Groq API Error {status}: {e}", exc_info=True)
                return {"type": "speak", "message": f"Error del modelo {status}: {str(e)[:100]}"}
        except Exception as e:
            logger.error(f"[REASONING] Excepción inesperada: {e}", exc_info=True)
            return {"type": "speak", "message": f"Error inesperado en razonamiento: {str(e)[:100]}"}

    return {"type": "speak", "message": "Disculpe señor, todas las claves de razonamiento han alcanzado su límite de cuota temporal."}


async def chat_with_jarvis(
    session_history: list,
    client_os: str,
    client_caps: list,
    username: str = "Invitado",
    role: str = "user",
    domain: str = None,
) -> dict:
    """Default entry point for reasoning queries."""
    return await chat_reasoning(session_history, client_os, client_caps, username, role, domain)
