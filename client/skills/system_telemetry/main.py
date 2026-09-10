import sys
import json
import os
import psutil
import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def get_cpu_ram():
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    used_gb = round(mem.used / (1024**3), 2)
    total_gb = round(mem.total / (1024**3), 2)
    return f"CPU: {cpu}% | RAM: {mem.percent}% ({used_gb} GB usados de {total_gb} GB)"

def get_battery():
    battery = psutil.sensors_battery()
    if not battery:
        return "Batería: Dispositivo de escritorio o sin batería detectada."
    status = "conectado al cargador" if battery.power_plugged else "usando batería"
    return f"Batería: {battery.percent}% ({status})"

def get_processes():
    procs = []
    for p in sorted(psutil.process_iter(['name', 'cpu_percent', 'memory_percent']), 
                    key=lambda x: (x.info.get('cpu_percent') or 0), reverse=True)[:5]:
        name = p.info.get('name')
        cpu = p.info.get('cpu_percent')
        mem = round(p.info.get('memory_percent') or 0, 1)
        procs.append(f"- {name}: CPU {cpu}% | RAM {mem}%")
    return "Procesos con mayor consumo:\n" + "\n".join(procs)

def take_screenshot(target_path=None):
    try:
        import pyautogui
        if not target_path:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = os.path.join(desktop, f"screenshot_{timestamp}.png")
        else:
            if not os.path.isabs(target_path):
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                target_path = os.path.join(desktop, target_path)

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        img = pyautogui.screenshot()
        img.save(target_path)
        return f"Captura de pantalla guardada con éxito en: {target_path}"
    except Exception as e:
        return f"Error al tomar captura de pantalla: {e}"

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

    metric = params.get("metric", "all_metrics")
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    if metric == "all_metrics":
        print(f"Fecha y Hora: {now_str}\n{get_cpu_ram()}\n{get_battery()}")
    elif metric == "cpu_ram":
        print(get_cpu_ram())
    elif metric == "battery":
        print(get_battery())
    elif metric == "top_processes":
        print(get_processes())
    elif metric == "screenshot":
        path = params.get("screenshot_path")
        print(take_screenshot(path))
    elif metric == "system_time":
        print(f"Fecha y Hora actual del sistema: {now_str}")
    else:
        print(f"Métrica desconocida: {metric}")

if __name__ == "__main__":
    main()
