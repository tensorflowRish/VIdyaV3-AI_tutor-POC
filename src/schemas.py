"""
schemas.py — Pydantic models for session config and tutor output validation.
"""

from typing import Literal
from pydantic import BaseModel, Field, field_validator


# ── Session Configuration (set once at startup) ──────────────────────────────

class SessionConfig(BaseModel):
    skill_topic: str = Field(..., min_length=1)
    mastery_level: float = Field(..., ge=0.0, le=1.0)
    icp_type: Literal["low_wage", "high_wage"]
    ca_phase: Literal["MODEL", "COACH", "SCAFFOLD", "FADE"]
    language_preference: Literal["en", "hi", "mixed"]

    @field_validator("skill_topic")
    @classmethod
    def topic_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("skill_topic cannot be blank")
        return v.strip()


# ── Official Tutor Output (Gemini must return this) ──────────────────────────

class TutorOutput(BaseModel):
    tutor_response: str = Field(..., min_length=1)
    updated_ca_phase: Literal["MODEL", "COACH", "SCAFFOLD", "FADE"]
    on_topic_flag: bool
    suggested_next_action: str = Field(..., min_length=1)


# ── Fallback output when Gemini returns invalid JSON ─────────────────────────

def fallback_output(current_phase: str) -> dict:
    return {
        "tutor_response": (
            "I had a small hiccup processing that. "
            "Could you rephrase your question? I'm here to help!"
        ),
        "updated_ca_phase": current_phase,
        "on_topic_flag": True,
        "suggested_next_action": "Please try rephrasing your message.",
    }
