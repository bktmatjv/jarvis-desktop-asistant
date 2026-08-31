import sys
import json
import pyautogui

# Desactivar failsafe ya que solo enviaremos teclas virtuales multimedia
pyautogui.FAILSAFE = False

def main():
    if len(sys.argv) < 2:
        print("Error: Falta el archivo de parámetros JSON.")
        sys.exit(1)
        
    try:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            params = json.load(f)
    except Exception as e:
        print(f"Error leyendo parámetros: {e}")
        sys.exit(1)
        
    action = params.get("action")
    if not action:
        print("Error: acción no proporcionada en los parámetros.")
        sys.exit(1)
        
    print(f" Ejecutando control multimedia: {action}")
    
    if action == "play_pause":
        pyautogui.press('playpause')
    elif action == "next":
        pyautogui.press('nexttrack')
    elif action == "previous":
        pyautogui.press('prevtrack')
    elif action == "volume_up":
        # Subimos el volumen unas cuantas veces para que el cambio sea notable
        pyautogui.press(['volumeup', 'volumeup', 'volumeup', 'volumeup'])
    elif action == "volume_down":
        pyautogui.press(['volumedown', 'volumedown', 'volumedown', 'volumedown'])
    else:
        print(f"Acción desconocida: {action}")
        sys.exit(1)

    print(f" Comando '{action}' enviado exitosamente.")

if __name__ == "__main__":
    main()
