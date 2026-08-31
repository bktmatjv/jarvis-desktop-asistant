"""
Memory Service module.
Handles long-term conversation history storage in MongoDB.
"""
import datetime
import certifi
import traceback
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

try:
    client = AsyncIOMotorClient(settings.MONGO_URI, tlsCAFile=certifi.where(), tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=3000)
    db = client.jarvis_db
    sessions_collection = db.sessions
    user_memories_collection = db.user_memories
except Exception as e:
    print(f"Advertencia: No se pudo conectar a MongoDB. Usando fallback en memoria. Error: {e}")
    sessions_collection = None
    user_memories_collection = None


# Fallback en memoria si falla MongoDB
in_memory_sessions = {}
mongo_is_down = False

async def get_recent_history(session_id: str, limit: int = 10) -> list:
    """
    Obtiene los últimos N mensajes de la sesión para el contexto del LLM (Sliding Window).
    """
    global mongo_is_down
    if sessions_collection is not None and not mongo_is_down:
        try:
            session = await sessions_collection.find_one({"session_id": session_id})
            if session and "messages" in session:
                messages = session["messages"]
                return messages[-limit:] if limit > 0 else messages
        except Exception as e:
            print(f"Error MongoDB (Lectura): {e}. Desactivando MongoDB y usando fallback.")
            mongo_is_down = True
            
    session = in_memory_sessions.get(session_id, {})
    messages = session.get("messages", [])
    return messages[-limit:] if limit > 0 else messages

async def add_message(session_id: str, message: dict):
    """
    Añade un mensaje al array de mensajes de una sesión.
    Crea la sesión si no existe.
    """
    global mongo_is_down
    message["timestamp"] = datetime.datetime.utcnow().isoformat()
    
    if sessions_collection is not None and not mongo_is_down:
        try:
            await sessions_collection.update_one(
                {"session_id": session_id},
                {
                    "$push": {"messages": message},
                    "$setOnInsert": {"created_at": datetime.datetime.utcnow().isoformat()}
                },
                upsert=True
            )
            return
        except Exception as e:
            print(f"Error MongoDB (Escritura): {e}. Desactivando MongoDB y guardando en memoria.")
            mongo_is_down = True
            
    if session_id not in in_memory_sessions:
        in_memory_sessions[session_id] = {"messages": []}
    in_memory_sessions[session_id]["messages"].append(message)

async def save_memory(fact: str) -> str:
    """Guarda un hecho importante en la memoria a largo plazo."""
    if user_memories_collection is not None and not mongo_is_down:
        try:
            doc = {
                "fact": fact,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            await user_memories_collection.insert_one(doc)
            return f"Hecho guardado en la memoria a largo plazo: {fact}"
        except Exception as e:
            return f"Error guardando en memoria (MongoDB): {e}"
    else:
        return "No se pudo guardar: MongoDB no está disponible."

async def search_memory(query: str) -> str:
    """Busca en la memoria a largo plazo usando expresiones regulares simples."""
    if user_memories_collection is not None and not mongo_is_down:
        try:
            # Búsqueda muy básica con regex (case-insensitive) sobre el campo 'fact'
            import re
            pattern = re.compile(query, re.IGNORECASE)
            cursor = user_memories_collection.find({"fact": {"$regex": pattern}}).sort("timestamp", -1).limit(10)
            results = await cursor.to_list(length=10)
            
            if not results:
                return f"No se encontraron recuerdos coincidentes con: {query}"
                
            formatted = "\n".join([f"- {r['fact']} (guardado el {r['timestamp'][:10]})" for r in results])
            return f"Recuerdos encontrados:\n{formatted}"
        except Exception as e:
            return f"Error buscando en memoria (MongoDB): {e}"
    else:
        return "No se pudo buscar: MongoDB no está disponible."


# ---------------------------------------------------------------------------
# Tool Result Cache — avoids re-executing heavy tools on follow-up questions
# ---------------------------------------------------------------------------

# In-memory fallback cache with a fixed max size (LRU-like via simple dict)
from collections import OrderedDict
_tool_result_cache: OrderedDict = OrderedDict()
_TOOL_CACHE_MAX = 50  # max entries in the in-memory fallback


async def save_tool_result(run_id: str, tool_name: str, result: str) -> None:
    """
    Stores a tool execution result keyed by run_id.
    Useful for follow-up questions on the same data without re-running the tool.
    TTL in MongoDB: 1 hour (requires a TTL index on 'expires_at').
    """
    global mongo_is_down
    doc = {
        "run_id": run_id,
        "tool_name": tool_name,
        "result": result,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "expires_at": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }

    if db is not None and not mongo_is_down:
        try:
            tool_results_col = db.tool_results
            await tool_results_col.update_one(
                {"run_id": run_id},
                {"$set": doc},
                upsert=True
            )
            return
        except Exception as e:
            print(f"Error MongoDB (tool result write): {e}")

    # In-memory fallback
    if len(_tool_result_cache) >= _TOOL_CACHE_MAX:
        _tool_result_cache.popitem(last=False)  # Evict oldest
    _tool_result_cache[run_id] = doc


async def get_tool_result(run_id: str) -> str | None:
    """
    Retrieves a cached tool result by run_id.
    Returns None if not found or expired.
    """
    global mongo_is_down
    if db is not None and not mongo_is_down:
        try:
            tool_results_col = db.tool_results
            doc = await tool_results_col.find_one({"run_id": run_id})
            if doc:
                return doc.get("result")
        except Exception as e:
            print(f"Error MongoDB (tool result read): {e}")

    # In-memory fallback
    cached = _tool_result_cache.get(run_id)
    if cached:
        return cached.get("result")
    return None
