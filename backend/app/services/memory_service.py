"""
Memory Service module.
Handles long-term conversation history storage in MongoDB.
"""
import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client.jarvis_db
sessions_collection = db.sessions

async def get_recent_history(session_id: str, limit: int = 10) -> list:
    """
    Obtiene los últimos N mensajes de la sesión para el contexto del LLM (Sliding Window).
    """
    session = await sessions_collection.find_one({"session_id": session_id})
    if not session or "messages" not in session:
        return []
        
    messages = session["messages"]
    return messages[-limit:] if limit > 0 else messages

async def add_message(session_id: str, message: dict):
    """
    Añade un mensaje al array de mensajes de una sesión.
    Crea la sesión si no existe.
    """
    message["timestamp"] = datetime.datetime.utcnow().isoformat()
    
    await sessions_collection.update_one(
        {"session_id": session_id},
        {
            "$push": {"messages": message},
            "$setOnInsert": {"created_at": datetime.datetime.utcnow().isoformat()}
        },
        upsert=True
    )
