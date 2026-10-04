import ctypes
import datetime
from typing import Dict, Any

class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("SystemStatusFlag", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]

def adjust_volume(action: str = "up", steps: int = 2) -> str:
    """
    Adjusts Windows system master volume.
    Parameters:
        action: 'up' (increase), 'down' (decrease), or 'mute' (toggle mute).
        steps: Number of volume steps to adjust (1-10, default 2).
    """
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF

    action_clean = action.lower()
    if any(k in action_clean for k in ["mute", "bisu", "senyap", "unmute"]):
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
        return "Status volume (mute/unmute) berhasil dialihkan."
    elif any(k in action_clean for k in ["up", "naik", "tambah", "keraskan", "tinggi"]):
        count = max(1, min(int(steps), 15))
        for _ in range(count):
            ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
        return f"Volume berhasil dinaikkan sebanyak {count} tingkat."
    elif any(k in action_clean for k in ["down", "turun", "kurang", "kecilkan", "rendah"]):
        count = max(1, min(int(steps), 15))
        for _ in range(count):
            ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
        return f"Volume berhasil diturunkan sebanyak {count} tingkat."
    else:
        return f"Aksi volume '{action}' tidak dikenali. Pilih: 'up', 'down', atau 'mute'."

def get_system_status() -> str:
    """
    Returns current Windows PC status (battery, charging state, local time).
    """
    now = datetime.datetime.now().strftime("%A, %d %B %Y - %H:%M:%S")
    
    # Check battery status
    power_status = SYSTEM_POWER_STATUS()
    has_power_info = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(power_status))
    
    battery_info = "Informasi baterai tidak tersedia (desktop PC)."
    if has_power_info and power_status.BatteryLifePercent <= 100:
        percent = power_status.BatteryLifePercent
        charging = "Sedang mengisi daya (Plugged in)" if power_status.ACLineStatus == 1 else "Menggunakan daya baterai"
        battery_info = f"Baterai: {percent}% ({charging})"

    return f"Status Sistem PC:\n- Waktu Saat Ini: {now}\n- {battery_info}"
