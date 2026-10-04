import os
import json
import re
from typing import List, Dict, Any

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTS_FILE = os.path.join(_BASE_DIR, "data", "facts.json")


def load_facts() -> List[str]:
    if not os.path.exists(FACTS_FILE):
        return []
    with open(FACTS_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data.get("facts", [])
        except json.JSONDecodeError:
            return []

def save_facts(facts: List[str]):
    os.makedirs(os.path.dirname(FACTS_FILE), exist_ok=True)
    with open(FACTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"facts": facts}, f, indent=4)

def add_fact(fact: str):
    facts = load_facts()
    if fact not in facts:
        facts.append(fact)
        save_facts(facts)

def get_facts_context() -> str:
    facts = load_facts()
    if not facts:
        return ""
    return "Remember the following facts about the user:\n" + "\n".join([f"- {fact}" for fact in facts])

def auto_extract_facts(messages: List[Dict[str, Any]], provider_instance=None) -> List[str]:
    """
    Analyzes recent dialogue turns and extracts durable user facts/preferences.
    Saves any newly discovered facts to data/facts.json.
    """
    if not messages or not provider_instance:
        return []

    # Filter recent dialogue turns
    recent_turns = [
        m for m in messages[-6:]
        if m.get("role") in ["user", "assistant"] and isinstance(m.get("content"), str) and m.get("content").strip()
    ]
    if len(recent_turns) < 2:
        return []

    existing_facts = load_facts()
    facts_str = json.dumps(existing_facts, ensure_ascii=False)
    dialogue_snippets = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in recent_turns])

    extraction_prompt = [
        {
            "role": "system",
            "content": (
                "You are an AI long-term memory assistant. Your goal is to identify and extract any NEW, "
                "durable personal facts, habits, occupation, name, preferences, or details about the USER from the dialogue snippet.\n"
                "- Do NOT extract temporary requests, casual greetings, or one-off tasks (e.g. 'user asked to open Chrome', 'user asked for weather').\n"
                "- Only extract lasting personal attributes (e.g. 'User bernama Rasya', 'User bekerja sebagai desainer', 'User suka minum kopi tanpa gula').\n"
                "- Do NOT repeat facts that are already known.\n"
                f"- Already known facts: {facts_str}\n"
                "Respond ONLY with a valid JSON array of strings containing the new facts (in Indonesian). "
                "If there are no new personal facts to record, respond strictly with []."
            )
        },
        {
            "role": "user",
            "content": f"Recent dialogue to analyze:\n{dialogue_snippets}"
        }
    ]

    try:
        response = provider_instance.send(extraction_prompt)
        content = response.get("content", "").strip()
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            new_facts = json.loads(match.group(0))
            added = []
            if isinstance(new_facts, list):
                for fact in new_facts:
                    clean = str(fact).strip()
                    if clean and clean not in existing_facts:
                        add_fact(clean)
                        added.append(clean)
            if added:
                print(f"[Memory] Fakta baru tentang pengguna otomatis disimpan: {added}")
            return added
    except Exception:
        pass

    return []
