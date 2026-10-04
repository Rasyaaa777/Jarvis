import os
import json
from typing import List, Dict, Any

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_FILE = os.path.join(_BASE_DIR, "data", "history.json")
MAX_HISTORY_LENGTH = 50

def load_history() -> List[Dict[str, Any]]:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_history(history: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    # Keep only the last MAX_HISTORY_LENGTH messages
    if len(history) > MAX_HISTORY_LENGTH:
        history = history[-MAX_HISTORY_LENGTH:]
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)

def append_to_history(message: Dict[str, Any]):
    history = load_history()
    history.append(message)
    save_history(history)
