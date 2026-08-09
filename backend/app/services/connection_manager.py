"""
Connection Manager module.
Maintains a registry of active WebSocket connections to allow proactive server-to-client push messages.
"""
from fastapi import WebSocket
from app.models.schemas import SpeakResponse

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_personal_message(self, message: str, session_id: str):
        if session_id in self.active_connections:
            ws = self.active_connections[session_id]
            resp = SpeakResponse(message=message)
            await ws.send_text(resp.model_dump_json())

manager = ConnectionManager()
