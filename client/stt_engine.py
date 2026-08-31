import os
import io
import wave
import tempfile
import speech_recognition as sr
from groq import Groq
from dotenv import load_dotenv

# Asegurar que se cargan las variables de entorno
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print(" Error: GROQ_API_KEY no encontrada en .env")

# Cliente de Groq para acceder a Whisper
client = Groq(api_key=api_key)

# Motor de reconocimiento para manejar el micrófono y silencios
recognizer = sr.Recognizer()

# Configuraciones de umbral de energía (se ajustan al ruido ambiente)
recognizer.energy_threshold = 300 
recognizer.dynamic_energy_threshold = True

def record_and_transcribe(on_listening_start=None):
    """
    Graba el micrófono hasta que el usuario deja de hablar,
    luego envía el audio a Groq Whisper y devuelve el texto.
    """
    with sr.Microphone() as source:
        # Ajusta el ruido ambiente por medio segundo antes de grabar
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
    
    # Escribir a un archivo temporal WAV porque Groq pide un archivo físico
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_filename = tmp_file.name
        with open(tmp_filename, "wb") as f:
            f.write(audio.get_wav_data())

    try:
        with open(tmp_filename, "rb") as file:
            transcription = client.audio.transcriptions.create(
              file=(tmp_filename, file.read()),
              model="whisper-large-v3",
              prompt="El audio es en idioma español.",  # Ayuda a que el modelo sepa el idioma por defecto
              response_format="json",
              language="es",
              temperature=0.0
            )
        
        # Limpiar archivo temporal
        os.remove(tmp_filename)
        
        texto = transcription.text.strip()
        print(f" [STT] Transcrito: '{texto}'")
        return texto

    except Exception as e:
        print(f" [STT] Error transcribiendo con Groq: {e}")
        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)
        return None
