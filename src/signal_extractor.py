"""
signal_extractor.py — SignalScorecard with rolling 0-100 scores.

Signal scores now come from Gemini's response JSON (signal_scores field).
Gemini evaluates the message in full context and returns scores directly.
No separate LLM judge call needed — one API call does everything.

Fallback: if Gemini doesn't return signal_scores, regex detection is used.

Rolling blend formula:
    new_score = 0.7 * gemini_score + 0.3 * current_score
This smooths out turn-by-turn variation while reacting quickly to changes.
"""

import re
import json
from typing import Optional

# ── Constants ─────────────────────────────────────────────────────────────────
NEUTRAL      = 50.0
BOOST_STRONG = 18.0
BOOST_WEAK   =  8.0
DECAY        =  5.0
CLAMP_MIN    =  0.0
CLAMP_MAX    = 100.0
BLEND_LLM    =  0.7   # weight for Gemini score
BLEND_ROLL   =  0.3   # weight for rolling current score

SIGNAL_KEYS = [
    "confusion", "frustration", "confidence",
    "effort", "answer_seeking", "off_topic",
]


# ── Regex fallback patterns ───────────────────────────────────────────────────

_CONFUSION_STRONG = [
    r"\bdon'?t understand\b", r"\bconfused\b", r"\bnot clear\b",
    r"\bsamajh\s+nah?i\b", r"\bsamajh\s+nhi\b", r"\bsamajh\s+nahi\s+aa\b",
    r"\bsamajh\s+nhi\s+aa\b", r"\bkuch\s+samajh\s+nahi\b", r"\bkuch\s+samajh\s+nhi\b",
    r"\bnahi\s+samjha\b", r"\bnhi\s+samjha\b", r"\bmujhe\s+samajh\b",
]
_CONFUSION_WEAK = [
    r"\bwhat is\b", r"\bwhat are\b", r"\bwhat does\b", r"\bhuh\b",
    r"\bkya hai\b", r"\bkya hota hai\b", r"\bkya hote hai\b", r"\bkya matlab\b",
    r"\bkaise\b",
]
_FRUSTRATION_STRONG = [
    r"\bi give up\b", r"\bi hate this\b", r"\bthis is impossible\b",
    r"\bnahi\s+ho\s+raha\b", r"\bnhi\s+ho\s+rha\b", r"\bbahut\s+mushkil\b",
]
_FRUSTRATION_WEAK = [
    r"\bfrustrat\b", r"\bstuck\b", r"\bthis is hard\b", r"\bugh\b",
    r"\byaar\b", r"\bmushkil\b", r"\bpareshaan\b",
]
_ANSWER_SEEKING_STRONG = [
    r"\bjust tell me\b", r"\bgive me the answer\b", r"\bdirect answer\b",
    r"\bbata\s*do\b", r"\bseedha\s+bata\b",
]
_ANSWER_SEEKING_WEAK = [
    r"\bwhat is the answer\b", r"\bsimply tell\b", r"\bshortcut\b",
]
_CONFIDENCE_STRONG = [
    r"\bi got it\b", r"\bi understand now\b", r"\bi understand\b",
    r"\bsamajh\s+gaya\b", r"\bsamajh\s+gya\b", r"\bclear\s+hai\b",
    r"\bmain\s+samajh\b", r"\bgot it\b", r"\bachha\b", r"\bok understood\b",
]
_CONFIDENCE_WEAK = [
    r"\bi think\b", r"\bi believe\b", r"\bmaybe\b", r"\bprobably\b",
    r"\bmujhe\s+lagta\b", r"\bshayad\b",
]
_EFFORT_STRONG = [
    r"\bmy attempt\b", r"\bhere is my\b", r"\bi wrote\b",
    r"def \w+\(", r"\blet me try\b", r"\btry\s+kiya\b",
    r"\bmene\s+try\b", r"\bmaine\s+try\b", r"\bkiya\s+mene\b",
]
_EFFORT_WEAK = [
    r"\bi tried\b", r"\bi attempted\b", r"\bkoshish\b", r"\btry\s+kar\b",
]


def _detect(text: str, strong: list, weak: list) -> float:
    lo = text.lower()
    if any(re.search(p, lo) for p in strong): return BOOST_STRONG
    if any(re.search(p, lo) for p in weak):   return BOOST_WEAK
    return 0.0


