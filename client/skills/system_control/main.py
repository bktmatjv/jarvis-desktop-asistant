import sys
import json
import os
import subprocess
import platform

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def open_app(program_name):
    if not program_name:
        print("Error: No se especificó el programa.")
        return

    is_windows = platform.system() == "Windows"
    
    # Try program indexer if available
    client_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if client_dir not in sys.path:
        sys.path.insert(0, client_dir)

    exact_path = None
    try:
        from utils.program_indexer import find_program
        exact_path = find_program(program_name)
    except Exception:
        pass

    if exact_path and os.path.exists(exact_path):
        print(f"Iniciando programa desde ruta indexada: {exact_path}")
        if is_windows:
            try:
                os.startfile(os.path.normpath(exact_path))
                print(f"'{program_name}' se ha iniciado correctamente.")
                return
            except Exception:
                subprocess.Popen([exact_path], shell=True)
                print(f"'{program_name}' se ha iniciado mediante subproceso.")
                return
        else:
            subprocess.Popen([exact_path])
            print(f"'{program_name}' iniciado en Linux.")
            return

    # Fallback to direct execution / aliases
    common_aliases = {
        "bloc de notas": "notepad",
        "notepad": "notepad",
        "calculadora": "calc",
        "calc": "calc",
        "chrome": "chrome",
        "google chrome": "chrome",
        "spotify": "spotify",
        "explorador": "explorer",
        "administrador de tareas": "taskmgr",
        "cmd": "cmd",
        "terminal": "powershell" if is_windows else "x-terminal-emulator",
        "code": "code",
        "visual studio code": "code"
    }

    cmd = common_aliases.get(program_name.lower().strip(), program_name)
    try:
        if is_windows:
            subprocess.Popen(f"start {cmd}", shell=True)
        else:
            subprocess.Popen([cmd])
        print(f"Comando de apertura ejecutado: '{cmd}'.")
    except Exception as e:
        print(f"No se pudo iniciar '{program_name}': {e}")

def set_volume(level):
    if level is None:
        print("Error: Nivel de volumen no proporcionado.")
        return
    level = max(0, min(100, int(level)))
    is_windows = platform.system() == "Windows"

    if is_windows:
        try:
            from ctypes import cast, POINTER
            import comtypes
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            print(f"Volumen ajustado al {level}%.")
            return
        except Exception as e:
            print(f"Aviso pycaw: {e}. Intentando ajuste alternativo...")
            try:
                import pyautogui
                # Best-effort fallback
                pyautogui.press('volumeup')
                print(f"Volumen modificado.")
                return
            except Exception:
                pass
    else:
        try:
            subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level}%"], check=True)
            print(f"Volumen ajustado al {level}% (Linux).")
            return
        except Exception as e:
            print(f"Error ajustando volumen con amixer: {e}")

def main():
    if len(sys.argv) < 2:
        print("Error: Se requiere archivo de parámetros JSON.")
        sys.exit(1)

    try:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            params = json.load(f)
    except Exception as e:
        print(f"Error leyendo parámetros: {e}")
        sys.exit(1)

    action = params.get("action")
    is_windows = platform.system() == "Windows"

    if action == "open_program":
        open_app(params.get("program"))
    elif action == "set_volume":
        set_volume(params.get("volume_level"))
    elif action == "shutdown":
        print("Iniciando secuencia de apagado del sistema...")
        if is_windows:
            os.system("shutdown /s /t 10")
        else:
            os.system("shutdown -h +1")
        print("Apagado programado.")
    elif action == "restart":
        print("Iniciando reinicio del sistema...")
        if is_windows:
            os.system("shutdown /r /t 10")
        else:
            os.system("reboot")
        print("Reinicio programado.")
    elif action == "sleep":
        print("Suspendiendo el equipo...")
        if is_windows:
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        else:
            os.system("systemctl suspend")
    elif action == "lock":
        print("Bloqueando sesión...")
        if is_windows:
            os.system("rundll32.exe user32.dll,LockWorkStation")
        else:
            os.system("loginctl lock-session")
        print("Sesión bloqueada.")
    else:
        print(f"Acción desconocida: '{action}'.")

if __name__ == "__main__":
    main()
