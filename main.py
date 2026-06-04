import os
import webview
# import keyboard 
from pynput import keyboard
import psutil
import threading
from datetime import datetime


# Esto asegura que Python siempre sepa que su carpeta de trabajo es donde está el script
os.chdir(os.path.dirname(os.path.abspath(__file__)))


from brain.planner import plan
from executor.executor import execute
from memory.memory import get_command, remember_command


# Variables globales para el control del widget
window = None
is_visible = True

def ui_print(msg):
    """Imprime en la consola de Windows y lo envía al HUD en tiempo real"""
    print(msg) # Lo sigues viendo en la consola negra normal
    
    if window:
        safe_msg = str(msg).replace("'", "\\'").replace('"', '\\"')
        window.evaluate_js(f"addLog('{safe_msg}')")


class JarvisAPI:
    def __init__(self):
        print("🧠 Cerebro de Jarvis inicializado y listo.")

        psutil.cpu_percent(interval=None) 

    def get_system_data(self):
        """Retorna los signos vitales de la PC y el saludo dinámico"""
        
        # 1. Lógica del saludo según la hora
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
        user_input = user_input.strip()
        if not user_input: return "Vacío"
            
        # 1️⃣ Imprimimos el comando que el usuario ingresó
        ui_print(f"👤 CMD: {user_input}")

        try:
            action = get_command(user_input)

            if not action:
                ui_print("🤖 Consultando al Planner_AI...")
                action = plan(user_input)

            if not action:
                ui_print("⚠️ Error: Unknown action")
                return "No sé cómo hacer eso aún"

            label = action.get("tool") or action.get("action") or "command"
            
            # 2️⃣ Informamos qué herramienta se está usando
            ui_print(f"⚙️ EXECUTING: {label}")

            

            execute(action)
            remember_command(user_input, action)

            # 3️⃣ Éxito
            ui_print("✅ TAREA COMPLETADA")

            respuesta_verbal = action.get("llm_response") or action.get("message") or action.get("reply") or "A sus órdenes."

            return respuesta_verbal


        except Exception as e:
            # 4️⃣ En caso de error, también lo mandamos a la pantallita
            ui_print(f"❌ ERROR: {e}")
            return "Algo salió mal"
    



    def hide_ui(self):
        """Llamado desde la web cuando presionas Escape"""
        hide_widget()

# --- Funciones para controlar la ventana ---

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
    """Reemplaza a tu antigua toggle_window()"""
    global is_visible
    if is_visible:
        hide_widget()
    else:
        show_widget()

if __name__ == '__main__':
    api = JarvisAPI()

    # 👇 NUEVA SINTAXIS DE PYNPUT 👇
    # Creamos el atajo global
    hotkey_listener = keyboard.GlobalHotKeys({
        '<ctrl>+<space>': toggle_window
    })
    # Iniciamos el escuchador en un hilo de fondo
    hotkey_listener.start()
    # 👆 FIN DE LA NUEVA SINTAXIS 👆

    # Reemplaza la creación de tu ventana con estas dimensiones
    window = webview.create_window(
        title='JARVIS', 
        url='web/index.html',
        js_api=api,
        width=1024,           # Escala panorámica ancha
        height=576,           # Proporción 16:9
        frameless=True,       
        transparent=True,     
        on_top=True           
    )
    
    print("GOD -> JARVIS listo. Presiona 'Ctrl + Espacio' para invocarlo.")
    # webview.start() bloquea el hilo principal, manteniendo vivo el programa
    # y permitiendo que el hotkey_listener funcione en segundo plano.
    webview.start()