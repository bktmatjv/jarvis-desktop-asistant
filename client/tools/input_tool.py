import pyautogui

# Desactivar el fail-safe si prefieres que no se detenga al mover el mouse a las esquinas
# pyautogui.FAILSAFE = False 

def keyboard_type(params):
    """Escribe texto simulando pulsaciones de teclas."""
    text = params.get("text", "")
    if text:
        print(f"⌨️ Jarvis escribiendo: {text}")
        pyautogui.write(text, interval=0.05)

def keyboard_shortcut(params):
    """Ejecuta combinaciones como 'ctrl+c' o 'alt+tab'."""
    keys = params.get("keys", "")
    if keys:
        print(f"⌨️ Jarvis ejecutando atajo: {keys}")
        # Divide 'ctrl+c' en ['ctrl', 'c']
        key_list = keys.replace(" ", "").split("+")
        pyautogui.hotkey(*key_list)

def mouse_move(params):
    """Mueve el mouse a coordenadas X, Y."""
    x = params.get("x")
    y = params.get("y")
    if x is not None and y is not None:
        print(f"🖱️ Jarvis moviendo mouse a: {x}, {y}")
        pyautogui.moveTo(x, y, duration=0.25)

def mouse_click(params):
    """Hace clic en la posición actual o en coordenadas específicas."""
    x = params.get("x")
    y = params.get("y")
    if x is not None and y is not None:
        pyautogui.click(x, y)
    else:
        pyautogui.click()
    print("🖱️ Jarvis hizo clic.")

def mouse_scroll(params):
    """Hace scroll. Valores positivos suben, negativos bajan."""
    amount = params.get("amount", 0)
    print(f"🖱️ Jarvis haciendo scroll: {amount}")
    pyautogui.scroll(amount)