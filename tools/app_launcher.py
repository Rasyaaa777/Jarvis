import os
import json
import glob
import re
import subprocess
import winreg
from rapidfuzz import process, fuzz
import win32com.client

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(_BASE_DIR, "data", "apps_cache.json")

# Instant-launch protocol handlers and native Windows tools
KNOWN_SYSTEM_APPS = {
    "spotify": "spotify:",
    "notepad": "notepad.exe",
    "catatan": "notepad.exe",
    "calculator": "calc.exe",
    "kalkulator": "calc.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "settings": "ms-settings:",
    "pengaturan": "ms-settings:",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe"
}


def _launch_target(target: str) -> bool:
    """Launches an app target (can be a .lnk file, shell:AppsFolder URI, protocol, or .exe)."""
    try:
        os.startfile(target)
        return True
    except Exception:
        try:
            subprocess.Popen(f'start "" "{target}"', shell=True)
            return True
        except Exception:
            return False


def _scan_windows_apps_folder(apps: dict):
    """
    Scans modern Windows Store apps, UWP apps, and PWAs via PowerShell Get-StartApps.
    This registers apps like Spotify, Calculator, Camera, WhatsApp, CapCut, etc.
    """
    try:
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-StartApps | ConvertTo-Json"]
        output = subprocess.check_output(cmd, text=True, timeout=12)
        if output:
            data = json.loads(output)
            if isinstance(data, list):
                for item in data:
                    name = item.get("Name")
                    app_id = item.get("AppID")
                    if name and app_id and name not in apps:
                        # Filter out internal uninstaller entries
                        if not any(skip in name.lower() for skip in ["uninstall", "uninst", "setup", "update helper"]):
                            apps[name] = f"shell:AppsFolder\\{app_id}"
            elif isinstance(data, dict):
                name = data.get("Name")
                app_id = data.get("AppID")
                if name and app_id:
                    apps[name] = f"shell:AppsFolder\\{app_id}"
    except Exception as e:
        print(f"[AppLauncher] Note: Get-StartApps scan skipped ({e})")


def _scan_start_menu_shortcuts(apps: dict):
    """
    Scans Start Menu directories for .lnk shortcuts.
    Stores the .lnk shortcut file directly so custom arguments (e.g. Spotify PWA --app-id) are preserved.
    """
    paths = [
        os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "Microsoft\\Windows\\Start Menu\\Programs\\**\\*.lnk"),
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft\\Windows\\Start Menu\\Programs\\**\\*.lnk")
    ]

    for path in paths:
        for lnk_file in glob.glob(path, recursive=True):
            try:
                app_name = os.path.splitext(os.path.basename(lnk_file))[0]
                if not any(skip in app_name.lower() for skip in ["uninstall", "uninst", "setup", "helper", "manual", "documentation"]):
                    # If not already present or replacing an older target, keep the shortcut
                    if app_name not in apps:
                        apps[app_name] = lnk_file
            except Exception:
                pass


def _scan_registry_uninstall_keys(apps: dict):
    """Scans Windows Registry Uninstall keys for installed applications as backup source."""
    reg_roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
    ]

    for hkey, subkey_path in reg_roots:
        try:
            with winreg.OpenKey(hkey, subkey_path) as root_key:
                num_subkeys = winreg.QueryInfoKey(root_key)[0]
                for i in range(num_subkeys):
                    try:
                        subkey_name = winreg.EnumKey(root_key, i)
                        with winreg.OpenKey(root_key, subkey_name) as app_key:
                            try:
                                display_name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                                display_name = str(display_name).strip()
                            except OSError:
                                continue

                            if not display_name or any(skip in display_name.lower() for skip in ["update", "redistributable", "sdk", "driver"]):
                                continue

                            exe_path = None
                            try:
                                icon_val, _ = winreg.QueryValueEx(app_key, "DisplayIcon")
                                clean_icon = str(icon_val).split(",")[0].strip('"')
                                if clean_icon.lower().endswith(".exe") and os.path.exists(clean_icon):
                                    exe_path = clean_icon
                            except OSError:
                                pass

                            if exe_path and display_name not in apps:
                                apps[display_name] = exe_path
                    except OSError:
                        pass
        except OSError:
            pass


