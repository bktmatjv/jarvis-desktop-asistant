import os
import subprocess
from utils.program_indexer import find_program

def open_program(params):
    program_name = params.get("program")
    if not program_name: return
    
    ruta_exacta = find_program(program_name)
    if ruta_exacta and os.path.exists(ruta_exacta):
        print(f" Jarvis detectó la ruta en caché: {ruta_exacta}")
        try:
            # En Linux usamos Popen pasándole la lista del comando
            subprocess.Popen([ruta_exacta], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f" '{program_name}' se ha iniciado correctamente.")
        except Exception as e:
            print(f" Jarvis: Error al ejecutar el binario en Linux: {e}")
    else:
        print(f" '{program_name}' no está en el índice. Intentando ejecución directa usando el PATH...")
        try:
            # Si es un comando global instalado (ej: firefox, gedit, terminal)
            subprocess.Popen([program_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f" '{program_name}' iniciado desde el PATH.")
        except Exception as e:
            print(f" Jarvis no pudo encontrar ni abrir '{program_name}'.")

def shutdown_system(params=None):
    print("️ Jarvis: Iniciando secuencia de apagado (Linux)...")
    os.system("shutdown +1") # Apaga en 1 minuto por seguridad

def restart_system(params=None):
    print(" Jarvis: Iniciando reinicio del sistema (Linux)...")
    os.system("shutdown -r +1")

def sleep_system(params=None):
    print(" Jarvis: Suspendiendo el sistema (Linux)...")
    os.system("systemctl suspend")

def lock_system(params=None):
    print(" Jarvis: Bloqueando la sesión de usuario (Linux)...")
    os.system("loginctl lock-session")

def control_volume(params):
    action = params.get("action")
    value = params.get("value")
    if not action: return

    try:
        if action == "mute":
            os.system("amixer -D pulse sset Master toggle")
            print(" Jarvis: Volumen muteado/desmuteado (Linux).")
            
        elif action == "up":
            os.system("amixer -D pulse sset Master 10%+")
            print(" Jarvis: Volumen subido (Linux).")
            
        elif action == "down":
            os.system("amixer -D pulse sset Master 10%-")
            print(" Jarvis: Volumen bajado (Linux).")
            
        elif action == "set" and value is not None:
            safe_value = max(0, min(100, int(value)))
            os.system(f"amixer -D pulse sset Master {safe_value}%")
            print(f" Jarvis: Volumen establecido al {safe_value}% (Linux).")
            
    except Exception as e:
        print(f" Jarvis: Error crítico en el módulo de audio de Linux: {e}")