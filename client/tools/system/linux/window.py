import subprocess

# IMPORTANTE: En Linux, esta herramienta requiere los paquetes 'wmctrl' y 'xdotool'
# Puedes instalarlos ejecutando: sudo apt install wmctrl xdotool

def _get_window_id(title_regex):
    """
    Función helper interna: Usa xdotool para encontrar el ID numérico
    de la ventana permitiendo expresiones regulares (ej: .*Firefox.*).
    """
    try:
        # xdotool search --name busca por título y soporta regex
        result = subprocess.run(
            ["xdotool", "search", "--name", title_regex], 
            capture_output=True, text=True, check=True
        )
        # Retorna el primer ID de la lista que coincida
        ids = result.stdout.strip().split('\n')
        return ids[0] if ids else None
    except subprocess.CalledProcessError:
        return None

def list_windows(params=None):
    """Devuelve una lista de las ventanas visibles actualmente en Linux usando wmctrl."""
    print("👁️ Jarvis está escaneando las ventanas abiertas (Linux)...")
    try:
        result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, check=True)
        
        titulos = []
        for line in result.stdout.splitlines():
            parts = line.split(None, 3)
            if len(parts) >= 4:
                title = parts[3].strip()
                if title not in ["Desktop", "panel", "cinnamon", "gnome-shell"]:
                    titulos.append(title)
                    
        print(f"✅ Se encontraron {len(titulos)} ventanas activas.")
        return titulos
        
    except FileNotFoundError:
        print("ERROR: Error Crítico: Necesitas instalar 'wmctrl' en Linux. (sudo apt install wmctrl)")
        return []
    except Exception as e:
        print(f"ERROR: Error al listar ventanas en Linux: {e}")
        return []

def focus_window(params):
    """Trae una ventana al frente en Linux."""
    title = params.get("title")
    if not title: return
        
    print(f"🔍 Jarvis buscando ventana para enfocar: '{title}'...")
    win_id = _get_window_id(title)
    
    if win_id:
        # wmctrl -i -a usa el ID de la ventana en lugar del nombre
        subprocess.run(["wmctrl", "-i", "-a", win_id], check=False)
        print(f"->> Ventana enfocada con éxito.")
    else:
        print(f"ERROR:  Jarvis no pudo enfocar o encontrar la ventana '{title}'.")

def minimize_window(params):
    """Minimiza una ventana específica en Linux usando xdotool."""
    title = params.get("title")
    if not title: return
    
    print(f"🔽 Jarvis minimizando: '{title}'...")
    win_id = _get_window_id(title)
    
    if win_id:
        subprocess.run(["xdotool", "windowminimize", win_id], check=False)
        print("->>> Ventana minimizada.")
    else:
        print(f"ERROR: No se encontró la ventana '{title}'.")

def maximize_window(params):
    """Maximiza una ventana específica en Linux."""
    title = params.get("title")
    if not title: return
    
    print(f"->> Jarvis maximizando: '{title}'...")
    win_id = _get_window_id(title)
    
    if win_id:
        # wmctrl -i -r <ID> altera las propiedades del ID exacto
        subprocess.run(["wmctrl", "-i", "-r", win_id, "-b", "add,maximized_vert,maximized_horz"], check=False)
        print("✅ Ventana maximizada.")
    else:
        print(f"❌ No se pudo encontrar '{title}' para maximizar.")

def close_window(params):
    """Cierra una ventana específica de forma segura en Linux."""
    title = params.get("title")
    if not title: return
    
    print(f"->> Jarvis cerrando ventana: '{title}'...")
    win_id = _get_window_id(title)
    
    if win_id:
        # wmctrl -i -c <ID> cierra por ID numérico
        subprocess.run(["wmctrl", "-i", "-c", win_id], check=False)
        print("✅ Ventana cerrada.")
    else:
        print(f"ERROR: No se encontró o no se pudo cerrar '{title}'.")