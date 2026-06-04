import os
import json
import time
from pathlib import Path


'''
    Documentación:
    - Este módulo es un script para indexar los programas instalados en el sistema 
    operativo de Windows, guardando sus rutas en un archivo JSON para que el cerebro de
      Jarvis pueda consultarlo cada vez que necesite abrir un programa. La idea es que esta herramienta realice un 
      escaneo completo de las carpetas donde comúnmente se instalan programas (como "C:/Program Files" y "C:/Program Files (x86)"), 
      identifique los archivos ejecutables (.exe), y guarde una asociación entre el nombre del programa (sin la extensión .exe) y su ruta 
      completa en un archivo JSON. Luego, cuando el cerebro de Jarvis reciba una orden del usuario como "abre el bloc de notas", pueda consultar 
      este índice para encontrar la ruta del bloc de notas (notepad.exe) y ejecutarlo. AUN EN DESARROLLO, NO TODAS LAS FUNCIONES ESTÁN OPTIMIZADAS O TERMINADAS, 
      PERO LA IDEA ES QUE SEA UNA HERRAMIENTA COMPLETA PARA INDEXAR PROGRAMAS DESDE EL CEREBRO DE JARVIS.
'''

# Ruta donde Jarvis guardará su "cerebro" de programas
CACHE_FILE = Path("memory/programs_cache.json")

# Rutas estándar de Windows donde se instalan los programas
SEARCH_PATHS = [
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path.home() / "AppData/Local",
    Path.home() / "AppData/Roaming"
]

# Palabras clave para no llenar el JSON de ejecutables basura (desinstaladores, actualizadores)
IGNORE_KEYWORDS = ["uninstall", "unins", "update", "setup", "installer", "helper", "crash", "reporter"]

def build_index():
    # Realiza un escaneo completo y guarda todos los .exe relevantes en el JSON.
    print("\n-->> Jarvis: Iniciando escaneo primario del sistema. Esto puede tomar un momento...")
    start_time = time.time()
    
    cache_data = {}
    
    for base in SEARCH_PATHS:
        if not base.exists():
            continue
            
        # os.walk recorre todas las subcarpetas
        for root, dirs, files in os.walk(base):
            for file in files:
                if file.endswith(".exe"):
                    file_lower = file.lower()
                    
                    # Filtramos basura
                    if any(kw in file_lower for kw in IGNORE_KEYWORDS):
                        continue
                        
                    # El nombre clave será el archivo sin el .exe (ej: 'chrome')
                    app_name = file_lower.replace(".exe", "")
                    
                    # Si no lo hemos registrado aún, lo guardamos
                    if app_name not in cache_data:
                        cache_data[app_name] = os.path.join(root, file)

    # Crear carpeta 'memory' si no existe
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Guardar en JSON
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=4)
        
    elapsed = time.time() - start_time
    print(f"✅ Escaneo completado en {elapsed:.2f} segundos. Se indexaron {len(cache_data)} programas.\n")

def _load_cache():
    # Carga el JSON a la memoria RAM.
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def find_program(program_name):
    # Busca el programa en el JSON con lógica mejorada para rutas complejas como Discord.
    target = program_name.lower().replace(".exe", "").strip()
    
    if not CACHE_FILE.exists():
        build_index()
        
    cache = _load_cache()

    '''
        documentacion:
        - Primero, se intenta una búsqueda exacta en el índice utilizando el nombre del programa proporcionado por el usuario.
        - Si no se encuentra una coincidencia exacta, se realiza una búsqueda inteligente que verifica si el nombre del programa está contenido en alguna de las claves del índice, o si alguna de las claves del índice está contenida en el nombre del programa. Esto permite manejar casos donde el usuario puede referirse a un programa de manera más informal (ej: "discord" en lugar de "discord_launcher").
        - Además, se agregó una nueva capa de búsqueda que verifica si el nombre del programa está presente en el nombre del archivo ejecutable dentro de la ruta, lo que ayuda a encontrar programas que pueden tener nombres de carpeta poco intuitivos pero archivos ejecutables con nombres reconocibles.
        - Si se encuentra una ruta válida, se devuelve; de lo contrario, se informa que no se pudo encontrar el programa en el índice.
    '''


    # 1. BÚSQUEDA EXACTA
    if target in cache:
        ruta = cache[target]
        # Normalizamos la ruta para que Windows no se confunda con los slashes
        ruta_normalizada = os.path.normpath(ruta)
        if os.path.exists(ruta_normalizada):
            print(f"⚡ [Caché] Jarvis encontró '{target}' exactamente.")
            return ruta_normalizada

    # 2. BÚSQUEDA INTELIGENTE (Iterando el diccionario)
    print(f"🔍 Buscando coincidencias para: {target}...")
    for name, path in cache.items():
        # Caso A: El nombre que pidió el usuario está contenido en la clave del JSON (ej: 'discord' en 'discord_launcher')
        # Caso B: La clave del JSON está en lo que pidió el usuario
        # Caso C: ¡NUEVO! El nombre buscado está en el NOMBRE DEL ARCHIVO de la ruta
        filename = os.path.basename(path).lower()
        
        if target in name or name in target or target in filename:
            ruta_normalizada = os.path.normpath(path)
            if os.path.exists(ruta_normalizada):
                print(f"⚡ [Match Inteligente] Jarvis asoció '{target}' con la ruta: {ruta_normalizada}")
                return ruta_normalizada

    print(f"❌ Jarvis no pudo encontrar ninguna ruta válida para '{target}' en el índice.")
    return None
