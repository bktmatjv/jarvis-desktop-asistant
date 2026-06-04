import platform

# Detectamos el sistema operativo al iniciar
OS_NAME = platform.system()

if OS_NAME == "Windows":
    # Importamos la lógica de ventanas para Windows (usando pywinauto)
    from .system.windows.window import (
        list_windows,
        focus_window,
        minimize_window,
        maximize_window,
        close_window
    )
elif OS_NAME == "Linux":
    # Importamos la lógica de ventanas para Linux (usando wmctrl / xdotool)
    from .system.linux.window import (
        list_windows,
        focus_window,
        minimize_window,
        maximize_window,
        close_window
    )
else:
    print(f"⚠️ Jarvis: Sistema operativo no soportado para window_tool ({OS_NAME})")
    
    # Fallbacks vacíos para evitar crashes
    def list_windows(params=None): return []
    def focus_window(params): pass
    def minimize_window(params): pass
    def maximize_window(params): pass
    def close_window(params): pass