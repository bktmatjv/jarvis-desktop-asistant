import sys
import json
import os
import platform

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

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

    action = params.get("action", "list")
    title = params.get("title", "")
    is_windows = platform.system() == "Windows"

    if action == "list":
        if is_windows:
            try:
                from pywinauto import Desktop
                desktop = Desktop(backend="uia")
                windows = desktop.windows(visible_only=True)
                titles = [v.window_text().strip() for v in windows if v.window_text().strip()]
                ignored = {"Program Manager", "Task View", "Barra de tareas", "Default IME", "MSCTFIME UI"}
                clean_titles = [t for t in titles if t not in ignored and len(t) > 1]
                print(f"Ventanas abiertas ({len(clean_titles)}):\n" + "\n".join([f"- {t}" for t in clean_titles[:15]]))
            except Exception as e:
                print(f"Error al listar ventanas en Windows: {e}")
        else:
            import subprocess
            try:
                res = subprocess.check_output(["wmctrl", "-l"], text=True)
                print("Ventanas abiertas (Linux):\n" + res)
            except Exception as e:
                print(f"wmctrl no disponible en Linux: {e}")

    elif action in ("focus", "minimize", "maximize", "close"):
        if not title:
            print(f"Error: La acción '{action}' requiere el parámetro 'title'.")
            sys.exit(1)

        if is_windows:
            try:
                import pywinauto
                from pywinauto import Desktop
                regex = f".*{title}.*"
                desktop = Desktop(backend="uia")
                win = desktop.window(title_re=regex, visible_only=True, found_index=0)

                if action == "focus":
                    win.set_focus()
                    print(f"Ventana '{title}' enfocada y traída al frente.")
                elif action == "minimize":
                    win.minimize()
                    print(f"Ventana '{title}' minimizada.")
                elif action == "maximize":
                    win.maximize()
                    print(f"Ventana '{title}' maximizada.")
                elif action == "close":
                    win.close()
                    print(f"Ventana '{title}' cerrada.")
            except pywinauto.findwindows.ElementNotFoundError:
                print(f"No se encontró ninguna ventana activa que coincida con '{title}'.")
            except Exception as e:
                print(f"Error ejecutando '{action}' sobre '{title}': {e}")
        else:
            import subprocess
            try:
                if action == "focus":
                    subprocess.run(["wmctrl", "-a", title], check=True)
                    print(f"Ventana '{title}' enfocada en Linux.")
                elif action == "close":
                    subprocess.run(["wmctrl", "-c", title], check=True)
                    print(f"Ventana '{title}' cerrada en Linux.")
                else:
                    print(f"Acción '{action}' no implementada para Linux.")
            except Exception as e:
                print(f"Error en wmctrl: {e}")
    else:
        print(f"Acción desconocida: '{action}'.")

if __name__ == "__main__":
    main()
