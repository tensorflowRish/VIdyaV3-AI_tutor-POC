"""
phase_manager.py — Phase assignment and fallback logic.

Two responsibilities:
1. mastery_to_phase()       — assigns initial CA phase from mastery_level + ICP
2. update_mastery()         — updates mastery_level each turn from signal scores
3. fallback_phase_update()  — safety net when Gemini returns invalid phase
4. validate_phase()         — checks phase string is a valid enum value
"""

from src.icp_profiles import mastery_to_phase   # re-exported for convenience

_PHASE_ORDER = ["MODEL", "COACH", "SCAFFOLD", "FADE"]

# ── Mastery update constants ──────────────────────────────────────────────────
MASTERY_BOOST  = 0.04   # confidence + effort → mastery goes up
MASTERY_DROP   = 0.02   # confusion or frustration → mastery goes down
MASTERY_MIN    = 0.0
MASTERY_MAX    = 1.0

# Signal score thresholds (0–100 scale from SignalScorecard)
HIGH_THRESHOLD = 65.0
LOW_THRESHOLD  = 35.0


def update_mastery(
    current_mastery: float,
    signal_scores: dict[str, float],
) -> float:
    """
    Updates mastery_level every turn based on current signal scores.

    Rules:
    - confidence AND effort both high (>= 65) → mastery +0.04
    - confidence AND effort both moderate (>= 55) → mastery +0.02
      (catches Turn 1 where scores haven't built up yet but intent is clear)
    - confusion OR frustration high (>= 65) → mastery -0.02
    - otherwise → mastery unchanged
    Returns new mastery_level clamped to [0.0, 1.0].
    """
    confidence  = signal_scores.get("confidence", 50)
    effort      = signal_scores.get("effort",     50)
    confusion   = signal_scores.get("confusion",  50)
    frustration = signal_scores.get("frustration",50)

    delta = 0.0

    if confidence >= HIGH_THRESHOLD and effort >= HIGH_THRESHOLD:
        # Both clearly active → full boost
        delta = +MASTERY_BOOST
    elif confidence >= 55 and effort >= 55:
        # Both moderate — user is trying and somewhat confident
        # (common on Turn 1 before scores accumulate)
        delta = +MASTERY_BOOST / 2   # +0.02

    if confusion >= HIGH_THRESHOLD or frustration >= HIGH_THRESHOLD:
        delta -= MASTERY_DROP

    new_mastery = current_mastery + delta
    return round(max(MASTERY_MIN, min(MASTERY_MAX, new_mastery)), 3)


def phase_from_mastery(mastery_level: float, icp_type: str) -> str:
    """Wrapper around icp_profiles.mastery_to_phase for convenience."""
    return mastery_to_phase(mastery_level, icp_type)


def fallback_phase_update(
    current_phase: str,
    signal_scores: dict[str, float],
) -> str:
    """
    Fallback CA phase decision using signal scores.
    Only called when Gemini returns an invalid phase value.
    """
    idx = _PHASE_ORDER.index(current_phase) if current_phase in _PHASE_ORDER else 0

    confusion_high   = signal_scores.get("confusion",   50) >= HIGH_THRESHOLD
    frustration_high = signal_scores.get("frustration", 50) >= HIGH_THRESHOLD
    confidence_high  = signal_scores.get("confidence",  50) >= HIGH_THRESHOLD
    effort_high      = signal_scores.get("effort",      50) >= HIGH_THRESHOLD

    if frustration_high or confusion_high:
        new_idx = max(0, idx - 1)
    elif confidence_high and effort_high:
        new_idx = min(len(_PHASE_ORDER) - 1, idx + 1)
    else:
        new_idx = idx

    return _PHASE_ORDER[new_idx]


def validate_phase(phase_value: str, current_phase: str) -> str:
    """Returns phase_value if valid, otherwise current_phase."""
    return phase_value if phase_value in _PHASE_ORDER else current_phase
