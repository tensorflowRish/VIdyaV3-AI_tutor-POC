"""
config.py — Loads environment variables and provides app-wide constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

SYSTEM_PROMPT_PATH:    Path = ROOT_DIR / "prompts" / "system_prompt.txt"
CONVERSATION_LOG_PATH: Path = ROOT_DIR / "logs" / "conversations.json"

VALID_ICP_TYPES  = ["low_wage", "high_wage"]
VALID_CA_PHASES  = ["MODEL", "COACH", "SCAFFOLD", "FADE"]
VALID_LANGUAGES  = ["en", "hi", "mixed"]

GEMINI_TEMPERATURE      = 0.3
GEMINI_MAX_OUTPUT_TOKENS = 512

if not GEMINI_API_KEY:
    raise EnvironmentError(
        "\n[ERROR] GEMINI_API_KEY is not set.\n"
        "  1. Copy .env.example to .env\n"
        "  2. Add your Gemini API key\n"
        "  3. Run again.\n"
    )
