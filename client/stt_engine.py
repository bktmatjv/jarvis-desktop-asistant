import os
import io
import speech_recognition as sr
from groq import Groq
from dotenv import load_dotenv

# Asegurar que se cargan las variables de entorno
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

# Cargar claves dedicadas para reconocimiento de voz
voice_keys_str = os.getenv("GROQ_API_KEYS_VOICE") or os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEYS") or ""
api_keys = [k.strip() for k in voice_keys_str.split(",") if k.strip()]

if not api_keys:
    print(" Error: No se encontró GROQ_API_KEYS_VOICE ni GROQ_API_KEY en .env")

clients = [Groq(api_key=k) for k in api_keys] if api_keys else []
current_voice_idx = 0

def _get_voice_client():
    global current_voice_idx
    if not clients:
        return None
    return clients[current_voice_idx]

def _rotate_voice_client():
    global current_voice_idx
    if clients:
        current_voice_idx = (current_voice_idx + 1) % len(clients)

# Motor de reconocimiento para manejar el micrófono y silencios
recognizer = sr.Recognizer()
recognizer.energy_threshold = 300 
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 0.5


def record_and_transcribe(on_listening_start=None):
    """
    Graba el micrófono hasta que el usuario deja de hablar,
    luego envía el audio a Groq Whisper y devuelve el texto.
    """
    with sr.Microphone() as source:
        # Ajusta el ruido ambiente por medio segundo antes de grabar (evita falsos positivos y ahorra API calls)
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        if on_listening_start:
            on_listening_start()
            
        print("️ [STT] Escuchando orden...")
        try:
            # timeout: cuánto tiempo esperamos para que el usuario empiece a hablar
            # phrase_time_limit: límite máximo de grabación
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            print("⏳ [STT] Tiempo de espera agotado. No se detectó voz.")
            return None

    print("️ [STT] Enviando audio a Groq Whisper...")
    
    # Mantener el audio en memoria RAM, evitando I/O de disco
    audio_data = audio.get_wav_data()

    model_name = os.getenv("VOICE_MODEL", "whisper-large-v3-turbo")

    for _ in range(max(1, len(clients))):
        cli = _get_voice_client()
        if not cli:
            print(" Error: No hay cliente Groq disponible para STT.")
            return None
        try:
            transcription = cli.audio.transcriptions.create(
                file=("audio.wav", audio_data),
                model=model_name,
                prompt="El audio es en idioma español.",
                response_format="json",
                language="es",
                temperature=0.0
            )
            texto = transcription.text.strip()
            print(f" [STT] Transcrito: '{texto}'")
            return texto
        except Exception as e:
            print(f" [STT] Error en transcripción con clave actual ({e}). Rotando...")
            _rotate_voice_client()

    return None
