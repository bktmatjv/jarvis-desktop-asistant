import pywinauto
from pywinauto import Desktop

def _get_window(title_regex):
    """
    Función helper interna: Escanea el escritorio y devuelve la primera 
    ventana visible que coincida con la expresión regular.
    """
    if not title_regex.startswith(".*"):
        title_regex = ".*" + title_regex
    if not title_regex.endswith(".*"):
        title_regex = title_regex + ".*"
        
    escritorio = Desktop(backend="uia")
    return escritorio.window(title_re=title_regex, visible_only=True, found_index=0)

def list_windows(params=None):
    """Devuelve una lista de las ventanas visibles actualmente."""
    print("️ Jarvis está escaneando las ventanas abiertas...")
    try:
        escritorio = Desktop(backend="uia")
        ventanas = escritorio.windows(visible_only=True)
        
        titulos = [v.window_text() for v in ventanas if v.window_text().strip()]
        
        lista_ignorados = ["Program Manager", "Task View", "Barra de tareas"]
        titulos_limpios = [t for t in titulos if t not in lista_ignorados]
        
        print(f"->> Se encontraron {len(titulos_limpios)} ventanas activas.")
        print(titulos_limpios)
        return titulos_limpios
        
    except Exception as e:
        print(f"ERROR: Error al listar ventanas: {e}")
        return str(e)

def focus_window(params):
    """Trae una ventana al frente."""
    title = params.get("title")
    if not title:
        print("ERROR: Jarvis necesita el parámetro 'title' para enfocar una ventana.")
        return
        
    print(f" Jarvis buscando ventana para enfocar: '{title}'...")
    try:
        ventana = _get_window(title)
        ventana.set_focus()
        print(f"->> Ventana enfocada con éxito.")
    except pywinauto.findwindows.ElementNotFoundError:
        print(f"ERROR: Jarvis no pudo encontrar ninguna ventana que coincida con '{title}'.")
    except Exception as e:
        print(f"ERROR: Error al enfocar ventana: {e}")

def minimize_window(params):
    """Minimiza una ventana específica."""
    title = params.get("title")
    if not title: return
    
    print(f" Jarvis minimizando: '{title}'...")
    try:
        ventana = _get_window(title)
        ventana.minimize()
        print("->> Ventana minimizada.")
    except pywinauto.findwindows.ElementNotFoundError:
        print(f"ERROR: No se encontró la ventana '{title}'.")

def maximize_window(params):
    """Maximiza una ventana específica."""
    title = params.get("title")
    if not title: return
    
    print(f" Jarvis maximizando: '{title}'...")
    try:
        ventana = _get_window(title)
        ventana.maximize()
        print("->> Ventana maximizada.")
    except pywinauto.findwindows.ElementNotFoundError:
        print(f"ERROR: No se encontró la ventana '{title}'.")

def close_window(params):
    """Cierra una ventana específica de forma segura."""
    title = params.get("title")
    if not title: return
    
    print(f" Jarvis cerrando ventana: '{title}'...")
    try:
        ventana = _get_window(title)
        ventana.close()
        print("->> Ventana cerrada.")
    except pywinauto.findwindows.ElementNotFoundError:
        print(f"ERROR: No se encontró la ventana '{title}'.")