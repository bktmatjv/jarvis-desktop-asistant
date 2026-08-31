"""
Connection Manager module.
Maintains a registry of active WebSocket connections to allow proactive server-to-client push messages.
"""
from fastapi import WebSocket
from app.models.schemas import SpeakResponse

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.client_meta: dict[str, dict] = {}

    async def connect(self, session_id: str, websocket: WebSocket, meta: dict = None):
        self.active_connections[session_id] = websocket
        if meta:
            self.client_meta[session_id] = meta
        else:
            self.client_meta[session_id] = {"username": "Invitado", "role": "user", "os": "unknown", "device_name": "Unknown"}

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.client_meta:
            del self.client_meta[session_id]

    async def send_personal_message(self, message: str, session_id: str):
        if session_id in self.active_connections:
            ws = self.active_connections[session_id]
            resp = SpeakResponse(message=message)
            await ws.send_text(resp.model_dump_json())

    def get_active_clients_info(self):
        users_map = {}
        for client_id, meta in self.client_meta.items():
            username = meta.get("username", "Invitado")
            role = meta.get("role", "user")
            
            if username not in users_map:
                users_map[username] = {"role": role, "devices": []}
                
            users_map[username]["devices"].append({
                "client_id": client_id,
                "os": meta.get("os", "unknown"),
                "device_name": meta.get("device_name", "Unknown")
            })
            
        users_list = []
        for uname, data in users_map.items():
            users_list.append({
                "username": uname,
                "role": data["role"],
                "devices": data["devices"]
            })
            
        return {
            "total_clients": len(self.active_connections),
            "users": users_list
        }

manager = ConnectionManager()
