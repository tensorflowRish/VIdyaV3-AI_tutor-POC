"""
schemas.py — Pydantic models for session config and tutor output validation.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ── Session Configuration ─────────────────────────────────────────────────────

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


# ── Signal Scores (now part of TutorOutput) ───────────────────────────────────

class SignalScoresOutput(BaseModel):
    """
    Signal scores returned by Gemini inside the tutor response JSON.
    Each score 0–100. 50 = neutral baseline.
    Replaces the separate LLM judge API call.
    """
    confusion:     float = Field(default=50.0, ge=0, le=100)
    frustration:   float = Field(default=50.0, ge=0, le=100)
    confidence:    float = Field(default=50.0, ge=0, le=100)
    effort:        float = Field(default=50.0, ge=0, le=100)
    answer_seeking:float = Field(default=50.0, ge=0, le=100)
    off_topic:     float = Field(default=50.0, ge=0, le=100)

    def to_dict(self) -> dict:
        return {
            "confusion":      round(self.confusion, 1),
            "frustration":    round(self.frustration, 1),
            "confidence":     round(self.confidence, 1),
            "effort":         round(self.effort, 1),
            "answer_seeking": round(self.answer_seeking, 1),
            "off_topic":      round(self.off_topic, 1),
        }


# ── Official Tutor Output ─────────────────────────────────────────────────────

class TutorOutput(BaseModel):
    tutor_response:       str = Field(..., min_length=1)
    updated_ca_phase:     Literal["MODEL", "COACH", "SCAFFOLD", "FADE"]
    on_topic_flag:        bool
    suggested_next_action:str = Field(..., min_length=1)
    signal_scores:        Optional[SignalScoresOutput] = None   # Gemini provides this


# ── Fallback output ───────────────────────────────────────────────────────────

def fallback_output(current_phase: str) -> dict:
    return {
        "tutor_response": (
            "I had a small hiccup processing that. "
            "Could you rephrase your question? I'm here to help!"
        ),
        "updated_ca_phase":     current_phase,
        "on_topic_flag":        True,
        "suggested_next_action":"Please try rephrasing your message.",
        "signal_scores":        None,
    }