def build_app_cache() -> dict:
    """Scans all sources (Windows StartApps, Start Menu shortcuts, and Registry) and caches to JSON."""
    apps = {}
    # 1. Primary: Windows Get-StartApps (covers UWP, Store Apps, PWAs, desktop apps)
    _scan_windows_apps_folder(apps)
    # 2. Secondary: Start Menu .lnk shortcuts (keeps full flags and custom arguments)
    _scan_start_menu_shortcuts(apps)
    # 3. Tertiary: Registry entries
    _scan_registry_uninstall_keys(apps)

    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(apps, f, indent=4)

    return apps


def load_app_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    return data
        except Exception:
            pass
    return build_app_cache()


def refresh_apps() -> str:
    """Forces a fresh re-scan of all applications on the PC."""
    apps = build_app_cache()
    return f"Berhasil memindai ulang aplikasi di PC. Terdeteksi total {len(apps)} aplikasi yang siap dibuka."


def clean_query(app_name: str) -> str:
    """Strips leading verbs and trailing conversational particles."""
    text = app_name.strip()
    pattern_prefix = r"^(?:coba|tolong|bisa|mohon|buka|bukain|bukakan|open|jalankan|start|launch|putar|play|aplikasi|app)\s+"
    while re.search(pattern_prefix, text, flags=re.I):
        text = re.sub(pattern_prefix, "", text, flags=re.I).strip()

    pattern_suffix = r"\s+(?:dong|ya|kan|please|plis|sekarang|nih)$"
    while re.search(pattern_suffix, text, flags=re.I):
        text = re.sub(pattern_suffix, "", text, flags=re.I).strip()

    return text if text else app_name.strip()


def open_app(app_name: str) -> str:
    """
    Opens an installed Windows application by fuzzy matching or known protocol.
    Handles desktop apps, Store apps, Chrome PWAs, and .lnk shortcuts.
    """
    target_clean = clean_query(app_name).lower()

    # 1. Check known fast-launch protocols & system tools
    if target_clean in KNOWN_SYSTEM_APPS:
        fast_target = KNOWN_SYSTEM_APPS[target_clean]
        if _launch_target(fast_target):
            return f"Berhasil membuka {target_clean.title()}."

    # Check individual words for known system apps (e.g. "coba play spotify dong" -> "spotify")
    for word in target_clean.split():
        if word in KNOWN_SYSTEM_APPS:
            if _launch_target(KNOWN_SYSTEM_APPS[word]):
                return f"Berhasil membuka {word.title()}."

    # 2. Search cached installed applications
    apps = load_app_cache()
    if not apps:
        apps = build_app_cache()

    if not apps:
        return "Tidak ada aplikasi yang ditemukan di cache. Silakan minta saya untuk 'refresh aplikasi'."

    names = list(apps.keys())

    # Fuzzy match with token_sort_ratio
    match = process.extractOne(target_clean, names, scorer=fuzz.token_sort_ratio)

    # Fallback to partial ratio if standard token sort ratio is lower
    if not match or match[1] < 55:
        match_partial = process.extractOne(target_clean, names, scorer=fuzz.partial_ratio)
        if match_partial and match_partial[1] >= 75:
            match = match_partial

    if match and match[1] >= 55:  # Confident threshold
        matched_name = match[0]
        app_target = apps[matched_name]

        if _launch_target(app_target):
            return f"Berhasil membuka {matched_name}."
        else:
            return f"Gagal meluncurkan {matched_name} dari sistem."

    # 3. Direct protocol attempt if word is a single identifier (e.g. 'spotify', 'vlc', 'discord')
    if re.match(r"^[a-zA-Z0-9_\-]+$", target_clean):
        try_protocol = f"{target_clean}:"
        if _launch_target(try_protocol):
            return f"Berhasil membuka {target_clean.title()}."

    # Suggestions for close matches
    close_matches = process.extract(target_clean, names, scorer=fuzz.token_sort_ratio, limit=3)
    suggestions = [m[0] for m in close_matches if m[1] >= 35]
    if suggestions:
        return f"Tidak menemukan aplikasi yang persis '{app_name}'. Apakah maksud Anda: {', '.join(suggestions)}?"

    return f"Aplikasi '{app_name}' tidak ditemukan di sistem. Anda bisa mengatakan 'refresh aplikasi' jika baru saja menginstalnya."
