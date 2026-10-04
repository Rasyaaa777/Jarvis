uimport os
import sys
import subprocess
import threading
import ctypes
import pystray
from PIL import Image, ImageDraw

# Ensure project root is in sys.path
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from brain.router import IntentRouter
from memory.history import load_history, save_history
from config import ACTIVE_PROVIDER

# Global state for tray app
_wake_thread = None
_wake_running = False
_router = None
_messages = None
_tray_icon = None


def create_jarvis_icon():
    """Generates a high-tech glowing cyan Arc-Reactor style icon for JARVIS."""
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Outer cyan ring
    draw.ellipse((4, 4, 60, 60), outline=(0, 210, 255, 255), width=4)
    # Inner tech ring
    draw.ellipse((14, 14, 50, 50), outline=(0, 160, 255, 220), width=3)
    # Glowing center core
    draw.ellipse((22, 22, 42, 42), fill=(0, 235, 255, 255))
    return image


def _wake_word_loop():
    """Background listener for 'Hey Jarvis' wake word."""
    global _wake_running, _router, _messages
    from tools.voice_input import wait_for_wake_word, listen_from_mic
    from tools.voice_output import speak

    speak("Mode hands-free aktif. Ucapkan Hey Jarvis kapan saja.")

    while _wake_running:
        try:
            detected, immediate_cmd = wait_for_wake_word(language="id-ID")
            if not detected or not _wake_running:
                continue

            # Play wake chime
            ctypes.windll.user32.MessageBeep(0)

            cmd = immediate_cmd
            if not cmd:
                speak("Ya, saya mendengarkan.")
                cmd = listen_from_mic(language="id-ID")

            if not cmd or not _wake_running:
                continue

            if cmd.lower() in ["berhenti", "stop", "matikan"]:
                speak("Sampai jumpa.")
                break

            _messages.append({"role": "user", "content": cmd})
            resp = _router.process_messages(_messages)
            _messages.append({"role": "assistant", "content": resp})
            save_history(_messages)

            speak(resp)

        except Exception as e:
            print(f"[Tray Voice Error] {e}")


def toggle_wake_word(icon, item):
    global _wake_running, _wake_thread, _router, _messages
    if _router is None:
        _router = IntentRouter()
        _messages = load_history()

    if _wake_running:
        _wake_running = False
        from tools.voice_output import speak
        speak("Mode hands-free dinonaktifkan.")
        icon.notify("Mode Wake Word dinonaktifkan.", "JARVIS AI")
    else:
        _wake_running = True
        _wake_thread = threading.Thread(target=_wake_word_loop, daemon=True)
        _wake_thread.start()
        icon.notify("Mode Wake Word Aktif! Ucapkan 'Hey Jarvis'.", "JARVIS AI")


def open_terminal_chat(icon=None, item=None):
    """Spawns an interactive text chat in a new console window."""
    script_path = os.path.join(_BASE_DIR, "main.py")
    subprocess.Popen(f'start cmd /k python "{script_path}" text', shell=True)


def open_dashboard_window(icon=None, item=None):
    """Spawns the terminal usage & cost dashboard in a new console window."""
    dash_path = os.path.join(_BASE_DIR, "dashboard", "terminal_dashboard.py")
    subprocess.Popen(f'start cmd /k python "{dash_path}"', shell=True)


def open_web_dashboard(icon=None, item=None):
    """Spawns the interactive Web Dashboard in browser."""
    script_path = os.path.join(_BASE_DIR, "main.py")
    subprocess.Popen(f'python "{script_path}" web', shell=True)


def switch_provider_action(provider_name: str):
    def _action(icon, item):
        global _router
        if _router is None:
            _router = IntentRouter()
        res = _router.switch_provider(provider_name)
        icon.notify(res, "JARVIS AI Provider")
    return _action


def quit_tray_app(icon, item):
    global _wake_running
    _wake_running = False
    icon.stop()


def run_tray():
    """Runs the system tray icon for JARVIS."""
    global _tray_icon, _router, _messages
    _router = IntentRouter()
    _messages = load_history()

    image = create_jarvis_icon()
    provider = (_router.active_provider_name or ACTIVE_PROVIDER).upper()

    menu = pystray.Menu(
        pystray.MenuItem(f"JARVIS AI ({provider})", lambda: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Mode Wake Word ('Hey Jarvis')", toggle_wake_word, checked=lambda item: _wake_running),
        pystray.MenuItem("Buka Obrolan Terminal (Text)", open_terminal_chat),
        pystray.MenuItem("Buka Web Dashboard (Browser)", open_web_dashboard),
        pystray.MenuItem("Buka Dashboard Terminal", open_dashboard_window),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Ganti ke Gemini", switch_provider_action("gemini")),
        pystray.MenuItem("Ganti ke OpenAI (GPT)", switch_provider_action("openai")),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Keluar (Quit)", quit_tray_app)
    )

    _tray_icon = pystray.Icon("JARVIS", image, "JARVIS AI Assistant", menu)
    print("JARVIS System Tray aktif di area notifikasi Windows (kanan bawah).")
    _tray_icon.run()


if __name__ == "__main__":
    run_tray()
