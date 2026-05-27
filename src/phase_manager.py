"""
phase_manager.py

Responsibilities:
1. update_mastery()        — updates mastery 0.0–1.0 from signal scores each turn
                             mastery = skill tracker only, NOT a phase gate
2. suggest_starting_phase()— suggests a starting phase based on mastery + ICP
                             this is a HINT to Gemini, not a hard assignment
3. fallback_phase_update() — safety net when Gemini returns invalid phase value
4. validate_phase()        — checks phase string is a valid enum

IMPORTANT DESIGN CHANGE:
Phase is now 100% Gemini's decision every turn.
Mastery is purely a skill level tracker — it goes up/down based on signals
but NEVER gates or blocks phase changes.
Gemini reads mastery as context and decides phase freely.
"""

_PHASE_ORDER = ["MODEL", "COACH", "SCAFFOLD", "FADE"]

# ── Mastery update constants ──────────────────────────────────────────────────
MASTERY_BOOST  = 0.04
MASTERY_MIN    = 0.0
MASTERY_MAX    = 1.0
HIGH_THRESHOLD = 65.0
LOW_THRESHOLD  = 35.0


def update_mastery(current_mastery: float, signal_scores: dict) -> float:
    """
    Updates mastery every turn from signal scores.
    Mastery = skill level tracker. Not used to gate phase.

    Up:
      confidence >= 65 AND effort >= 65  → +0.04  (learner understands and is trying)
      confidence >= 55 AND effort >= 55  → +0.02  (Turn 1 cold start fix)

    Down:
      frustration >= 80                  → -0.06  (dominant frustration)
      frustration >= 65                  → -0.03  (clear frustration)
      confusion >= 65                    → -0.03  (clear confusion)
      confusion >= 55                    → -0.02  (mild confusion)
    """
    confidence  = signal_scores.get("confidence",  50)
    effort      = signal_scores.get("effort",      50)
    confusion   = signal_scores.get("confusion",   50)
    frustration = signal_scores.get("frustration", 50)

    delta = 0.0

    if confidence >= HIGH_THRESHOLD and effort >= HIGH_THRESHOLD:
        delta += MASTERY_BOOST          # +0.04
    elif confidence >= 55 and effort >= 55:
        delta += MASTERY_BOOST / 2      # +0.02

    if frustration >= 80:
        delta -= MASTERY_BOOST * 1.5    # -0.06
    elif frustration >= HIGH_THRESHOLD:
        delta -= MASTERY_BOOST * 0.75   # -0.03
    elif confusion >= HIGH_THRESHOLD:
        delta -= MASTERY_BOOST * 0.75   # -0.03
    elif confusion >= 55:
        delta -= MASTERY_BOOST / 2      # -0.02

    return round(max(MASTERY_MIN, min(MASTERY_MAX, current_mastery + delta)), 3)


def suggest_starting_phase(mastery_level: float, icp_type: str) -> str:
    """
    Suggests a starting CA phase based on mastery + ICP.
    This is passed to Gemini as a recommendation — not a hard rule.
    Gemini may override this from the first turn based on the conversation.

    high_wage: advances earlier (less support expected)
    low_wage:  advances later (more support needed)
    """
    if icp_type == "high_wage":
        if mastery_level < 0.25: return "MODEL"
        if mastery_level < 0.50: return "COACH"
        if mastery_level < 0.75: return "SCAFFOLD"
        return "FADE"
    else:  # low_wage
        if mastery_level < 0.40: return "MODEL"
        if mastery_level < 0.65: return "COACH"
        if mastery_level < 0.85: return "SCAFFOLD"
        return "FADE"


def fallback_phase_update(current_phase: str, signal_scores: dict) -> str:
    """
    Safety net — only called when Gemini returns an invalid phase string.
    Uses signal scores to make a simple decision.
    """
    idx = _PHASE_ORDER.index(current_phase) if current_phase in _PHASE_ORDER else 0

    if signal_scores.get("frustration", 50) >= HIGH_THRESHOLD or \
       signal_scores.get("confusion",   50) >= HIGH_THRESHOLD:
        return _PHASE_ORDER[max(0, idx - 1)]

    if signal_scores.get("confidence", 50) >= HIGH_THRESHOLD and \
       signal_scores.get("effort",     50) >= HIGH_THRESHOLD:
        return _PHASE_ORDER[min(len(_PHASE_ORDER) - 1, idx + 1)]

    return current_phase


def validate_phase(phase_value: str, current_phase: str) -> str:
    return phase_value if phase_value in _PHASE_ORDER else current_phase
