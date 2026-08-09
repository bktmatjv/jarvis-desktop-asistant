import os
import json
import time
import platform
from pathlib import Path

'''
    Documentación:
    - Este módulo es un script multiplataforma (Windows/Linux) para indexar los programas 
      instalados en el sistema operativo. Guarda sus rutas en un archivo JSON para que el cerebro de
      Jarvis pueda consultarlo al abrir un programa.
    - En Windows: Escanea carpetas comunes y filtra por la extensión .exe.
    - En Linux: Escanea los directorios de binarios estándar (como /usr/bin) y evalúa los permisos de ejecución.
'''

CACHE_FILE = Path("memory/programs_cache.json")
OS_NAME = platform.system()  # Identifica el sistema operativo

if OS_NAME == "Windows":
    SEARCH_PATHS = [
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
        Path.home() / "AppData/Local",
        Path.home() / "AppData/Roaming"
    ]
else:
    SEARCH_PATHS = [
        Path("/usr/bin"),
        Path("/usr/local/bin"),
        Path("/opt"),
        Path.home() / ".local/bin"
    ]

# Palabras clave para no llenar el JSON de ejecutables basura
IGNORE_KEYWORDS = ["uninstall", "unins", "update", "setup", "installer", "helper", "crash", "reporter"]

def is_executable(file_path, filename):
    """Determina si un archivo es un ejecutable válido dependiendo del OS."""
    if OS_NAME == "Windows":
        return filename.lower().endswith(".exe")
    else:
        # En Linux, comprobamos que sea un archivo y tenga permisos de ejecución (X_OK)
        return os.path.isfile(file_path) and os.access(file_path, os.X_OK)

def build_index():
    print(f"\n-->> Jarvis: Iniciando escaneo primario del sistema ({OS_NAME}). Esto puede tomar un momento...")
    start_time = time.time()
    
    cache_data = {}
    
    for base in SEARCH_PATHS:
        if not base.exists():
            continue
            
        for root, dirs, files in os.walk(base):
            for file in files:
                file_path = os.path.join(root, file)
                
                if is_executable(file_path, file):
                    file_lower = file.lower()
                    
                    # Filtramos basura
                    if any(kw in file_lower for kw in IGNORE_KEYWORDS):
                        continue
                        
                    # Limpieza del nombre (quitamos .exe en caso de Windows)
                    app_name = file_lower.replace(".exe", "") if OS_NAME == "Windows" else file_lower
                    
                    # Guardamos la primera ocurrencia (evita sobreescribir binarios principales con copias secundarias)
                    if app_name not in cache_data:
                        cache_data[app_name] = file_path

    # Crear carpeta 'memory' si no existe
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Guardar en JSON
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=4)
        
    elapsed = time.time() - start_time
    print(f"✅ Escaneo completado en {elapsed:.2f} segundos. Se indexaron {len(cache_data)} programas.\n")

def _load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def find_program(program_name):
    # Limpiamos el input del usuario (por si dice "abre notepad.exe" estando en Linux o Windows)
    target = program_name.lower().replace(".exe", "").strip()
    
    if not CACHE_FILE.exists():
        build_index()
        
    cache = _load_cache()

    # 1. BÚSQUEDA EXACTA
    if target in cache:
        ruta = cache[target]
        ruta_normalizada = os.path.normpath(ruta)
        if os.path.exists(ruta_normalizada):
            print(f"⚡ [Caché] Jarvis encontró '{target}' exactamente.")
            return ruta_normalizada

    # 2. BÚSQUEDA INTELIGENTE
    print(f"🔍 Buscando coincidencias para: {target}...")
    for name, path in cache.items():
        filename = os.path.basename(path).lower()
        
        if target in name or name in target or target in filename:
            ruta_normalizada = os.path.normpath(path)
            if os.path.exists(ruta_normalizada):
                print(f"⚡ [Match Inteligente] Jarvis asoció '{target}' con la ruta: {ruta_normalizada}")
                return ruta_normalizada

    print(f"❌ Jarvis no pudo encontrar ninguna ruta válida para '{target}' en el índice.")
    return None


build_index()