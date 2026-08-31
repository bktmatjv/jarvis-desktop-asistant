import os
import sys
import queue
import threading
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer

# Desactivar logs de Vosk para no ensuciar la consola
from vosk import SetLogLevel
SetLogLevel(-1)

_q = queue.Queue()
_is_listening = False
_wake_callback = None

def _audio_callback(indata, frames, time, status):
    """Llamado por sounddevice por cada bloque de audio entrante."""
    if status:
        print(f"SD Status: {status}", file=sys.stderr)
    if _is_listening:
        _q.put(bytes(indata))

def _listen_worker():
    global _is_listening
    
    model_path = os.path.join(os.path.dirname(__file__), "model")
    if not os.path.exists(model_path):
        print(" Error: No se encontró el modelo de Vosk en la carpeta 'model/'. El wake word no funcionará.")
        return
        
    try:
        model = Model(model_path)
        # Diccionario limitado para que solo busque la palabra Jarvis (aumenta la velocidad y precisión)
        # Agregamos variaciones fonéticas comunes
        recognizer = KaldiRecognizer(model, 16000, '["jarvis", "yarvis", "harvis", "[unk]"]')
    except Exception as e:
        print(f" Error cargando modelo Vosk: {e}")
        return

    try:
        with sd.RawInputStream(samplerate=16000, blocksize=8000, device=None,
                               dtype='int16', channels=1, callback=_audio_callback):
            print("️ Motor Wake Word activo. Esperando 'Jarvis' en background...")
            while True:
                data = _q.get()
                if not _is_listening:
                    continue
                    
                if recognizer.AcceptWaveform(data):
                    res = json.loads(recognizer.Result())
                    text = res.get("text", "")
                    if text and text != "[unk]":
                        if "jarvis" in text or "yarvis" in text or "harvis" in text:
                            print(" [WAKE WORD DETECTADO: JARVIS]")
                            if _wake_callback:
                                _wake_callback()
                            # Limpiar cola para no disparar dos veces seguidas
                            with _q.mutex:
                                _q.queue.clear()
    except Exception as e:
        print(f" Error en stream de audio: {e}")

def start_listening(callback):
    """Inicia el motor de detección en un hilo aparte."""
    global _is_listening, _wake_callback
    _wake_callback = callback
    _is_listening = True  # AHORA ESCUCHA SIEMPRE POR DEFECTO
    threading.Thread(target=_listen_worker, daemon=True).start()

def set_listening_state(is_listening: bool):
    """Activa o desactiva la escucha de Vosk (para pausarlo mientras Whisper graba)."""
    global _is_listening
    _is_listening = is_listening
    # Si acabamos de activar, limpiamos el audio residual
    if is_listening:
        with _q.mutex:
            _q.queue.clear()
