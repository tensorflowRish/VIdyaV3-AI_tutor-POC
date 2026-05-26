"""
gemini_client.py — Calls Gemini using the modern google-genai SDK.
Composes a single prompt: system_prompt + session config + history + user message.
Returns raw text from Gemini (expected to be JSON).
"""

import json
from google import genai
from google.genai import types

from src.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_MAX_OUTPUT_TOKENS,
)


# Initialise client once at module load
_client = genai.Client(api_key=GEMINI_API_KEY)


def _compose_prompt(
    system_prompt: str,
    session_config: dict,
    conversation_history: list[dict],
    user_message: str,
) -> str:
    """
    Builds a single text prompt that gives Gemini full context.
    Structure:
        [SYSTEM]         — tutor identity + rules
        [SESSION CONFIG] — topic, mastery, phase, language, ICP
        [CONVERSATION]   — prior turns
        [USER MESSAGE]   — latest input
    """
    lines = []

    # System prompt
    lines.append("=== SYSTEM PROMPT ===")
    lines.append(system_prompt.strip())
    lines.append("")

    # Session config
    lines.append("=== SESSION CONFIG ===")
    lines.append(json.dumps(session_config, ensure_ascii=False, indent=2))
    lines.append("")

    # Conversation history (last 10 turns to stay within token budget)
    if conversation_history:
        lines.append("=== CONVERSATION HISTORY (most recent last) ===")
        recent = conversation_history[-10:]
        for turn in recent:
            role_label = "User" if turn["role"] == "user" else "Tutor"
            lines.append(f"{role_label}: {turn['content']}")
        lines.append("")

    # Latest user message
    lines.append("=== LATEST USER MESSAGE ===")
    lines.append(user_message.strip())
    lines.append("")

    # Language enforcement — injected last so it's the freshest instruction Gemini sees
    lang = session_config.get("language_preference", "en") if session_config else "en"
    lang_instructions = {
        "hi":    "MANDATORY: Your tutor_response MUST be in Hindi or Hinglish. No full English sentences. Hinglish Roman script is fine.",
        "mixed": "MANDATORY: Your tutor_response MUST mix Hindi and English in every sentence. Do not write fully in English.",
        "en":    "Respond in English only.",
    }
    lines.append(f"=== LANGUAGE INSTRUCTION (OVERRIDE) ===")
    lines.append(lang_instructions.get(lang, "Respond in English only."))
    lines.append("")
    lines.append("Respond ONLY with a valid JSON object as specified in the system prompt.")

    return "\n".join(lines)


def call_gemini(
    system_prompt: str,
    session_config: dict,
    conversation_history: list[dict],
    user_message: str,
) -> str:
    """
    Sends the composed prompt to Gemini and returns the raw response text.
    Raises RuntimeError if the API call fails completely.
    """
    prompt = _compose_prompt(
        system_prompt, session_config, conversation_history, user_message
    )

    config = types.GenerateContentConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
    )

    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=config,
    )

    return response.text
