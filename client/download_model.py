import os
import urllib.request
import zipfile
import shutil

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"
ZIP_PATH = "model.zip"
EXTRACT_DIR = "model_tmp"
FINAL_DIR = "model"

print("Descargando modelo Vosk (40MB)...")
urllib.request.urlretrieve(MODEL_URL, ZIP_PATH)

print("Extrayendo...")
with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
    zip_ref.extractall(EXTRACT_DIR)

# Mover la carpeta extraída (que adentro tiene otra carpeta) al destino final
extracted_folders = os.listdir(EXTRACT_DIR)
source_model_dir = os.path.join(EXTRACT_DIR, extracted_folders[0])

if os.path.exists(FINAL_DIR):
    shutil.rmtree(FINAL_DIR)
    
os.rename(source_model_dir, FINAL_DIR)

# Limpieza
os.remove(ZIP_PATH)
shutil.rmtree(EXTRACT_DIR)

print("Modelo instalado en 'model/'")
