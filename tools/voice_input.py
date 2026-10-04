import io
import wave
import time
import re
import collections
from typing import Optional, Tuple
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from rich.console import Console

console = Console()

# ── Audio settings ──────────────────────────────────────────────────────────
SAMPLE_RATE = 16000   # Hz — optimal for Google STT
CHUNK_SIZE  = 1024    # Samples per block (~64ms)
MAX_DURATION = 15     # Max seconds to record
SILENCE_DURATION = 1.1  # Seconds of silence after speech to finish recording
PRE_SPEECH_CHUNKS = 6   # Keep last ~0.35s before speech to avoid cutting first syllable

_recognizer = sr.Recognizer()
_cached_device_id: Optional[int] = None
_cached_device_name: Optional[str] = None


def get_best_microphone() -> Tuple[Optional[int], str]:
    """
    Selects the best physical microphone.
    Avoids virtual audio inputs (like Iriun, DroidCam, OBS) that send silent streams.
    """
    global _cached_device_id, _cached_device_name
    if _cached_device_id is not None:
        return _cached_device_id, _cached_device_name or "Default Mic"

    devices = sd.query_devices()
    physical_candidates = []

    for idx, dev in enumerate(devices):
        if dev.get("max_input_channels", 0) > 0:
            name = dev.get("name", "")
            lower = name.lower()
            # Filter out virtual/dummy webcams and loopbacks
            is_virtual = any(v in lower for v in ["iriun", "droidcam", "obs", "mapper", "stereo mix", "virtual"])
            if not is_virtual:
                physical_candidates.append((idx, name))

    # Priority 1: Connected Realtek / Headset microphone
    for idx, name in physical_candidates:
        lower = name.lower()
        if "realtek" in lower or "headset" in lower or "array" in lower or "microphone" in lower:
            _cached_device_id = idx
            _cached_device_name = name
            return idx, name

    # Priority 2: Any non-virtual candidate
    if physical_candidates:
        _cached_device_id = physical_candidates[0][0]
        _cached_device_name = physical_candidates[0][1]
        return _cached_device_id, _cached_device_name

    # Fallback to system default
    default_dev = sd.default.device[0]
    dev_name = sd.query_devices(default_dev)["name"] if default_dev is not None else "Default"
    _cached_device_id = default_dev
    _cached_device_name = dev_name
    return default_dev, dev_name


def _record_utterance(device_id: Optional[int]) -> Optional[np.ndarray]:
    """
    Streams audio using dynamic Voice Activity Detection (VAD).
    Calibrates noise floor, buffers pre-speech, and records until silence.
    """
    # Wait if JARVIS is currently speaking to avoid self-listening loop
    try:
        from tools.voice_output import is_speaking
        while is_speaking():
            time.sleep(0.1)
        time.sleep(0.15)
    except Exception:
        pass

    pre_buffer = collections.deque(maxlen=PRE_SPEECH_CHUNKS)
    recorded_chunks = []
    speech_detected = False
    silent_chunks_count = 0

    max_silent_chunks = int(SILENCE_DURATION * SAMPLE_RATE / CHUNK_SIZE)
    max_total_chunks  = int(MAX_DURATION * SAMPLE_RATE / CHUNK_SIZE)

    try:
        with sd.InputStream(device=device_id, samplerate=SAMPLE_RATE, channels=1,
                            dtype="int16", blocksize=CHUNK_SIZE) as stream:
            
            # Step 1: Quick noise floor calibration (~0.2s)
            calibration_chunks = []
            for _ in range(3):
                data, _ = stream.read(CHUNK_SIZE)
                calibration_chunks.append(data.astype(np.float32))
            
            noise_rms = float(np.sqrt(np.mean(np.concatenate(calibration_chunks) ** 2))) if calibration_chunks else 50.0
            # Dynamic threshold: minimum 80, or 2.5x ambient noise
            speech_threshold = max(75.0, noise_rms * 2.5 + 25.0)

            # Step 2: Main listening loop
            for _ in range(max_total_chunks):
                # Abort if JARVIS started speaking unexpectedly
                try:
                    from tools.voice_output import is_speaking
                    if is_speaking():
                        return None
                except Exception:
                    pass

                data, _ = stream.read(CHUNK_SIZE)
                rms = float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))

                if rms > speech_threshold:
                    if not speech_detected:
                        speech_detected = True
                        console.print("[bold green]🎙  Mendengar suara Anda...[/bold green]")
                        # Prepend buffered pre-speech audio
                        recorded_chunks.extend(list(pre_buffer))
                    
                    silent_chunks_count = 0
                    recorded_chunks.append(data.copy())

                elif speech_detected:
                    recorded_chunks.append(data.copy())
                    silent_chunks_count += 1
                    if silent_chunks_count >= max_silent_chunks:
                        break  # User finished speaking
                else:
                    pre_buffer.append(data.copy())

    except Exception as e:
        console.print(f"[bold red]Audio Stream Error:[/bold red] {e}")
        return None

    if not recorded_chunks or not speech_detected:
        return None

    return np.concatenate(recorded_chunks)


def _to_wav_bytes(audio: np.ndarray) -> bytes:
    """Converts int16 numpy audio to in-memory WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)   # 16-bit = 2 bytes
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


def listen_from_mic(language: str = "id-ID") -> Optional[str]:
    """
    Listens from the best physical microphone and returns transcribed text.
    Supports Indonesian ('id-ID') and English ('en-US').
    """
    try:
        from tools.voice_output import is_speaking
        while is_speaking():
            time.sleep(0.1)
        time.sleep(0.15)
    except Exception:
        pass
    dev_id, dev_name = get_best_microphone()
    audio = _record_utterance(dev_id)
    if audio is None:
        return None

    wav_bytes = _to_wav_bytes(audio)
    buf = io.BytesIO(wav_bytes)

    with sr.AudioFile(buf) as source:
        recorded = _recognizer.record(source)

    try:
        # Recognize speech using Google STT
        text = _recognizer.recognize_google(recorded, language=language)
        return text.strip() if text else None
    except sr.UnknownValueError:
        # Could not distinguish speech from noise
        return None
    except sr.RequestError as e:
        console.print(f"[bold red][Voice Error] Google STT service unavailable:[/bold red] {e}")
        return None


def check_wake_word(text: str) -> Tuple[bool, Optional[str]]:
    """
    Checks if text contains wake word triggers: 'hey jarvis', 'halo jarvis', 'hai jarvis', or 'jarvis'.
    Returns (is_detected, trailing_command).
    """
    if not text:
        return False, None
    lower = text.lower().strip()
    
    patterns = [
        r"^(?:hey|hai|halo|ok|oke)?\s*jarvis\b[,!.]?\s*(.*)$",
        r"\bjarvis\b[,!.]?\s*(.*)$"
    ]
    for pat in patterns:
        m = re.search(pat, lower)
        if m:
            command = m.group(1).strip()
            return True, command if command else None
    return False, None


def wait_for_wake_word(language: str = "id-ID") -> Tuple[bool, Optional[str]]:
    """
    Listens once and returns (True, optional_command) if wake word was detected.
    """
    text = listen_from_mic(language=language)
    if text:
        detected, command = check_wake_word(text)
        if detected:
            return True, command
    return False, None

