"""
Router Service module — JARVIS 2.5 Loop Engineering.
Classifies user intent into specialized domains (chat, system, research, media)
and generates human stalling phrases for non-chat actions.
"""
import json
import random
from groq import AsyncGroq, RateLimitError
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("router_service")

# Build router clients from segregated FAST keys pool
_fast_keys = settings.get_fast_keys()
if not _fast_keys:
    _fast_keys = [settings.GROQ_API_KEY] if settings.GROQ_API_KEY else []

_router_clients = [AsyncGroq(api_key=key) for key in _fast_keys] if _fast_keys else []
_router_client_idx = 0

FALLBACK_STALLING = [
    "Dame un segundo, revisando eso.",
    "Un momento, procesando la solicitud.",
    "Déjame ver qué encuentro.",
    "A la orden, dame un instante.",
    "Revisando los sistemas, espérame un momento."
]

_ROUTER_SYSTEM_PROMPT = """Eres el clasificador de intenciones de JARVIS.
Analiza el último mensaje y responde EXCLUSIVAMENTE con este JSON:
{"domain": "chat"|"system"|"research"|"media", "stalling_phrase": "frase corta casual en español o vacía si es chat"}

Reglas:
- "chat": Charla general, saludos, ayuda conceptual o preguntas directas sin necesidad de herramientas.
- "system": Abrir programas, volumen, ventanas, hardware, comandos de terminal o telemetría.
- "research": Búsquedas en internet, noticias, clima o consultar datos web en tiempo real.
- "media": Reproducir música, canciones en YouTube Music o pausar/cambiar pistas.
- "stalling_phrase": Frase humana, breve y casual (sin emojis). Si domain="chat", déjala vacía ""."""


async def classify_intent(session_history: list) -> dict:
    """
    Classifies the user's intent into a domain and produces a stalling phrase.
    Returns:
        dict: {"intent": "chat"|"tool", "domain": "chat"|"system"|"research"|"media", "stalling_phrase": str}
    """
    global _router_client_idx

    if not _router_clients:
        logger.warning("[ROUTER] No hay clientes de Groq configurados para router. Defaulting a 'tool'.")
        return {"intent": "tool", "domain": "system", "stalling_phrase": random.choice(FALLBACK_STALLING)}

    # Minimal context: only last 3 messages to minimize tokens
    recent = session_history[-3:] if len(session_history) > 3 else session_history
    messages_for_router = [{"role": "system", "content": _ROUTER_SYSTEM_PROMPT}]
    for msg in recent:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant") and isinstance(content, str) and content:
            messages_for_router.append({"role": role, "content": content[:300]})

    for attempt in range(len(_router_clients)):
        client = _router_clients[_router_client_idx]
        try:
            response = await client.chat.completions.create(
                model=settings.ROUTER_MODEL,
                messages=messages_for_router,
                response_format={"type": "json_object"},
                max_tokens=128,
                temperature=0.1,
                stream=False,
            )
            raw = (response.choices[0].message.content or "").strip()

            parsed = json.loads(raw)
            domain = parsed.get("domain", "system").lower()
            if domain not in ("chat", "system", "research", "media"):
                domain = "system"

            stalling = parsed.get("stalling_phrase", "").strip()
            if domain != "chat" and not stalling:
                stalling = random.choice(FALLBACK_STALLING)

            intent = "chat" if domain == "chat" else "tool"

            logger.info(f"[ROUTER] Dominio: {domain} | Intent: {intent}")
            return {
                "intent": intent,
                "domain": domain,
                "stalling_phrase": stalling
            }

        except RateLimitError:
            logger.warning(f"[ROUTER] Rate limit en key {_router_client_idx}. Rotando...")
            _router_client_idx = (_router_client_idx + 1) % len(_router_clients)
            continue
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"[ROUTER] Error parseando respuesta: {e}. Defaulting a 'tool'.")
            return {"intent": "tool", "domain": "system", "stalling_phrase": random.choice(FALLBACK_STALLING)}
        except Exception as e:
            logger.error(f"[ROUTER] Excepción inesperada: {e}", exc_info=True)
            return {"intent": "tool", "domain": "system", "stalling_phrase": random.choice(FALLBACK_STALLING)}

    logger.error("[ROUTER] Todos los clientes Groq agotados. Defaulting a 'tool'.")
    return {"intent": "tool", "domain": "system", "stalling_phrase": random.choice(FALLBACK_STALLING)}

