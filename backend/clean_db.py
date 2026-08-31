import asyncio
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def clean():
    client = AsyncIOMotorClient(settings.MONGO_URI, tlsCAFile=certifi.where())
    db = client.jarvis_db
    await db.sessions.drop()
    print("¡Base de datos limpiada con éxito! El historial gigantesco ha sido borrado.")

if __name__ == "__main__":
    asyncio.run(clean())
