"""
Entry point for the FastAPI backend application.
Handles the API initialization and application lifespan (startup/shutdown events).
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.websockets.chat import router as chat_router
from app.services.scheduler_service import scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(title="Jarvis API", version="2.0", lifespan=lifespan)

app.include_router(chat_router)

@app.get("/")
def read_root():
    return {"status": "Jarvis API is running"}
