"""
Voice Engine module — JARVIS 2.0.
Manages the TTS subprocess (pyttsx3) for real-time voice output.

Key improvements:
  - speak_streaming(): splits text into sentences and speaks each one immediately,
    enabling the TTS to start before the LLM finishes generating the full response.
  - Improved text cleaning: removes markdown symbols, code blocks, backticks.
  - Robust subprocess lifecycle management with auto-restart.
"""
import subprocess
import threading
import sys
import os
import re

_tts_proc = None
_tts_lock = threading.Lock()

_TTS_WORKER_CODE = """
import pyttsx3
import sys

try:
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    
    # Buscar específicamente la voz de RAUL primero
    voz_seleccionada = None
    for v in voices:
        if 'raul' in v.name.lower():
            voz_seleccionada = v.id
            break
            
    # Si no encuentra a Raul, hace fallback a cualquier voz en español
    if not voz_seleccionada:
        for v in voices:
            langs = v.languages
            lang_str = str(langs).lower() if langs else ""
            name_str = v.name.lower()
            if 'es' in lang_str or 'spanish' in name_str or 'español' in name_str or 'sabina' in name_str or 'helena' in name_str:
                voz_seleccionada = v.id
                break
                
    if voz_seleccionada:
        engine.setProperty('voice', voz_seleccionada)
            
    # Hacemos que hable ligeramente más rápido para más fluidez
    engine.setProperty('rate', 180)
except Exception as e:
    print(f"Error inicializando pyttsx3: {e}", file=sys.stderr)
    sys.exit(1)

sys.stdin.reconfigure(encoding='utf-8')

try:
    engine.startLoop(False)
except Exception:
    pass
    
for line in sys.stdin:
    text = line.strip()
    if text:
        try:
            engine.say(text)
            while engine.isBusy():
                engine.iterate()
                import time
                time.sleep(0.02)
        except Exception as e:
            print(f"Error hablando: {e}", file=sys.stderr)
"""


def _start_tts_process():
    global _tts_proc
    try:
        _tts_proc = subprocess.Popen(
            [sys.executable, '-c', _TTS_WORKER_CODE],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )
    except Exception as e:
        print(f"Error al iniciar subproceso de TTS: {e}")


# Start the TTS subprocess immediately on import
_start_tts_process()


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def _clean_for_tts(text: str) -> str:
    """Removes markdown and code artifacts."""
    text = re.sub(r'```[\s\S]*?```', '[código adjunto]', text)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}(.*?)_{1,3}', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = text.replace('\\', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _split_sentences(text: str) -> list[str]:
    """Splits text into sentences suitable for incremental TTS delivery."""
    parts = re.split(r'(?<=[.!?…])\s+', text)
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Core speak function
# ---------------------------------------------------------------------------

def speak(text: str, voice=None, speed=1.1):
    """
    Sends text to the TTS subprocess for immediate playback.
    Thread-safe.
    """
    global _tts_proc
    if not text or not text.strip():
        return

    clean_text = _clean_for_tts(text)
    if not clean_text:
        return

    clean_text = clean_text.replace('\n', ' ').replace('\r', '')

    with _tts_lock:
        if _tts_proc is None or _tts_proc.poll() is not None:
            _start_tts_process()

        if _tts_proc and _tts_proc.poll() is None:
            try:
                _tts_proc.stdin.write(clean_text + '\n')
                _tts_proc.stdin.flush()
            except Exception as e:
                print(f"Error TTS: {e}")


# ---------------------------------------------------------------------------
# Streaming TTS
# ---------------------------------------------------------------------------

def speak_streaming(text: str):
    """Splits text into sentences and speaks each one immediately."""
    clean = _clean_for_tts(text)
    sentences = _split_sentences(clean)
    for sentence in sentences:
        if sentence:
            speak(sentence)


