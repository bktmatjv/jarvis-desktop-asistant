"""
Client Main module.
Entry point for the JARVIS desktop client. 
Initializes the PyWebView UI (Orb and Panel), global hotkeys, and the WebSocket connection.
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
import time
import wake_word
import stt_engine
import voice_engine

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from connection import connection_instance
from executor.executor import execute_from_server, resolve_security

orb_window = None
panel_window = None
orb_visible = False
panel_visible = False
ws_loop = None
last_activity = time.time()
SLEEP_TIMEOUT = 10 # El orbe se oculta a los 10 segundos de inactividad

def reset_activity():
    global last_activity
    last_activity = time.time()

def _run_voice_command():
    # Pausamos Vosk para que no escuche doble ni haya conflictos
    try:
        wake_word.set_listening_state(False)
    except Exception:
        pass
    
    def on_start():
        if orb_window:
            try:
                orb_window.evaluate_js("listeningUI()")
            except:
                pass
                
    texto = stt_engine.record_and_transcribe(on_listening_start=on_start)
    
    if orb_window:
        try:
            orb_window.evaluate_js("resetHUD()")
        except:
            pass
            
    if texto:
        global api
        api.send_command(texto)
    else:
        # STT timed out or detected no voice — give audio feedback
        voice_engine.speak("No le escuché, señor.")
        reset_activity()
        
    # Reanudamos Vosk
    try:
        wake_word.set_listening_state(True)
    except Exception:
        pass

def wake_up_jarvis():
    reset_activity()
    show_orb()
    if orb_window:
        try:
            orb_window.evaluate_js("wakeUpUI()")
        except:
            pass

    import random
    # Short, varied acknowledgements
    acks = ["Dime", "¿Qué necesitas?", "Te escucho", "Dígame"]
    voice_engine.speak(random.choice(acks))
    
    # Lanzar la escucha activa en un hilo separado
    threading.Thread(target=_run_voice_command, daemon=True).start()


def ui_print(msg):
    """Imprime en la consola y lo envía al Panel en tiempo real"""
    print(msg)
    # NOTA: NO llamamos reset_activity() aquí porque ui_print se dispara
    # en cada mensaje del servidor, lo que impediría que el orbe se durmiera.
    
    if panel_window:
        try:
            safe_msg = json.dumps(str(msg))
            panel_window.evaluate_js(f"addLog({safe_msg})")
        except Exception:
            pass

def update_ui_response(text):
    """Actualiza la respuesta en el Panel (y opcionalmente en el Orbe si tiene texto)"""
    if panel_window:
        try:
            safe_msg = json.dumps(str(text))
            panel_window.evaluate_js(f"updateJarvisResponse({safe_msg})")
        except Exception:
            pass

def set_action_status(command_text):
    """Muestra en el Panel el comando exacto que Jarvis está ejecutando"""
    if panel_window:
        try:
            safe_msg = json.dumps(str(command_text))
            panel_window.evaluate_js(f"showSystemAction({safe_msg})")
        except Exception:
            pass

def show_action_output(output_text):
    """Muestra en el Panel el resultado del comando ejecutado"""
    if panel_window:
        try:
            # Acortamos para no saturar el DOM si el output es inmenso
            max_len = 1500
            if len(output_text) > max_len:
                output_text = output_text[:max_len] + "\n...[OUTPUT TRUNCADO]..."
            safe_msg = json.dumps(str(output_text))
            panel_window.evaluate_js(f"showCommandOutput({safe_msg})")
        except Exception:
            pass


def update_loop_step(payload):
    """Actualiza la visualización de Loop Engineering en el Panel en tiempo real"""
    if panel_window:
        try:
            safe_payload = json.dumps(payload)
            panel_window.evaluate_js(f"updateLoopProcess({safe_payload})")
        except Exception:
            pass


class JarvisAPI:
    def __init__(self):
        print(" Cliente Jarvis inicializado y listo.")
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

        user_name = os.getenv("USER_NAME", "USUARIO").upper()
        user_role = os.getenv("USER_ROLE", "usuario").upper()
        cpu_usage = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        ram_used_gb = round(ram.used / (1024**3), 1)
        ram_total_gb = round(ram.total / (1024**3), 1)

        import platform
        return {
            "greeting": f"{saludo}, {user_name}.",
            "cpu": cpu_usage,
            "ram_used": ram_used_gb,
            "ram_total": ram_total_gb,
            "ram_percent": ram.percent,
            "username": user_name,
            "role": user_role,
            "device_name": platform.node().upper() or "JARVIS-HOST"
        }


    def send_command(self, user_input):
        """Enviado desde el frontend JS cuando se presiona Enter o por Voz"""
        reset_activity()
        user_input = user_input.strip()
        if not user_input: return ""
            
        ui_print(f" CMD: {user_input}")
        update_loop_step({"step": "ingestion", "status": "active", "detail": f"Input: {user_input[:35]}"})

        event = {
            "type": "message",
            "content": user_input
        }
        
        if ws_loop:
            asyncio.run_coroutine_threadsafe(connection_instance.send_event(event), ws_loop)
            
        return ""

    def update_hotkey(self, hotkey):
        """Actualiza el hotkey global registrado."""
        print(f" Hotkey actualizado a: {hotkey}")
        return True

    def security_response(self, is_allowed):
        """Llamado desde JS cuando el usuario hace clic en Permitir/Denegar"""
        if ws_loop:
            ws_loop.call_soon_threadsafe(resolve_security, is_allowed)

    def hide_ui(self):
        hide_orb()
        hide_panel()
        
    def minimize_window(self):
        global panel_window
        if panel_window:
            try:
                panel_window.minimize()
            except Exception:
                pass
            
    def maximize_window(self):
        pass

    def close_window(self):
        hide_orb()
        hide_panel()



# --- Controles de Ventanas ---

def hide_orb():
    global orb_visible, orb_window
    if orb_window and orb_visible:
        orb_window.hide()
        orb_visible = False
        try:
            wake_word.set_listening_state(True)
        except Exception:
            pass

def show_orb():
    global orb_visible, orb_window
    reset_activity()
    if orb_window and not orb_visible:
        orb_window.show()
        orb_visible = True
        try:
            wake_word.set_listening_state(True)
        except Exception:
            pass

def toggle_orb():
    global orb_visible
    if orb_visible:
        hide_orb()
    else:
        wake_up_jarvis()

def toggle_panel():
    global panel_visible, panel_window
    if panel_visible:
        panel_window.hide()
        panel_visible = False
    else:
        panel_window.show()
        panel_visible = True

# -----------------------------

def start_websocket_loop():
    global ws_loop
    ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ws_loop)
    
    connection_instance.set_executor(execute_from_server)
    ws_loop.run_until_complete(connection_instance.connect())

def inactivity_checker():
    global orb_visible
    while True:
        time.sleep(1)
        if orb_visible and (time.time() - last_activity > SLEEP_TIMEOUT):
            # 1. Primero animamos el sleep mientras la ventana aún es visible
            if orb_window:
                try:
                    orb_window.evaluate_js("sleepUI()")
                except:
                    pass
            # 2. Esperamos un momento para que la animación de salida ocurra
            time.sleep(0.8)
            # 3. Luego ocultamos la ventana
            hide_orb()

if __name__ == '__main__':
    sys.modules['main'] = sys.modules[__name__]

    api = JarvisAPI()

    hotkey_listener = keyboard.GlobalHotKeys({
        '<ctrl>+<space>': toggle_orb,
        '<ctrl>+<up>': toggle_panel
    })
    hotkey_listener.start()

    threading.Thread(target=start_websocket_loop, daemon=True).start()
    threading.Thread(target=inactivity_checker, daemon=True).start()
    
    # Iniciar motor de Wake Word
    wake_word.start_listening(wake_up_jarvis)

    DEV_MODE = False
    if DEV_MODE:
        orb_url = "http://localhost:5173/?mode=orb"
        panel_url = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'index.html')
    else:
        import pathlib
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Generar URLs file:// válidas para Windows. Se usa '#' en vez de '?' porque los archivos locales no soportan query strings en Windows.
        orb_path = os.path.join(base_dir, 'frontend', 'dist', 'index.html')
        orb_url = pathlib.Path(orb_path).as_uri() + "#mode=orb"
        
        panel_path = os.path.join(base_dir, 'web', 'index.html')
        panel_url = pathlib.Path(panel_path).as_uri()

    # 1. Ventana del Panel (Vanilla JS)
    panel_window = webview.create_window(
        title="JARVIS Panel de Control",
        url=panel_url,
        js_api=api,
        width=1280,
        height=720,
        hidden=False, # Ahora inicia visible por defecto
        resizable=True,
    )

    # 2. Ventana del Orbe (React Vite)
    orb_window = webview.create_window(
        title="JARVIS",
        url=orb_url,
        js_api=api,
        width=300,
        height=300,
        x=50,
        y=50,
        frameless=True,       
        transparent=True,     
        on_top=True,
        resizable=False,
        hidden=True # El orbe inicia oculto hasta que dices Jarvis
    )
    
    def startup_greeting():
        import time
        time.sleep(3.0) 
        try:
            greeting = api.get_system_data()["greeting"]
            voice_engine.speak_streaming(greeting)
        except Exception as e:
            print(f"Error en saludo inicial: {e}")

    threading.Thread(target=startup_greeting, daemon=True).start()
    print("GOD -> JARVIS listo. Presiona 'Ctrl + Espacio' para el Orbe, y 'Ctrl + Flecha Arriba' para el Panel.")
    
    # Inicia el loop de la interfaz
    webview.start()