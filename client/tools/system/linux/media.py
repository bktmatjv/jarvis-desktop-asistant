import urllib.request
import urllib.parse
import re
import webbrowser
import subprocess

# IMPORTANTE: En Linux, esta herramienta para controlar el reproductor requiere 'playerctl'
# Puedes instalarlo ejecutando: sudo apt install playerctl

def play_youtube_music(params):
    """Busca en YouTube, extrae el primer video y lo reproduce automáticamente."""
    query = params.get("song") or params.get("query")
    if not query:
        print("❌ Jarvis: No me dijiste qué canción poner.")
        return

    print(f"🔍 Jarvis buscando en YouTube: '{query}'...")
    try:
        query_string = urllib.parse.urlencode({"search_query": query})
        url_busqueda = f"https://www.youtube.com/results?{query_string}"
        
        req = urllib.request.Request(url_busqueda, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            html_content = response.read().decode()
        
        search_results = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html_content)

        if search_results:
            primer_video_url = f"https://www.youtube.com/watch?v={search_results[0]}"
            print(f"▶️ Jarvis: Reproduciendo ahora: {primer_video_url}")
            webbrowser.open(primer_video_url)
            print("✅ Navegador abierto.")
        else:
            print("❌ Jarvis: Encontré la página pero no pude extraer ningún video.")

    except Exception as e:
        print(f"❌ Jarvis: Error al buscar en YouTube: {e}")

# --- FUNCIONES DE CONTROL GLOBAL (LINUX) ---

def global_music_play(params=None):
    print("⏯️ Jarvis: Play (Linux).")
    try:
        subprocess.run(["playerctl", "play"], check=False)
    except FileNotFoundError:
        print("❌ Error: Necesitas instalar 'playerctl' (sudo apt install playerctl)")

def global_music_pause(params=None):
    print("⏸️ Jarvis: Pausa (Linux).")
    try:
        subprocess.run(["playerctl", "pause"], check=False)
    except FileNotFoundError:
        print("❌ Error: Necesitas instalar 'playerctl' (sudo apt install playerctl)")

def global_music_next(params=None):
    print("⏭️ Jarvis: Siguiente (Linux).")
    try:
        subprocess.run(["playerctl", "next"], check=False)
    except FileNotFoundError:
        print("❌ Error: Necesitas instalar 'playerctl' (sudo apt install playerctl)")

def global_music_previous(params=None):
    print("⏮️ Jarvis: Anterior (Linux).")
    try:
        subprocess.run(["playerctl", "previous"], check=False)
    except FileNotFoundError:
        print("❌ Error: Necesitas instalar 'playerctl' (sudo apt install playerctl)")