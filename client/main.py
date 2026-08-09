"""
Client Main module.
Entry point for the JARVIS desktop client. 
Initializes the PyWebView UI, global hotkeys, and the WebSocket connection.
"""
import os
import webview
from pynput import keyboard
import psutil
import threading
from datetime import datetime
import asyncio
import sys
import json

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from connection import connection_instance
from executor.executor import execute_from_server, resolve_security


window = None
is_visible = True
ws_loop = None

def ui_print(msg):
    """Imprime en la consola y lo envía al HUD en tiempo real"""
    print(msg) 
    
    if window:
        try:
            safe_msg = json.dumps(str(msg))
            window.evaluate_js(f"addLog({safe_msg})")
        except Exception:
            pass

def update_ui_response(text):
    """Actualiza la caja principal de respuesta en el HUD"""
    if window:
        try:
            safe_msg = json.dumps(str(text))
            window.evaluate_js(f"updateJarvisResponse({safe_msg})")
        except Exception:
            pass

def set_action_status(command_text):
    """Muestra en la interfaz web el comando exacto que Jarvis está ejecutando"""
    if window:
        try:
            safe_msg = json.dumps(str(command_text))
            window.evaluate_js(f"showSystemAction({safe_msg})")
        except Exception:
            pass

def show_action_output(output_text):
    """Muestra en la interfaz web el resultado del comando ejecutado"""
    if window:
        try:
            # Acortamos para no saturar el DOM si el output es inmenso
            max_len = 1500
            if len(output_text) > max_len:
                output_text = output_text[:max_len] + "\n...[OUTPUT TRUNCADO]..."
            safe_msg = json.dumps(str(output_text))
            window.evaluate_js(f"showCommandOutput({safe_msg})")
        except Exception:
            pass


class JarvisAPI:
    def __init__(self):
        print("🧠 Cliente Jarvis inicializado y listo.")
        psutil.cpu_percent(interval=None) 

    def get_system_data(self):
        """Retorna los signos vitales de la PC y el saludo dinámico"""
        hora = datetime.now().hour
        if 5 <= hora < 12:
            saludo = "BUENOS DÍAS"
        elif 12 <= hora < 19:
            saludo = "BUENAS TARDES"
        else:
            saludo = "BUENAS NOCHES"

        cpu_usage = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        ram_used_gb = round(ram.used / (1024**3), 1)
        ram_total_gb = round(ram.total / (1024**3), 1)

        return {
            "greeting": f"{saludo}, MATIAS JAVIER.",
            "cpu": cpu_usage,
            "ram_used": ram_used_gb,
            "ram_total": ram_total_gb,
            "ram_percent": ram.percent
        }

    def send_command(self, user_input):
        """Enviado desde el frontend JS cuando se presiona Enter"""
        user_input = user_input.strip()
        if not user_input: return "Vacío"
            
        ui_print(f"👤 CMD: {user_input}")

        event = {
            "type": "message",
            "content": user_input
        }
        
        if ws_loop:
            asyncio.run_coroutine_threadsafe(connection_instance.send_event(event), ws_loop)
            
        return "COMANDO ENVIADO AL SERVIDOR..."

    def security_response(self, is_allowed):
        """Llamado desde JS cuando el usuario hace clic en Permitir/Denegar"""
        # Debe llamar al evento de asyncio pero thread-safe
        if ws_loop:
            ws_loop.call_soon_threadsafe(resolve_security, is_allowed)

    def hide_ui(self):
        hide_widget()




def hide_widget():
    global is_visible, window
    if window and is_visible:
        window.hide()
        is_visible = False

def show_widget():
    global is_visible, window
    if window and not is_visible:
        window.show()
        is_visible = True

def toggle_window():
    global is_visible
    if is_visible:
        hide_widget()
    else:
        show_widget()

def start_websocket_loop():
    global ws_loop
    ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ws_loop)
    
    connection_instance.set_executor(execute_from_server)
    ws_loop.run_until_complete(connection_instance.connect())

if __name__ == '__main__':
    sys.modules['main'] = sys.modules[__name__]

    api = JarvisAPI()

    hotkey_listener = keyboard.GlobalHotKeys({
        '<ctrl>+<space>': toggle_window
    })
    hotkey_listener.start()

    threading.Thread(target=start_websocket_loop, daemon=True).start()

    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'index.html')
    window = webview.create_window(
        title='JARVIS', 
        url=html_path,
        js_api=api,
        width=1024,
        height=576,
        frameless=True,       
        transparent=True,     
        on_top=True           
    )
    
    print("GOD -> JARVIS listo. Presiona 'Ctrl + Espacio' para invocarlo.")
    webview.start()