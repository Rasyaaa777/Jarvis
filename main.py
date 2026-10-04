import sys
from brain.router import IntentRouter
from memory.history import load_history, save_history
from rich.console import Console

console = Console()

# ─── Voice mode helpers ───────────────────────────────────────────────────────

from typing import Callable, Tuple, Optional

def _get_voice_modules() -> Tuple[Callable, Callable]:
    """Lazily import voice modules so text-only mode still works without sounddevice."""
    try:
        from tools.voice_input import listen_from_mic
        from tools.voice_output import speak
        return listen_from_mic, speak
    except ImportError as e:
        console.print(f"[bold red]Voice libs not installed:[/bold red] {e}")
        console.print("Run: [bold]pip install SpeechRecognition sounddevice numpy pyttsx3[/bold]")
        raise SystemExit(1)

# ─── Modes ────────────────────────────────────────────────────────────────────

def run_text_mode(router: IntentRouter, messages: list):
    """Classic text input / text output loop."""
    console.print("[bold green]JARVIS is online.[/bold green] "
                  "[dim]Mode: text | Type 'exit' to quit[/dim]")

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                break

            messages.append({"role": "user", "content": user_input})

            with console.status("[bold cyan]JARVIS is thinking...[/bold cyan]"):
                response_text = router.process_messages(messages)

            console.print(f"\n[bold blue]JARVIS:[/bold blue] {response_text}")

            messages.append({"role": "assistant", "content": response_text})
            save_history(messages)

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")


def run_voice_mode(router: IntentRouter, messages: list):
    """Fully hands-free: speak to JARVIS, JARVIS speaks back."""
    listen_from_mic, speak = _get_voice_modules()

    from tools.voice_input import get_best_microphone
    dev_id, dev_name = get_best_microphone()

    console.print("[bold green]JARVIS is online.[/bold green] "
                  "[dim]Mode: voice | Press Ctrl+C to quit[/dim]")
    console.print(f"[dim]Mikrofon Aktif: {dev_name} (ID: {dev_id})[/dim]")
    speak("JARVIS siap. Silakan bicara.")


    while True:
        try:
            console.print("\n[bold yellow]🎙  Listening...[/bold yellow]")
            user_input = listen_from_mic(language="id-ID")

            if user_input is None:
                continue  # Silence or noise — keep listening

            console.print(f"\n[bold white]You:[/bold white] {user_input}")

            # Allow voice exit commands
            lower_voice = user_input.lower().strip()
            if any(k in lower_voice for k in ["exit", "quit", "keluar", "tutup jarvis", "matikan jarvis"]):
                speak("Sampai jumpa!")
                break

            messages.append({"role": "user", "content": user_input})

            with console.status("[bold cyan]JARVIS is thinking...[/bold cyan]"):
                response_text = router.process_messages(messages)

            console.print(f"\n[bold blue]JARVIS:[/bold blue] {response_text}")
            speak(response_text)

            messages.append({"role": "assistant", "content": response_text})
            save_history(messages)

        except KeyboardInterrupt:
            speak("Sampai jumpa!")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")

def run_wake_word_mode(router: IntentRouter, messages: list):
    """Standby wake-word mode: activates hands-free when user says 'Hey Jarvis'."""
    listen_from_mic, speak = _get_voice_modules()

    import ctypes
    from tools.voice_input import wait_for_wake_word, get_best_microphone

    dev_id, dev_name = get_best_microphone()

    console.print("\n[bold green]JARVIS Wake Word Mode is Online.[/bold green]")
    console.print(f"[dim]Mikrofon: {dev_name} (ID: {dev_id})[/dim]")
    console.print("[bold cyan]Ucapkan [yellow]'Hey Jarvis'[/yellow] atau [yellow]'Jarvis'[/yellow] untuk mengaktifkan.[/bold cyan] [dim](Ctrl+C untuk keluar)[/dim]\n")
    speak("Mode Wake Word aktif. Silakan panggil Hey Jarvis.")

    while True:
        try:
            detected, immediate_cmd = wait_for_wake_word(language="id-ID")
            if not detected:
                continue

            # Play wake chime / system beep
            ctypes.windll.user32.MessageBeep(0)
            console.print("\n[bold yellow]⚡ Wake word terdeteksi![/bold yellow]")

            user_cmd = immediate_cmd
            if not user_cmd:
                speak("Ya, saya mendengarkan.")
                console.print("[bold yellow]🎙  Mendengarkan perintah...[/bold yellow]")
                user_cmd = listen_from_mic(language="id-ID")

            if not user_cmd:
                console.print("[dim]Tidak ada suara terdeteksi, kembali ke mode standby.[/dim]\n")
                continue

            console.print(f"\n[bold white]You:[/bold white] {user_cmd}")

            lower_cmd = user_cmd.lower().strip()
            if any(k in lower_cmd for k in ["exit", "quit", "keluar", "tutup jarvis", "matikan jarvis"]):
                speak("Sampai jumpa!")
                break

            messages.append({"role": "user", "content": user_cmd})

            with console.status("[bold cyan]JARVIS is thinking...[/bold cyan]"):
                response_text = router.process_messages(messages)

            console.print(f"\n[bold blue]JARVIS:[/bold blue] {response_text}")
            speak(response_text)

            messages.append({"role": "assistant", "content": response_text})
            save_history(messages)

            console.print("[dim]Kembali ke mode standby 'Hey Jarvis'...[/dim]\n")

        except KeyboardInterrupt:
            speak("Sampai jumpa!")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    # Start persistent reminder daemon in background
    from tools.reminder import start_reminder_daemon
    start_reminder_daemon()

    # Supported modes: text | voice | wake | tray | dashboard | web
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "wake"

    if mode in ["web", "webdash", "gui"]:
        from dashboard.web.server import start_server
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 5050
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{port}")
        start_server(port)
        return

    if mode in ["dashboard", "stats"]:
        from dashboard.terminal_dashboard import show_dashboard
        show_dashboard()
        return

    if mode in ["tray", "systemtray"]:
        from tray import run_tray
        run_tray()
        return

    router = IntentRouter()
    messages = load_history()  # Restore conversation from disk

    if mode == "text":
        run_text_mode(router, messages)
    elif mode == "voice":
        run_voice_mode(router, messages)
    else:
        run_wake_word_mode(router, messages)


if __name__ == "__main__":
    main()

