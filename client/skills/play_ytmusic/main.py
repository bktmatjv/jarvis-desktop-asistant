import sys
import json
import urllib.request
import urllib.parse
import re
import webbrowser
import time
import pyautogui

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
        
    song_name = params.get("song_name")
    if not song_name:
        print("Error: song_name no proporcionado en los parámetros.")
        sys.exit(1)
        
    print(f" Buscando en YouTube: {song_name}")
    
    # Obtener el ID del primer video de YouTube
    try:
        query = urllib.parse.quote(song_name)
        url = f"https://www.youtube.com/results?search_query={query}"
        html = urllib.request.urlopen(url).read().decode()
        video_ids = re.findall(r"watch\?v=(\S{11})", html)
        
        if not video_ids:
            print(f"No se encontraron resultados para: {song_name}")
            sys.exit(1)
            
        video_id = video_ids[0]
        ytmusic_url = f"https://music.youtube.com/watch?v={video_id}"
        print(f" Video encontrado. Abriendo YouTube Music: {ytmusic_url}")
        
        # Abrir YouTube Music
        webbrowser.open(ytmusic_url)
        print("▶️ Reproduciendo directamente en YouTube Music.")
        
    except Exception as e:
        print(f"Error al buscar o reproducir en YouTube Music: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
