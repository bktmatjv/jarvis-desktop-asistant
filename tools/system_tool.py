import platform

# Detectamos el sistema operativo al iniciar la herramienta
OS_NAME = platform.system()

if OS_NAME == "Windows":
    # Importamos desde la nueva ruta tools.system.windows.system
    from .system.windows.system import (
        open_program,
        shutdown_system,
        restart_system,
        sleep_system,
        lock_system,
        control_volume
    )
elif OS_NAME == "Linux":
    # Importamos desde la nueva ruta tools.system.linux.system
    from .system.linux.system import (
        open_program,
        shutdown_system,
        restart_system,
        sleep_system,
        lock_system,
        control_volume
    )
else:
    print(f"⚠️ Jarvis: Sistema operativo no soportado para system_tool ({OS_NAME})")