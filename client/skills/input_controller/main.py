import sys
import json
import pyautogui

pyautogui.FAILSAFE = False

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

    action = params.get("action")

    if action == "type_text":
        text = params.get("text", "")
        if text:
            pyautogui.write(text, interval=0.03)
            print(f"Texto escrito: '{text}'")
        else:
            print("Error: Texto vacío.")

    elif action == "hotkey":
        keys_str = params.get("keys", "").strip()
        if keys_str:
            key_list = [k.strip().lower() for k in keys_str.replace(" ", "").split("+") if k.strip()]
            pyautogui.hotkey(*key_list)
            print(f"Atajo ejecutado: {' + '.join(key_list)}")
        else:
            print("Error: Atajo no especificado.")

    elif action == "click":
        x = params.get("x")
        y = params.get("y")
        if x is not None and y is not None:
            pyautogui.click(int(x), int(y))
            print(f"Clic realizado en ({x}, {y}).")
        else:
            pyautogui.click()
            print("Clic realizado en la posición actual del cursor.")

    elif action == "move_mouse":
        x = params.get("x")
        y = params.get("y")
        if x is not None and y is not None:
            pyautogui.moveTo(int(x), int(y), duration=0.2)
            print(f"Cursor movido a ({x}, {y}).")
        else:
            print("Error: Coordenadas X e Y requeridas para mover el cursor.")

    elif action == "scroll":
        amount = params.get("scroll_amount", 0)
        pyautogui.scroll(int(amount))
        print(f"Scroll aplicado: {amount}")

    else:
        print(f"Acción de entrada desconocida: '{action}'.")

if __name__ == "__main__":
    main()
