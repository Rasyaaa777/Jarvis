import os
import re
import uuid
import ctypes
import asyncio
import tempfile
import threading
from typing import Optional

# Optional fallback engine (pyttsx3 for offline)
_pyttsx_engine = None
_lock = threading.Lock()
_is_speaking = False

# Preferred Neural voice
# 'id-ID-ArdiNeural' (Male Indo, JARVIS-like), 'id-ID-GadisNeural' (Female Indo)
VOICE_ID = "id-ID-ArdiNeural"
VOICE_RATE = "+15%"


def is_speaking() -> bool:
    """Returns True if JARVIS is currently speaking audio aloud."""
    return _is_speaking


def clean_markdown_for_speech(text: str) -> str:
    """Strips markdown formatting, URLs, code blocks, and symbols for natural voice output."""
    if not text:
        return ""
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Remove inline code
    text = re.sub(r"`[^`]*`", "", text)
    # Remove markdown bold/italics/headings
    text = re.sub(r"[\*_#~]", "", text)
    # Remove numbered list markers and bullet points
    text = re.sub(r"^\s*[0-9]+[.)]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s*", "", text, flags=re.MULTILINE)
    # Remove links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove raw URLs
    text = re.sub(r"https?://\S+", "", text)
    # Clean up double punctuation and spacing
    text = re.sub(r"\n+", ". ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _get_pyttsx_engine():
    global _pyttsx_engine
    if _pyttsx_engine is None:
        try:
            import pyttsx3
            _pyttsx_engine = pyttsx3.init()
            _pyttsx_engine.setProperty("rate", 175)
            _pyttsx_engine.setProperty("volume", 1.0)
        except Exception:
            _pyttsx_engine = None
    return _pyttsx_engine


async def _synthesize_edge(clean_text: str, mp3_path: str):
    import edge_tts
    tts = edge_tts.Communicate(clean_text, VOICE_ID, rate=VOICE_RATE)
    await tts.save(mp3_path)


def _play_mp3_windows(mp3_path: str):
    """Plays MP3 using native Windows winmm.dll (no external audio player needed)."""
    winmm = ctypes.windll.winmm
    alias = f"jarvis_{uuid.uuid4().hex[:8]}"
    abs_path = os.path.abspath(mp3_path)
    
    try:
        winmm.mciSendStringW(f'open "{abs_path}" type mpegvideo alias {alias}', None, 0, None)
        winmm.mciSendStringW(f'play {alias} wait', None, 0, None)
    finally:
        winmm.mciSendStringW(f'close {alias}', None, 0, None)


def speak(text: str):
    """
    Converts text to human-like speech and plays it aloud.
    Uses Microsoft Edge Neural TTS with SAPI5 offline fallback.
    """
    global _is_speaking
    clean_text = clean_markdown_for_speech(text)
    if not clean_text:
        return

    with _lock:
        _is_speaking = True
        try:
            # Try Edge Neural TTS first (crisp, natural human voice)
            temp_mp3 = os.path.join(tempfile.gettempdir(), f"jarvis_speech_{uuid.uuid4().hex[:8]}.mp3")
            try:
                asyncio.run(_synthesize_edge(clean_text, temp_mp3))
                _play_mp3_windows(temp_mp3)
                return
            except Exception:
                pass
            finally:
                if os.path.exists(temp_mp3):
                    try:
                        os.remove(temp_mp3)
                    except Exception:
                        pass

            # Offline fallback to pyttsx3
            engine = _get_pyttsx_engine()
            if engine:
                try:
                    engine.say(clean_text)
                    engine.runAndWait()
                except Exception:
                    pass
        finally:
            _is_speaking = False


def stop_speaking():
    """Stops ongoing pyttsx speech if active."""
    global _is_speaking
    engine = _get_pyttsx_engine()
    if engine:
        try:
            engine.stop()
        except Exception:
            pass
    _is_speaking = False
