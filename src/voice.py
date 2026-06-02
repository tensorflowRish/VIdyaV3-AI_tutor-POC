"""
voice.py — Server-side speech I/O for the Streamlit UI.

STT: Gemini multimodal (audio bytes → transcript).
TTS: gTTS (text → MP3 on the server). No browser SpeechRecognition / speechSynthesis.
"""

from __future__ import annotations

import io
import logging

from google import genai
from google.genai import types
from gtts import gTTS

from src.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=GEMINI_API_KEY)

# gTTS language codes (single language per clip; best-effort for mixed)
_GTTS_LANG = {"en": "en", "hi": "hi", "mixed": "hi"}

_TRANSCRIBE_HINT = {
    "en": "English",
    "hi": "Hindi",
    "mixed": "Hindi and English (Hinglish)",
}


def transcribe_audio(
    audio_bytes: bytes,
    mime_type: str = "audio/wav",
    language_preference: str = "en",
) -> str:
    """Return spoken text from raw audio using Gemini."""
    if not audio_bytes:
        return ""

    lang_hint = _TRANSCRIBE_HINT.get(language_preference, "English")
    prompt = (
        f"Transcribe the following audio exactly as spoken. "
        f"The speaker is expected to use {lang_hint}. "
        "Return ONLY the transcript text with no quotes, labels, or commentary."
    )

    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type or "audio/wav"),
            prompt,
        ],
    )
    return (response.text or "").strip()


def synthesize_speech(text: str, language_preference: str = "en") -> bytes:
    """Return MP3 bytes for the given text (Google TTS via gTTS, server-side)."""
    cleaned = (text or "").strip()
    if not cleaned:
        return b""

    lang = _GTTS_LANG.get(language_preference, "en")
    # gTTS URL length limit — tutor replies are short; cap defensively
    clip = cleaned[:4500]
    buf = io.BytesIO()
    gTTS(text=clip, lang=lang).write_to_fp(buf)
    return buf.getvalue()
