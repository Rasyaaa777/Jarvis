import os
import sqlite3
import threading
import time
import ctypes
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from rich.console import Console

console = Console()

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(_BASE_DIR, "data", "app.db")

_daemon_started = False
_daemon_lock = threading.Lock()


def _get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=15.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
    except Exception:
        pass
    return conn


def _init_reminder_table():
    conn = _get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                due_timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
            )
        ''')
        conn.commit()
    finally:
        conn.close()


def _trigger_reminder(rem_id: int, message: str):
    """Fires alert when a reminder is due, then updates its status."""
    conn = _get_connection()
    try:
        c = conn.cursor()
        c.execute("UPDATE reminders SET status = 'triggered' WHERE id = ?", (rem_id,))
        conn.commit()
    finally:
        conn.close()

    # Play system chime
    try:
        ctypes.windll.user32.MessageBeep(0xFFFFFFFF)
    except Exception:
        pass

    console.print(f"\n[bold yellow]🔔 [PENGINGAT JARVIS][/bold yellow] [bold white]{message}[/bold white]")

    # Speak aloud
    try:
        from tools.voice_output import speak
        speak(f"Perhatian, pengingat untuk Anda: {message}")
    except Exception:
        pass


def _reminder_daemon_loop():
    """Background polling worker that checks for due reminders every 3 seconds."""
    _init_reminder_table()
    while True:
        try:
            now_iso = datetime.now().isoformat()
            conn = _get_connection()
            due_items = []
            try:
                c = conn.cursor()
                c.execute(
                    "SELECT id, message FROM reminders WHERE status = 'pending' AND due_timestamp <= ? ORDER BY due_timestamp ASC",
                    (now_iso,)
                )
                due_items = c.fetchall()
            finally:
                conn.close()

            for rem_id, msg in due_items:
                _trigger_reminder(rem_id, msg)

        except Exception as e:
            print(f"[Reminder Daemon Error] {e}")

        time.sleep(3)


def start_reminder_daemon():
    """Starts the background reminder scheduler thread if not already running."""
    global _daemon_started
    with _daemon_lock:
        if not _daemon_started:
            _init_reminder_table()
            thread = threading.Thread(target=_reminder_daemon_loop, daemon=True, name="ReminderDaemon")
            thread.start()
            _daemon_started = True


# Auto-start daemon when module is imported
start_reminder_daemon()


def set_reminder(message: str, delay_seconds: int = 60) -> str:
    """
    Sets a durable reminder with sound & voice alert, saved to database.
    Survives PC restarts and application reboots.
    """
    _init_reminder_table()
    start_reminder_daemon()

    delay = max(1, int(delay_seconds))
    now = datetime.now()
    due_dt = now + timedelta(seconds=delay)
    due_iso = due_dt.isoformat()
    created_iso = now.isoformat()

    conn = _get_connection()
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO reminders (message, due_timestamp, created_at, status) VALUES (?, ?, ?, 'pending')",
            (message, due_iso, created_iso)
        )
        conn.commit()
        rem_id = c.lastrowid
    finally:
        conn.close()

    minutes = delay // 60
    secs = delay % 60
    time_str = ""
    if minutes > 0:
        time_str += f"{minutes} menit "
    if secs > 0 or minutes == 0:
        time_str += f"{secs} detik"

    return f"Pengingat disetel untuk {time_str.strip()} lagi (pukul {due_dt.strftime('%H:%M')}): '{message}'."


def list_reminders() -> str:
    """Returns all currently active (pending) reminders."""
    _init_reminder_table()
    start_reminder_daemon()

    conn = _get_connection()
    try:
        c = conn.cursor()
        c.execute(
            "SELECT id, message, due_timestamp FROM reminders WHERE status = 'pending' ORDER BY due_timestamp ASC"
        )
        rows = c.fetchall()
    finally:
        conn.close()

    if not rows:
        return "Tidak ada pengingat yang sedang aktif saat ini."

    results = ["Daftar pengingat aktif Anda:"]
    for rem_id, msg, due_iso in rows:
        try:
            due_dt = datetime.fromisoformat(due_iso)
            time_formatted = due_dt.strftime("%d %b %H:%M")
        except Exception:
            time_formatted = due_iso
        results.append(f"- [ID {rem_id}] '{msg}' (Jadwal: {time_formatted})")

    return "\n".join(results)


def cancel_reminder(query: str) -> str:
    """
    Cancels an active reminder by ID or matching keyword in note.
    """
    _init_reminder_table()
    conn = _get_connection()
    try:
        c = conn.cursor()
        # 1. Try by exact ID
        clean = query.strip()
        if clean.isdigit():
            c.execute("UPDATE reminders SET status = 'cancelled' WHERE id = ? AND status = 'pending'", (int(clean),))
            if c.rowcount > 0:
                conn.commit()
                return f"Pengingat nomor #{clean} berhasil dibatalkan."

        # 2. Try by matching message text
        c.execute(
            "UPDATE reminders SET status = 'cancelled' WHERE message LIKE ? AND status = 'pending'",
            (f"%{clean}%",)
        )
        if c.rowcount > 0:
            conn.commit()
            return f"Pengingat yang berkaitan dengan '{clean}' berhasil dibatalkan."

        return f"Tidak ditemukan pengingat aktif yang cocok dengan '{query}'."
    finally:
        conn.close()
