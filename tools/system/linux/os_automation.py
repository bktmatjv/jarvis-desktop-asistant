import subprocess
import time

def automate_program(params):
    # Parámetros adaptados por defecto a Linux (ej: gedit en vez de notepad)
    executable = params.get("executable", "gedit")
    window_title = params.get("window_title", ".*")
    text_to_type = params.get("text", "")

    print(f"⚙️ Jarvis intentando abrir y controlar: {executable} en Linux...")

    try:
        # Abre el programa
        subprocess.Popen([executable], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)  # Pausa para que el OS renderice la ventana (X11 / Wayland)

        # Busca la ventana y la trae al frente usando xdotool
        try:
            print(f"🔍 Jarvis buscando ventana activa...")
            # Si pasaste un título específico, xdotool puede buscarlo y activarlo:
            if window_title != ".*":
                subprocess.run(["xdotool", "search", "--name", window_title, "windowactivate"], check=False)
        except Exception as ex:
            print(f"⚠️ No se pudo enfocar la ventana por título. {ex}")

        # Si Jarvis tiene algo que escribir, lo inyecta
        if text_to_type:
            print("✍️ Jarvis está escribiendo en el sistema (vía xdotool)...")
            
            # xdotool inyecta el texto simulando pulsaciones
            subprocess.run(["xdotool", "type", "--delay", "50", text_to_type])
            
            # Presionamos Enter al final
            subprocess.run(["xdotool", "key", "Return"])
            
        print("✅ Acción de sistema operativo completada en Linux.")

    except FileNotFoundError:
        print("ERROR: Error Crítico: Necesitas instalar 'xdotool' en Linux para simular teclado/mouse.")
        print("   -> Ejecuta: sudo apt install xdotool")
    except Exception as e:
        print(f"ERROR: Error al intentar controlar el sistema en Linux: {e}")