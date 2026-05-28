"""
phase_manager.py

ARCHITECTURE:
- Phase is 100% Gemini's decision every turn.
- Mastery is a skill level tracker only — sent to Gemini as context, never gates phase.
- This file handles: mastery updates, starting phase suggestion, fallback safety net.

Functions used in production:
  update_mastery()         — updates mastery 0-1 from signal scores each turn
  suggest_starting_phase() — suggests starting phase at session init (hint only)
  validate_phase()         — checks Gemini's phase string is valid enum
  fallback_phase_update()  — safety net when Gemini returns invalid phase string
  is_hint_seeking()        — detects hint dependency for signal context
"""

_PHASE_ORDER = ["MODEL", "COACH", "SCAFFOLD", "FADE"]

MASTERY_BOOST  = 0.04
MASTERY_MIN    = 0.0
MASTERY_MAX    = 1.0
HIGH_THRESHOLD = 65.0
LOW_THRESHOLD  = 35.0


# ── Mastery update (skill tracker only) ──────────────────────────────────────

def update_mastery(current_mastery: float, signal_scores: dict) -> float:
    """
    Updates mastery every turn from signal scores.
    Mastery tracks skill level — does NOT control phase.

    Up:   confidence >= 65 AND effort >= 65  → +0.04
          confidence >= 55 AND effort >= 55  → +0.02  (cold start fix)
    Down: frustration >= 80                  → -0.06
          frustration >= 65                  → -0.03
          confusion >= 65                    → -0.03
          confusion >= 55                    → -0.02
    """
    confidence  = signal_scores.get("confidence",  50)
    effort      = signal_scores.get("effort",      50)
    confusion   = signal_scores.get("confusion",   50)
    frustration = signal_scores.get("frustration", 50)

    delta = 0.0

    if confidence >= HIGH_THRESHOLD and effort >= HIGH_THRESHOLD:
        delta += MASTERY_BOOST
    elif confidence >= 55 and effort >= 55:
        delta += MASTERY_BOOST / 2

    if frustration >= 80:
        delta -= MASTERY_BOOST * 1.5
    elif frustration >= HIGH_THRESHOLD:
        delta -= MASTERY_BOOST * 0.75
    elif confusion >= HIGH_THRESHOLD:
        delta -= MASTERY_BOOST * 0.75
    elif confusion >= 55:
        delta -= MASTERY_BOOST / 2

    return round(max(MASTERY_MIN, min(MASTERY_MAX, current_mastery + delta)), 3)


# ── Starting phase suggestion (session init only) ─────────────────────────────

def suggest_starting_phase(mastery_level: float, icp_type: str) -> str:
    """
    Suggests a starting CA phase based on mastery + ICP.
    This is a HINT passed to Gemini at session start — not a hard rule.
    Gemini can override this from Turn 1 based on the conversation.
    """
    if icp_type == "high_wage":
        if mastery_level < 0.25: return "MODEL"
        if mastery_level < 0.50: return "COACH"
        if mastery_level < 0.75: return "SCAFFOLD"
        return "FADE"
    else:  # low_wage
        if mastery_level < 0.25: return "MODEL"
        if mastery_level < 0.50: return "COACH"
        if mastery_level < 0.75: return "SCAFFOLD"
        return "FADE"


# ── Safety net (only when Gemini returns invalid phase) ───────────────────────

def validate_phase(phase_value: str, current_phase: str) -> str:
    """Returns phase_value if valid enum, otherwise current_phase unchanged."""
    return phase_value if phase_value in _PHASE_ORDER else current_phase


def fallback_phase_update(current_phase: str, signal_scores: dict) -> str:
    """
    Safety net — ONLY called when Gemini returns an invalid phase string.
    Uses signal scores to make a simple decision.
    Not used in normal flow — Gemini's phase is trusted directly.
    """
    idx = _PHASE_ORDER.index(current_phase) if current_phase in _PHASE_ORDER else 0

    if signal_scores.get("frustration", 50) >= HIGH_THRESHOLD or \
       signal_scores.get("confusion",   50) >= HIGH_THRESHOLD:
        return _PHASE_ORDER[max(0, idx - 1)]

    if signal_scores.get("confidence", 50) >= HIGH_THRESHOLD and \
       signal_scores.get("effort",     50) >= HIGH_THRESHOLD:
        return _PHASE_ORDER[min(len(_PHASE_ORDER) - 1, idx + 1)]

    return current_phase


# ── Hint dependency helper ────────────────────────────────────────────────────

def is_hint_seeking(signal_scores: dict) -> bool:
    """
    Returns True if this turn shows hint dependency.
    answer_seeking high OR (low effort + low confidence).
    Used by signal context — NOT for phase gating.
    """
    return (
        signal_scores.get("answer_seeking", 50) >= HIGH_THRESHOLD or
        (signal_scores.get("effort", 50) <= LOW_THRESHOLD and
         signal_scores.get("confidence", 50) <= LOW_THRESHOLD)
    )
