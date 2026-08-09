"""
Client Connection module.
Manages the WebSocket connection to the backend server and dispatches incoming actions.
"""
import asyncio
import websockets
import json
import traceback
import os
from dotenv import load_dotenv
from pathlib import Path

# Cargar .env desde la raíz del proyecto
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class JarvisConnection:
    def __init__(self):
        # Leemos BACKEND_URL del .env, si no existe usamos un valor por defecto seguro
        self.uri = os.getenv("BACKEND_URL", "ws://127.0.0.1:8000/ws")
        self.websocket = None
        self.running = False
        
    def set_executor(self, execute_func):
        self.execute_from_server = execute_func

    async def connect(self):
        self.running = True
        while self.running:
            try:
                print(f"🔌 Conectando a {self.uri}...")
                async with websockets.connect(self.uri) as ws:
                    self.websocket = ws
                    print("✅ Conectado al servidor JARVIS.")
                    
                    handshake = {
                        "type": "handshake",
                        "client_id": "hud_desktop",
                        "os": "linux",
                        "capabilities": ["bash_repl", "ui_render", "audio_record"]
                    }
                    await self.websocket.send(json.dumps(handshake))
                    
                    await self.receive_loop()
            except websockets.exceptions.ConnectionClosed:
                print("❌ Conexión cerrada. Reintentando en 5 segundos...")
            except Exception as e:
                print(f"⚠️ Error de conexión: {e}. Reintentando en 5 segundos...")
            
            if self.running:
                await asyncio.sleep(5)

    async def receive_loop(self):
        try:
            async for message in self.websocket:
                try:
                    payload = json.loads(message)
                    print(f"📥 Servidor envió: {payload}")
                    
                    if hasattr(self, 'execute_from_server'):
                        response = await self.execute_from_server(payload)
                        if response is not None:
                            await self.websocket.send(json.dumps(response))
                        
                except json.JSONDecodeError:
                    print("⚠️ Recibido mensaje no JSON del servidor.")
                except Exception as e:
                    print(f"⚠️ Error procesando comando: {e}")
                    traceback.print_exc()
        except websockets.exceptions.ConnectionClosedError:
            print("❌ Conexión perdida.")

    async def send_event(self, event_data: dict):
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(event_data))
            except Exception as e:
                print(f"⚠️ Error enviando evento: {e}")
        else:
            print("⚠️ No se pudo enviar el evento, WebSocket desconectado.")

connection_instance = JarvisConnection()
