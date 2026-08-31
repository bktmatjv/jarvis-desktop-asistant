"""
Router Service module.
Uses the fast OSS 20B model to classify user intent and generate stalling phrases.
This runs before the heavy Reasoning model to keep the WebSocket responsive.
"""
import json
import random
from groq import AsyncGroq, RateLimitError
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("router_service")

# Build router clients from same API key pool as main service
_api_keys = [k.strip() for k in settings.GROQ_API_KEYS.split(",") if k.strip()]
_router_clients = [AsyncGroq(api_key=key) for key in _api_keys]
_router_client_idx = 0

# Fallback stalling phrases if the router itself fails
FALLBACK_STALLING = [
    "Un momento, señor, consultando los sistemas.",
    "Dame un segundo, procesando su solicitud.",
    "Revisando la información, señor.",
    "Accediendo a los datos, un instante.",
    "Déjeme verificarlo, señor.",
]

_ROUTER_SYSTEM_PROMPT = """Eres un clasificador de intenciones para JARVIS, un asistente de escritorio autónomo.
Tu ÚNICA tarea es analizar el último mensaje del usuario y responder con un JSON.

Responde EXCLUSIVAMENTE con este JSON (sin texto adicional, sin markdown, sin explicaciones):
{
  "intent": "chat" | "tool",
  "stalling_phrase": "..." 
}

REGLAS:
- "chat": El usuario quiere conversar, preguntar algo general, o la respuesta no requiere acceder a herramientas externas, ejecutar comandos, buscar datos o realizar acciones en el sistema.
- "tool": El usuario pide abrir programas, ejecutar comandos, buscar en el sistema, gestionar archivos, agendar recordatorios, o cualquier acción que requiera herramientas.
- "stalling_phrase": Una frase corta y formal en español para decirle al usuario mientras se procesa su solicitud. Solo se usa si intent="tool". Ejemplos: "Un momento señor, ejecutando el comando.", "Verificando los sistemas, señor."
- Si intent="chat", la stalling_phrase puede ser una cadena vacía "".
- Habla SIEMPRE en primera persona, formal, con "señor". Sin emojis."""


async def classify_intent(session_history: list) -> dict:
    """
    Classifies the user's last message as 'chat' or 'tool' using the fast OSS 20B model.
    
    Returns:
        dict with keys: "intent" ("chat" | "tool"), "stalling_phrase" (str)
    """
    global _router_client_idx

    # Build a minimal context: only the last 4 messages + last user message
    recent = session_history[-4:] if len(session_history) > 4 else session_history
    messages_for_router = [
        {"role": "system", "content": _ROUTER_SYSTEM_PROMPT}
    ]
    for msg in recent:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Skip tool calls and tool results — the router only needs conversational context
        if role in ("user", "assistant") and isinstance(content, str) and content:
            messages_for_router.append({"role": role, "content": content[:500]})

    for attempt in range(len(_router_clients)):
        client = _router_clients[_router_client_idx]
        try:
            response = await client.chat.completions.create(
                model=settings.ROUTER_MODEL,
                messages=messages_for_router,
                max_tokens=128,
                temperature=0.1,  # Low temperature for consistent classification
                stream=False,
            )
            raw = (response.choices[0].message.content or "").strip()

            # Clean up potential markdown fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            parsed = json.loads(raw)
            intent = parsed.get("intent", "tool")
            stalling = parsed.get("stalling_phrase", random.choice(FALLBACK_STALLING))

            # Validate intent value
            if intent not in ("chat", "tool"):
                intent = "tool"

            logger.info(f"[ROUTER] Intent clasificado: {intent}")
            return {"intent": intent, "stalling_phrase": stalling}

        except RateLimitError:
            logger.warning(f"[ROUTER] Rate limit en key {_router_client_idx}. Rotando...")
            _router_client_idx = (_router_client_idx + 1) % len(_router_clients)
            continue
        except (json.JSONDecodeError, KeyError) as e:
            # If parsing fails, default to 'tool' to be safe (reasoning model will handle it)
            logger.warning(f"[ROUTER] No se pudo parsear respuesta del router: {e}. Defaulting a 'tool'.")
            return {"intent": "tool", "stalling_phrase": random.choice(FALLBACK_STALLING)}
        except Exception as e:
            logger.error(f"[ROUTER] Error inesperado: {e}", exc_info=True)
            return {"intent": "tool", "stalling_phrase": random.choice(FALLBACK_STALLING)}

    # All keys exhausted — fallback safely
    logger.error("[ROUTER] Todos los clientes Groq agotados. Defaulting a 'tool'.")
    return {"intent": "tool", "stalling_phrase": random.choice(FALLBACK_STALLING)}
