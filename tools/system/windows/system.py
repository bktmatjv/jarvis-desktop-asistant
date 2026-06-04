import os
from ctypes import cast, POINTER


import subprocess # Usaremos subprocess como alternativa más potente a os.system
import warnings
from utils.program_indexer import find_program

import pyautogui
import comtypes
from ctypes import cast, POINTER
from pycaw.pycaw import IAudioEndpointVolume, IMMDeviceEnumerator
# 🛡️ EL ESCUDO: Definimos el ID interno de Windows manualmente.
# Así no dependemos de dónde lo esconda pycaw en sus actualizaciones.
CLSID_MMDeviceEnumerator = comtypes.GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")


'''
    script para controlar funciones del sistema operativo como abrir programas, apagar, reiniciar, suspender, bloquear la pantalla y controlar el volumen. La idea es que puedas enviar comandos al cerebro de Jarvis como "abre el bloc de notas", o "apaga la PC", o "sube el volumen al 50%", y esta herramienta se encargue de traducir esos comandos a acciones reales en el sistema operativo de Windows. AUN EN DESARROLLO, NO TODAS LAS FUNCIONES ESTÁN OPTIMIZADAS O TERMINADAS, PERO LA IDEA ES QUE SEA UNA HERRAMIENTA COMPLETA PARA CONTROLAR FUNCIONES DEL SISTEMA DESDE EL CEREBRO DE JARVIS.

'''


# Silenciamos advertencias de threading
warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto")

def open_program(params):
    """Abre un programa usando el indexador de búsqueda primaria de Jarvis."""
    program_name = params.get("program")
    
    if not program_name: 
        return
    
    # 1. Buscamos en el JSON de caché
    ruta_exacta = find_program(program_name)
    
    print(f"ruta_exacta: {ruta_exacta}")

    if ruta_exacta and os.path.exists(ruta_exacta):
        print(f"🚀 Jarvis detectó la ruta en caché: {ruta_exacta}")
        try:
            # En Windows, lo ideal para rutas absolutas es usar os.startfile
            # Pero le pasamos la ruta normalizada para evitar errores de barras inclinadas
            os.startfile(os.path.normpath(ruta_exacta))
            print(f"✅ '{program_name}' se ha iniciado correctamente.")
        except Exception as e:
            print(f"⚠️ Error al abrir con startfile, intentando método alternativo: {e}")
            # Plan B: Usar subprocess para forzar la apertura
            subprocess.Popen([ruta_exacta], shell=True)
    else:
        # 2. Si no está en el JSON, intentamos el comando directo (por si es una app del sistema como 'calc')
        print(f"🔍 '{program_name}' no está en el índice. Intentando ejecución directa del sistema...")
        try:
            # Intentamos abrirlo como comando de consola (ej: 'notepad', 'calc')
            subprocess.Popen(f"start {program_name}", shell=True)
        except Exception as e:
            print(f"❌ Jarvis no pudo encontrar ni abrir '{program_name}' de ninguna forma.")

def shutdown_system(params=None):
    """Apaga la PC"""
    print("⚠️ Jarvis: Iniciando secuencia de apagado...")
    os.system("shutdown /s /t 5") # 5 segundos de gracia

def restart_system(params=None):
    """Reinicia la PC"""
    print("🔄 Jarvis: Iniciando reinicio del sistema...")
    os.system("shutdown /r /t 5")

def sleep_system(params=None):
    """Suspende la PC"""
    print("💤 Jarvis: Suspendiendo el sistema...")
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

def lock_system(params=None):
    """Bloquea la pantalla de Windows"""
    print("🔒 Jarvis: Bloqueando la sesión de usuario...")
    os.system("rundll32.exe user32.dll,LockWorkStation")



def control_volume(params):
    """Controla el volumen maestro con doble seguridad y acceso directo a Windows."""
    action = params.get("action")
    value = params.get("value")
    
    if not action: return

    try:
        # 1. ACCIONES RÁPIDAS
        if action == "mute":
            pyautogui.press('volumemute')
            print("🔇 Jarvis: Volumen muteado/desmuteado.")
            return
            
        elif action == "up":
            for _ in range(5): pyautogui.press('volumeup')
            print("🔊 Jarvis: Volumen subido.")
            return
            
        elif action == "down":
            for _ in range(5): pyautogui.press('volumedown')
            print("🔉 Jarvis: Volumen bajado.")
            return

        # 2. ACCIÓN DE PRECISIÓN (Porcentaje)
        elif action == "set" and value is not None:
            safe_value = max(0, min(100, int(value)))
            
            try:
                # INTENTO 1: Acceso Directo al Núcleo de Windows
                comtypes.CoInitialize()
                enumerator = comtypes.CoCreateInstance(
                    CLSID_MMDeviceEnumerator,
                    interface=IMMDeviceEnumerator,
                    clsctx=comtypes.CLSCTX_ALL
                )
                
                device = enumerator.GetDefaultAudioEndpoint(0, 1)
                interface = device.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
                vol = cast(interface, POINTER(IAudioEndpointVolume))
                
                # Aplicamos el volumen
                vol.SetMasterVolumeLevelScalar(safe_value / 100.0, None)
                print(f"🔊 Jarvis: Volumen establecido al {safe_value}% (Vía COM API).")

            except Exception as e:
                print(f"⚠️ Jarvis: La API de Windows falló ({e}). Usando el 'Teclado Fantasma'...")
                
                # INTENTO 2: Fallback Infalible (Simulación humana)
                # Muteamos bajando a 0
                for _ in range(50): 
                    pyautogui.press('volumedown')
                
                # Subimos la cantidad exacta (cada toque suele ser 2%)
                toques = safe_value // 2
                for _ in range(toques): 
                    pyautogui.press('volumeup')
                    
                print(f"🔊 Jarvis: Volumen establecido aprox al {safe_value}% (Vía manual).")
            
    except Exception as e:
        print(f"❌ Jarvis: Error crítico en el módulo de audio: {e}")
