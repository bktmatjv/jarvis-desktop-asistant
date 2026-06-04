import urllib.request
import urllib.parse
import re
import webbrowser
import pyautogui

def play_youtube_music(params):
    """
    Busca en YouTube, extrae el primer video y lo reproduce automáticamente.
    """
    # Extraemos el nombre de la canción del diccionario de parámetros
    query = params.get("song") or params.get("query")

    if not query:
        print("❌ Jarvis: No me dijiste qué canción poner.")
        return

    print(f"🔍 Jarvis buscando en YouTube: '{query}'...")

    try:
        # 1. Formateamos la búsqueda
        query_string = urllib.parse.urlencode({"search_query": query})
        url_busqueda = f"https://www.youtube.com/results?{query_string}"
        
        # 2. Realizamos la petición con un User-Agent para evitar bloqueos
        req = urllib.request.Request(url_busqueda, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            html_content = response.read().decode()
        
        # 3. Buscamos el ID del primer video (watch?v=XXXXXXXXXXX)
        # El regex busca 11 caracteres alfanuméricos tras el v=
        search_results = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html_content)

        if search_results:
            # 4. Construimos la URL del primer video encontrado
            primer_video_url = f"https://www.youtube.com/watch?v={search_results[0]}"
            print(f"▶️ Jarvis: Reproduciendo ahora: {primer_video_url}")
            
            # 5. Abrimos el navegador
            webbrowser.open(primer_video_url)
            print("✅ Navegador abierto.")
        else:
            print("❌ Jarvis: Encontré la página pero no pude extraer ningún video.")

    except Exception as e:
        print(f"❌ Jarvis: Error de conexión o de red al buscar en YouTube: {e}")

# --- FUNCIONES DE CONTROL GLOBAL ---

def global_music_play(params=None):
    """Simula tecla Play/Pause."""
    print("⏯️ Jarvis: Play.")
    pyautogui.press('playpause')

def global_music_pause(params=None):
    """Simula tecla Pause."""
    print("⏸️ Jarvis: Pausa.")
    pyautogui.press('playpause')

def global_music_next(params=None):
    """Simula tecla Siguiente."""
    print("⏭️ Jarvis: Siguiente.")
    pyautogui.press('nexttrack')

def global_music_previous(params=None):
    """Simula tecla Anterior."""
    print("⏮️ Jarvis: Anterior.")
    pyautogui.press('prevtrack')