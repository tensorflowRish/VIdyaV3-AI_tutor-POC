"""
gemini_client.py — Calls Gemini with automatic retry, backoff, and graceful error handling.

Error handling layers:
1. Rate limit (429)  → extract retry-after seconds, wait, retry up to 3 times
2. Server error (5xx)→ exponential backoff, retry up to 3 times
3. All retries fail  → raise GeminiUnavailableError (caught by tutor_session)
4. tutor_session     → returns friendly fallback response to user
"""

import json
import time
import re
import logging
from google import genai
from google.genai import types

from src.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_MAX_OUTPUT_TOKENS,
)

logger = logging.getLogger(__name__)

# ── Custom exception ──────────────────────────────────────────────────────────

class GeminiUnavailableError(Exception):
    """Raised when Gemini is unavailable after all retries."""
    def __init__(self, reason: str, retry_after: int = 0):
        self.reason      = reason
        self.retry_after = retry_after   # seconds user should wait
        super().__init__(reason)


# ── Retry config ──────────────────────────────────────────────────────────────

MAX_RETRIES       = 3
BASE_BACKOFF      = 2    # seconds — doubles each retry for server errors
MAX_BACKOFF       = 30   # seconds cap
RATE_LIMIT_WAIT   = 20   # default wait if API doesn't tell us how long


# ── Client ────────────────────────────────────────────────────────────────────

_client = genai.Client(api_key=GEMINI_API_KEY)


# ── Prompt builder ────────────────────────────────────────────────────────────

def _compose_prompt(
    system_prompt: str,
    session_config: dict,
    conversation_history: list[dict],
    user_message: str,
) -> str:
    lines = []

    lines.append("=== SYSTEM PROMPT ===")
    lines.append(system_prompt.strip())
    lines.append("")

    lines.append("=== SESSION CONFIG ===")
    lines.append(json.dumps(session_config, ensure_ascii=False, indent=2))
    lines.append("")

    if conversation_history:
        lines.append("=== CONVERSATION HISTORY (most recent last) ===")
        for turn in conversation_history[-10:]:
            role_label = "User" if turn["role"] == "user" else "Tutor"
            lines.append(f"{role_label}: {turn['content']}")
        lines.append("")

    lines.append("=== LATEST USER MESSAGE ===")
    lines.append(user_message.strip())
    lines.append("")

    lang = session_config.get("language_preference", "en") if session_config else "en"
    lang_instructions = {
        "hi":    "MANDATORY: Your tutor_response MUST be in Hindi or Hinglish. No full English sentences.",
        "mixed": "MANDATORY: Your tutor_response MUST mix Hindi and English in every sentence.",
        "en":    "Respond in English only.",
    }
    lines.append("=== LANGUAGE INSTRUCTION (OVERRIDE) ===")
    lines.append(lang_instructions.get(lang, "Respond in English only."))
    lines.append("")
    lines.append("Respond ONLY with a valid JSON object as specified in the system prompt.")

    return "\n".join(lines)


# ── Error classifier ──────────────────────────────────────────────────────────

def _extract_retry_after(error_str: str) -> int:
    """
    Tries to extract retry delay from the error message.
    Gemini 429 errors often say 'Please retry in 18.3s'.
    Returns seconds to wait, or RATE_LIMIT_WAIT as default.
    """
    match = re.search(r"retry[^\d]*(\d+(?:\.\d+)?)\s*s", error_str, re.IGNORECASE)
    if match:
        return int(float(match.group(1))) + 2   # add 2s buffer
    return RATE_LIMIT_WAIT


def _is_rate_limit(error) -> bool:
    err = str(error)
    return "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower()


def _is_server_error(error) -> bool:
    err = str(error)
    return any(code in err for code in ["500", "502", "503", "504", "UNAVAILABLE"])


# ── Main call with retry ──────────────────────────────────────────────────────

def call_gemini(
    system_prompt: str,
    session_config: dict,
    conversation_history: list[dict],
    user_message: str,
) -> str:
    """
    Calls Gemini with automatic retry and backoff.
    Returns raw response text on success.
    Raises GeminiUnavailableError on total failure.
    """
    prompt = _compose_prompt(
        system_prompt, session_config, conversation_history, user_message
    )

    config = types.GenerateContentConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
    )

    last_error     = None
    last_wait      = 0

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = _client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config,
            )
            return response.text   # success

        except Exception as e:
            last_error = e
            err_str    = str(e)

            if _is_rate_limit(e):
                wait = _extract_retry_after(err_str)
                last_wait = wait
                logger.warning(f"Rate limit hit (attempt {attempt}/{MAX_RETRIES}). Waiting {wait}s...")

                if attempt < MAX_RETRIES:
                    time.sleep(wait)
                    continue
                else:
                    raise GeminiUnavailableError(
                        reason="rate_limit",
                        retry_after=wait,
                    )

            elif _is_server_error(e):
                wait = min(BASE_BACKOFF * (2 ** (attempt - 1)), MAX_BACKOFF)
                logger.warning(f"Server error (attempt {attempt}/{MAX_RETRIES}). Waiting {wait}s...")

                if attempt < MAX_RETRIES:
                    time.sleep(wait)
                    continue
                else:
                    raise GeminiUnavailableError(
                        reason="server_error",
                        retry_after=0,
                    )

            else:
                # Unknown error — don't retry
                raise GeminiUnavailableError(
                    reason=f"unknown: {err_str[:100]}",
                    retry_after=0,
                )

    raise GeminiUnavailableError(reason="max_retries_exceeded", retry_after=last_wait)


def transcribe_audio_bytes(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """
    Transcribes user audio using Gemini multimodal input.
    Returns plain transcript text.
    """
    try:
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                (
                    "Transcribe this user audio message. Return only the exact spoken "
                    "text, with no commentary, no labels, and no markdown."
                ),
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
            ),
        )
        return (response.text or "").strip()
    except Exception as e:
        raise GeminiUnavailableError(reason=f"transcription_failed: {str(e)[:100]}", retry_after=0)