def _regex_scores(user_message: str, skill_topic: str) -> dict:
    """Regex fallback — returns boost amounts per signal."""
    topic_words = skill_topic.lower().split()
    msg_lower   = user_message.lower()
    topic_hit   = any(w in msg_lower for w in topic_words if len(w) > 3)

    return {
        "confusion":     _detect(user_message, _CONFUSION_STRONG,     _CONFUSION_WEAK),
        "frustration":   _detect(user_message, _FRUSTRATION_STRONG,   _FRUSTRATION_WEAK),
        "answer_seeking":_detect(user_message, _ANSWER_SEEKING_STRONG, _ANSWER_SEEKING_WEAK),
        "confidence":    _detect(user_message, _CONFIDENCE_STRONG,     _CONFIDENCE_WEAK),
        "effort":        _detect(user_message, _EFFORT_STRONG,         _EFFORT_WEAK),
        "off_topic":     0.0 if topic_hit else (BOOST_WEAK if len(user_message.split()) > 5 else 0.0),
    }


def _clamp(v: float) -> float:
    return max(CLAMP_MIN, min(CLAMP_MAX, v))


def _decay_toward_neutral(score: float) -> float:
    if score > NEUTRAL: return max(NEUTRAL, score - DECAY)
    if score < NEUTRAL: return min(NEUTRAL, score + DECAY)
    return score


# ── SignalScorecard ───────────────────────────────────────────────────────────

class SignalScorecard:
    """
    Maintains rolling 0-100 signal scores across turns.

    Primary source: Gemini's signal_scores from response JSON.
    Fallback source: regex detection (if Gemini doesn't return signal_scores).

    Rolling blend: new = 0.7 * gemini_score + 0.3 * current
    This smooths variation while reacting quickly to real changes.
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.scores: dict[str, float] = {k: NEUTRAL for k in SIGNAL_KEYS}
        self.history: list[dict]      = []
        # api_key/model kept for interface compatibility but not used
        # (LLM judge replaced by Gemini's own signal_scores in response)
        self.gemini_scores_count  = 0
        self.regex_fallback_count = 0

    def update_from_gemini(
        self,
        gemini_signal_scores: Optional[dict],
        user_message: str,
        skill_topic: str,
    ) -> dict[str, float]:
        """
        Updates scores using Gemini's signal_scores if available,
        otherwise falls back to regex.

        Called by tutor_session after parsing Gemini's response.
        """
        if gemini_signal_scores and all(k in gemini_signal_scores for k in SIGNAL_KEYS):
            # Primary path — blend Gemini's scores with rolling history
            self.gemini_scores_count += 1
            for key in SIGNAL_KEYS:
                gemini_val = float(max(0, min(100, gemini_signal_scores.get(key, NEUTRAL))))
                # 70% Gemini score + 30% rolling current score
                self.scores[key] = _clamp(
                    BLEND_LLM * gemini_val + BLEND_ROLL * self.scores[key]
                )
        else:
            # Fallback path — regex detection
            self.regex_fallback_count += 1
            boosts = _regex_scores(user_message, skill_topic)
            for key in SIGNAL_KEYS:
                if boosts[key] > 0:
                    self.scores[key] = _clamp(self.scores[key] + boosts[key])
                else:
                    self.scores[key] = _decay_toward_neutral(self.scores[key])

        snapshot = {k: round(v, 1) for k, v in self.scores.items()}
        self.history.append(snapshot)
        return snapshot

    # Keep old update() for backward compat (benchmark runner uses it)
    def update(
        self,
        user_message: str,
        skill_topic: str,
        conversation_history: list = None,
    ) -> dict[str, float]:
        """Backward-compatible method — uses regex only."""
        return self.update_from_gemini(None, user_message, skill_topic)

    def is_high(self, signal: str, threshold: float = 65.0) -> bool:
        return self.scores.get(signal, NEUTRAL) >= threshold

    def is_low(self, signal: str, threshold: float = 35.0) -> bool:
        return self.scores.get(signal, NEUTRAL) <= threshold

    def to_dict(self) -> dict:
        return {k: round(v, 1) for k, v in self.scores.items()}

    def stats(self) -> str:
        total = self.gemini_scores_count + self.regex_fallback_count
        if total == 0: return "no turns yet"
        pct = int(100 * self.gemini_scores_count / total)
        return f"Gemini signals: {self.gemini_scores_count}/{total} turns ({pct}%)"
