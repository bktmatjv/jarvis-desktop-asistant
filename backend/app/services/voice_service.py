import io
import base64
import soundfile as sf
import numpy as np

try:
    from kokoro import KPipeline
except ImportError:
    KPipeline = None

pipeline = None
DEFAULT_VOICE = 'em_alex'

def init_voice_engine():
    global pipeline
    if not KPipeline:
        print("Motor Kokoro no disponible. Faltan dependencias en el servidor.")
        return
    try:
        print("Iniciando Kokoro Voice Engine en Servidor Backend...")
        pipeline = KPipeline(lang_code='es')
        print("Motor TTS servidor inicializado y en memoria.")
    except Exception as e:
        print(f"Error inicializando Kokoro servidor: {e}")

def synthesize_stream(text: str, voice: str = DEFAULT_VOICE, speed: float = 1.0):
    """
    Generador que devuelve partes de audio en formato Base64 WAV para lograr Streaming de Cero-Latencia.
    """
    if not pipeline:
        return
    
    try:
        # Split agresivo para trozos rápidos (Streaming)
        generator = pipeline(text, voice=voice, speed=speed, split_pattern=r'(?<=[.,!?;\n])\s+')
        for i, (graphemes, phonemes, audio) in enumerate(generator):
            if audio is not None:
                # Escribimos el numpy array a WAV en memoria RAM
                buffer = io.BytesIO()
                sf.write(buffer, audio, 24000, format='WAV', subtype='PCM_16')
                buffer.seek(0)
                # Convertimos a base64
                b64_audio = base64.b64encode(buffer.read()).decode('utf-8')
                yield b64_audio
    except Exception as e:
        print(f"Error en sintesis del servidor: {e}")
