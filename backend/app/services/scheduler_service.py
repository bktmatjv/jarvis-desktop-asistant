"""
Scheduler Service module.
Provides background task execution and timed reminders via APScheduler.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from app.services.connection_manager import manager
import asyncio
from app.services.memory_service import add_message

scheduler = AsyncIOScheduler()

async def push_notification(session_id: str, message: str):
    """
    Se ejecuta cuando se cumple el temporizador. 
    Guarda el mensaje en el historial y lo empuja al cliente de forma proactiva.
    """
    print(f"⏰ [SCHEDULER] Disparando notificación para {session_id}: {message}")
    
    await add_message(session_id, {
        "role": "assistant",
        "content": f"[SYSTEM.NOTIFICATION]: {message}"
    })
    
    await manager.send_personal_message(message, session_id)

def schedule_reminder(session_id: str, message: str, delay_seconds: int):
    """
    Programa una tarea para ejecutarse dentro de X segundos.
    """
    run_date = datetime.now() + timedelta(seconds=delay_seconds)
    print(f" [SCHEDULER] Agendado '{message}' para {run_date} (en {delay_seconds}s)")
    
    scheduler.add_job(
        push_notification,
        'date',
        run_date=run_date,
        args=[session_id, message]
    )
