import platform

# Detectamos el sistema operativo
OS_NAME = platform.system()

if OS_NAME == "Windows":
    # Importamos la automatización nativa de Windows (con pywinauto)
    from .system.windows.os_automation import automate_program
elif OS_NAME == "Linux":
    # Importamos la automatización nativa de Linux (con xdotool)
    from .system.linux.os_automation import automate_program
else:
    print(f"⚠️ Jarvis: Sistema operativo no soportado para os_automation_tool ({OS_NAME})")
    
    # Función vacía de fallback para evitar crashes si se usa en Mac u otro SO
    def automate_program(params):
        pass