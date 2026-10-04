import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ACTIVE_PROVIDER = os.getenv("ACTIVE_PROVIDER", "gemini")

# Budget and pricing settings
MONTHLY_BUDGET = float(os.getenv("MONTHLY_BUDGET", "5.0"))
BUDGET_ALERT_THRESHOLD = float(os.getenv("BUDGET_ALERT_THRESHOLD", "0.8"))

SYSTEM_PROMPT_PATH = os.path.join(BASE_DIR, "system_prompt.txt")
PRICING_PATH = os.path.join(BASE_DIR, "pricing.json")

if ACTIVE_PROVIDER == "openai" and not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY is not set.")
if ACTIVE_PROVIDER == "gemini" and not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY is not set.")
