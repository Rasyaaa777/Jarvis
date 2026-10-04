import os
from typing import Dict, Any, Callable
from tools import app_launcher
from tools import web_search
from tools import weather
from tools import system_control
from tools import reminder
from memory import facts as facts_module

# Dictionary mapping tool names to execution functions
_TOOL_FUNCTIONS: Dict[str, Callable] = {}

def remember_fact(fact: str) -> str:
    """Save a user fact into long-term memory."""
    facts_module.add_fact(fact)
    return f"Saya sudah mengingat fakta ini: '{fact}'."

def get_all_tools() -> list[dict[str, Any]]:
    """Returns the JSON schema definitions of all available tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": "open_app",
                "description": "Opens an installed Windows application by fuzzy-matching its name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "description": "The name of the app to open, e.g., 'capcut', 'spotify', 'chrome', 'notepad'"
                        }
                    },
                    "required": ["app_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "remember_fact",
                "description": "Saves a permanent fact, preference, or detail about the user to long-term memory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fact": {
                            "type": "string",
                            "description": "The specific fact or preference to store about the user (e.g. 'User nama Rasya', 'User suka minum kopi tanpa gula')"
                        }
                    },
                    "required": ["fact"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Searches the web for recent events, news, or general factual information not in the model's memory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search keyword or query"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Gets the current real-time weather and forecast for any city in the world.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "The city name, e.g., 'Jakarta', 'Bandung', 'Tokyo', 'London'"
                        }
                    },
                    "required": ["city"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "adjust_volume",
                "description": "Adjusts or mutes the master volume on the Windows PC.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Volume action: 'up' (increase), 'down' (decrease), or 'mute' (toggle mute)"
                        },
                        "steps": {
                            "type": "integer",
                            "description": "Number of volume steps to change (e.g. 2, 4, 6). Default is 2."
                        }
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_system_status",
                "description": "Checks current Windows PC time, battery percentage, and charging state.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "set_reminder",
                "description": "Sets a local reminder timer on the PC with sound and message alert.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The reminder note or task (e.g. 'Minum air', 'Meeting dimulai')"
                        },
                        "delay_seconds": {
                            "type": "integer",
                            "description": "Delay in seconds until the reminder triggers (e.g., 60 for 1 minute, 300 for 5 minutes)"
                        }
                    },
                    "required": ["message", "delay_seconds"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_reminders",
                "description": "Lists all currently pending and active scheduled reminders.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "cancel_reminder",
                "description": "Cancels an active reminder by ID or matching keyword/message note.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The reminder ID (number) or keyword note to cancel (e.g. '1', 'minum air')"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "refresh_apps",
                "description": "Re-scans the Windows PC to discover and refresh all installed applications into the cache. Use this when the user asks to refresh apps, update app list, or says they just installed a new software.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    ]

def register_tool(name: str, func: Callable):
    _TOOL_FUNCTIONS[name] = func

# Register all tools
register_tool("open_app", app_launcher.open_app)
register_tool("refresh_apps", app_launcher.refresh_apps)
register_tool("remember_fact", remember_fact)
register_tool("search_web", web_search.search_web)
register_tool("get_weather", weather.get_weather)
register_tool("adjust_volume", system_control.adjust_volume)
register_tool("get_system_status", system_control.get_system_status)
register_tool("set_reminder", reminder.set_reminder)
register_tool("list_reminders", reminder.list_reminders)
register_tool("cancel_reminder", reminder.cancel_reminder)

def execute_tool(name: str, arguments: Dict[str, Any]) -> Any:
    """Executes a registered tool by name with the given arguments."""
    if name not in _TOOL_FUNCTIONS:
        return f"Error: Tool '{name}' not found."
    
    try:
        return _TOOL_FUNCTIONS[name](**arguments)
    except Exception as e:
        return f"Error executing tool '{name}': {str(e)}"
