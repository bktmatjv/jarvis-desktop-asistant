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
    
    # Prefer a Spanish voice (Mexico, Spain, etc.)
    for v in voices:
        langs = v.languages
        lang_str = str(langs).lower() if langs else ""
        name_str = v.name.lower()
        if 'es' in lang_str or 'spanish' in name_str or 'español' in name_str or 'sabina' in name_str or 'helena' in name_str:
            engine.setProperty('voice', v.id)
            break
            
    engine.setProperty('rate', 160)
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
                time.sleep(0.05)
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
    """
    Removes markdown and code artifacts that would sound bad when spoken:
    - Code blocks (``` ... ```)
    - Backtick-enclosed inline code
    - Asterisks, underscores (bold/italic markers)
    - Markdown headings (#)
    - Excessive whitespace
    """
    # Remove fenced code blocks entirely (replace with spoken indicator)
    text = re.sub(r'```[\s\S]*?```', '[código adjunto]', text)
    # Remove inline code
    text = re.sub(r'`[^`]+`', '', text)
    # Remove markdown bold/italic
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}(.*?)_{1,3}', r'\1', text)
    # Remove heading markers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove backslashes
    text = text.replace('\\', ' ')
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _split_sentences(text: str) -> list[str]:
    """
    Splits text into sentences suitable for incremental TTS delivery.
    Splits on sentence-ending punctuation followed by whitespace.
    """
    # Split on . ! ? followed by space (keep delimiter with previous sentence)
    parts = re.split(r'(?<=[.!?…])\s+', text)
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Core speak function
# ---------------------------------------------------------------------------

def speak(text: str, voice=None, speed=1.1):
    """
    Sends text to the TTS subprocess for immediate playback.
    Cleans markdown and code artifacts before speaking.
    Thread-safe.
    """
    global _tts_proc
    if not text or not text.strip():
        return

    clean_text = _clean_for_tts(text)
    if not clean_text:
        return

    # Replace newlines with spaces (avoid "slash n" being spoken)
    clean_text = clean_text.replace('\n', ' ').replace('\r', '')

    with _tts_lock:
        if _tts_proc is None or _tts_proc.poll() is not None:
            _start_tts_process()

        if _tts_proc and _tts_proc.poll() is None:
            try:
                with open("voice_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"TTS: {clean_text}\n")
                _tts_proc.stdin.write(clean_text + '\n')
                _tts_proc.stdin.flush()
            except Exception as e:
                with open("voice_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"Error TTS: {e}\n")


# ---------------------------------------------------------------------------
# Streaming TTS — incremental sentence-by-sentence delivery
# ---------------------------------------------------------------------------

def speak_streaming(text: str):
    """
    Splits text into sentences and speaks each one immediately via speak().
    Use this when receiving a full text response that should start playing
    before the user reads the whole thing.

    Example:
        speak_streaming("Buenos días, señor. El sistema está operativo. Temperatura del CPU: 45 grados.")
        # → speaks "Buenos días, señor." immediately, then "El sistema está operativo.", etc.
    """
    clean = _clean_for_tts(text)
    sentences = _split_sentences(clean)
    for sentence in sentences:
        if sentence:
            speak(sentence)


def enqueue_audio(b64_audio: str):
    """Placeholder for future audio streaming support."""
    pass
