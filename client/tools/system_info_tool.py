import psutil
import datetime
import platform

def get_system_time(params=None):
    """Devuelve la hora y fecha actual."""
    now = datetime.datetime.now()
    time_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%d/%m/%Y")
    print(f"🕒 Jarvis: Son las {time_str} del {date_str}.")
    return {"time": time_str, "date": date_str}

def get_battery_info(params=None):
    """Devuelve el estado de la batería."""
    battery = psutil.sensors_battery()
    if battery is None:
        print("🔌 Jarvis: Esta PC no tiene batería (posiblemente una Desktop).")
        return "No battery detected"
    
    percent = battery.percent
    plugged = battery.power_plugged
    status = "conectado" if plugged else "descargando"
    
    print(f"🔋 Jarvis: Tienes {percent}% de batería y el cargador está {status}.")
    return {"percent": percent, "plugged": plugged}

def get_cpu_usage(params=None):
    """Devuelve el porcentaje de uso del CPU."""
    # interval=1 hace que espere un segundo para dar un promedio real
    usage = psutil.cpu_percent(interval=1)
    print(f"🧠 Jarvis: El uso del CPU es del {usage}%.")
    return {"cpu_usage": usage}

def get_memory_usage(params=None):
    """Devuelve el uso de la memoria RAM."""
    memory = psutil.virtual_memory()
    percent = memory.percent
    # Convertimos bytes a GB para que sea legible
    available_gb = round(memory.available / (1024**3), 2)
    
    print(f"📊 Jarvis: El uso de RAM es del {percent}%. Tienes {available_gb} GB disponibles.")
    return {"ram_usage": percent, "available_gb": available_gb}

def list_running_programs(params=None):
    """Lista los procesos que más CPU están consumiendo actualmente."""
    print("🕵️ Jarvis: Escaneando procesos activos...")
    procesos = []
    # Obtenemos los 5 procesos que más RAM consumen
    for proc in sorted(psutil.process_iter(['name', 'cpu_percent']), key=lambda x: x.info['cpu_percent'], reverse=True)[:5]:
        procesos.append(proc.info)
        print(f" - {proc.info['name']} ({proc.info['cpu_percent']}%)")
    return procesos

def take_screenshot(params):
    """Toma una captura de pantalla y la guarda en el path especificado."""
    path = params.get("path", "desktop/screenshot_jarvis.png")
    # Importamos aquí para no cargar la librería si no se usa
    import pyautogui
    
    # Usamos tu lógica de resolución de rutas que hicimos en filesystem_tool
    from tools.filesystem_tool import _resolve_path
    full_path = _resolve_path(path)
    
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(full_path)
        print(f"📸 Jarvis: Captura de pantalla guardada en '{full_path}'.")
    except Exception as e:
        print(f"❌ Error al tomar captura: {e}")