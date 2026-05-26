"""
signal_extractor.py — Two-layer signal detection.

Layer 1 (regex): Fast local detection for obvious patterns.
                 Gives a base score per signal.

Layer 2 (LLM judge): Gemini evaluates the message in context
                     and returns refined signal scores 0-100.
                     Overrides regex when available.

SignalScorecard maintains rolling 0-100 scores across turns.
"""

import re
import json
from google import genai
from google.genai import types

# ── Score constants ───────────────────────────────────────────────────────────
NEUTRAL      = 50.0
BOOST_STRONG = 18.0
BOOST_WEAK   =  8.0
DECAY        =  5.0
CLAMP_MIN    =  0.0
CLAMP_MAX    = 100.0

SIGNAL_KEYS = [
    "confusion", "frustration", "confidence",
    "effort", "answer_seeking", "off_topic",
]

# ── Regex patterns (Layer 1) ──────────────────────────────────────────────────

_CONFUSION_STRONG = [
    r"\bdon'?t understand\b", r"\bconfused\b", r"\bnot clear\b", r"\bi have no idea\b",
    r"\bsamajh\s+nah?i\b", r"\bsamajh\s+nhi\b", r"\bsamajh\s+nahi\s+aa\b",
    r"\bsamajh\s+nhi\s+aa\b", r"\bkuch\s+samajh\s+nahi\b", r"\bkuch\s+samajh\s+nhi\b",
    r"\bnahi\s+samjha\b", r"\bnhi\s+samjha\b", r"\bmujhe\s+samajh\b", r"\bmujhe\s+samjh\b",
]
_CONFUSION_WEAK = [
    r"\bwhat is\b", r"\bwhat are\b", r"\bwhat does\b", r"\bhuh\b",
    r"\bkya hai\b", r"\bkya hota hai\b", r"\bkya hote hai\b", r"\bkya matlab\b",
    r"\bkaise\b", r"\bsmajh\b",
]

_FRUSTRATION_STRONG = [
    r"\bi give up\b", r"\bi hate this\b", r"\bthis is impossible\b", r"\bI can'?t do this\b",
    r"\bnahi\s+ho\s+raha\b", r"\bnhi\s+ho\s+raha\b", r"\bnahi\s+ho\s+rha\b", r"\bnhi\s+ho\s+rha\b",
    r"\bbahut\s+mushkil\b", r"\bbohat\s+hard\b",
]
_FRUSTRATION_WEAK = [
    r"\bfrustrat\b", r"\bstuck\b", r"\bthis is hard\b", r"\bugh\b",
    r"\bso difficult\b", r"\bboring\b", r"\byaar\b", r"\byar\b", r"\bmushkil\b", r"\bpareshaan\b",
]

_ANSWER_SEEKING_STRONG = [
    r"\bjust tell me\b", r"\bgive me the answer\b", r"\bdirect answer\b", r"\btell me directly\b",
    r"\bbata\s*do\b", r"\bans\s*do\b", r"\bseedha\s+bata\b", r"\bdirect\s+bata\b",
]
_ANSWER_SEEKING_WEAK = [
    r"\bwhat is the answer\b", r"\bsimply tell\b", r"\bshortcut\b",
    r"\bbas\s+bata\b", r"\bsimply\s+bata\b",
]

_CONFIDENCE_STRONG = [
    r"\bi got it\b", r"\bi understand now\b", r"\bi know this\b", r"\bi understand\b",
    r"\bsamajh\s+gaya\b", r"\bsamajh\s+gya\b", r"\bsamajh\s+aa\s+gaya\b",
    r"\bsamajh\s+aa\s+gya\b", r"\bsamajh\s+gyi\b", r"\bab\s+samajh\b",
    r"\bclear\s+hai\b", r"\bclear\s+ho\s+gaya\b", r"\bclear\s+ho\s+gya\b",
    r"\bmain\s+samajh\b", r"\bmujhe\s+samajh\s+aa\b", r"\bsmajh\s+gya\b",
    r"\bgot it\b", r"\bI see\b", r"\bachha\b", r"\btheek hai\b", r"\bok understood\b",
]
_CONFIDENCE_WEAK = [
    r"\bi think\b", r"\bi believe\b", r"\bmaybe\b", r"\bprobably\b",
    r"\bmujhe\s+lagta\b", r"\blgta\b", r"\bshayad\b", r"\blag\s+raha\b",
    r"\bI think so\b", r"\bperhaps\b",
]

_EFFORT_STRONG = [
    r"\bmy attempt\b", r"\bhere is my\b", r"\bmera\s+attempt\b", r"\bi wrote\b",
    r"\bhere'?s my code\b", r"def \w+\(", r"\blet me try\b", r"\bi tried this\b",
    r"\bmaine\s+try\b", r"\bmene\s+try\b", r"\bmaine\s+likha\b", r"\bmene\s+likha\b",
    r"\bye\s+try\b", r"\byeh\s+try\b", r"\bmera\s+code\b", r"\bkiya\s+mene\b",
    r"\bkiya\s+maine\b", r"\btry\s+kiya\b", r"\btry\s+karunga\b", r"\bkarunga\b",
    r"\bkarne\s+ki\b", r"\bkarta\s+hoon\b",
]
_EFFORT_WEAK = [
    r"\bi tried\b", r"\bi attempted\b", r"\blet me attempt\b",
    r"\bmy code\b", r"\bthis code\b", r"\bthis function\b", r"\bkoshish\b",
    r"\btry\s+kar\b",
]


def _score_signal(text, strong, weak):
    lo = text.lower()
    if any(re.search(p, lo) for p in strong): return BOOST_STRONG
    if any(re.search(p, lo) for p in weak):   return BOOST_WEAK
    return 0.0


def _decay(score):
    if score > NEUTRAL: return max(NEUTRAL, score - DECAY)
    if score < NEUTRAL: return min(NEUTRAL, score + DECAY)
    return score


def _clamp(v): return max(CLAMP_MIN, min(CLAMP_MAX, v))


def regex_detect(user_message: str, skill_topic: str) -> dict:
    """Layer 1 — fast regex detection. Returns boost amounts per signal."""
    topic_words = skill_topic.lower().split()
    msg_lower   = user_message.lower()
    topic_hit   = any(w in msg_lower for w in topic_words if len(w) > 3)

    return {
        "confusion":     _score_signal(user_message, _CONFUSION_STRONG,     _CONFUSION_WEAK),
        "frustration":   _score_signal(user_message, _FRUSTRATION_STRONG,   _FRUSTRATION_WEAK),
        "answer_seeking":_score_signal(user_message, _ANSWER_SEEKING_STRONG, _ANSWER_SEEKING_WEAK),
        "confidence":    _score_signal(user_message, _CONFIDENCE_STRONG,     _CONFIDENCE_WEAK),
        "effort":        _score_signal(user_message, _EFFORT_STRONG,         _EFFORT_WEAK),
        "off_topic":     0.0 if topic_hit else (BOOST_WEAK if len(user_message.split()) > 5 else 0.0),
    }


# ── LLM Judge (Layer 2) ───────────────────────────────────────────────────────

_judge_client = None

def _get_judge_client(api_key: str):
    global _judge_client
    if _judge_client is None:
        _judge_client = genai.Client(api_key=api_key)
    return _judge_client


LLM_JUDGE_PROMPT = """You are a signal detection engine for an AI tutoring system.
Analyse the learner message below and rate each signal 0-100.

SIGNAL DEFINITIONS:
- confusion (0=crystal clear, 100=completely lost)
- frustration (0=calm, 100=extremely frustrated/giving up)
- confidence (0=no confidence, 100=very confident they understand)
- effort (0=no attempt made, 100=wrote code/made full attempt)
- answer_seeking (0=not asking for answer, 100=demanding direct answer)
- off_topic (0=fully on topic, 100=completely off topic)

SCORE GUIDE:
- 80-100: signal strongly present
- 65-79:  signal clearly present
- 50-64:  signal slightly present or neutral
- 35-49:  signal slightly absent
- 0-34:   signal clearly absent

SKILL TOPIC: {skill_topic}
LEARNER MESSAGE: "{message}"
CONVERSATION CONTEXT (last 2 turns): {context}

Return ONLY this JSON, no explanation:
{{"confusion": 0-100, "frustration": 0-100, "confidence": 0-100, "effort": 0-100, "answer_seeking": 0-100, "off_topic": 0-100}}"""


def llm_judge_signals(
    user_message: str,
    skill_topic: str,
    conversation_history: list,
    api_key: str,
    model: str,
) -> dict | None:
    """
    Layer 2 — Gemini judges signal scores from the message in context.
    Returns dict of signal scores or None if call fails.
    """
    try:
        client = _get_judge_client(api_key)

        # Build brief conversation context
        recent = conversation_history[-4:] if conversation_history else []
        context_str = ""
        for turn in recent:
            role = "Learner" if turn["role"] == "user" else "Tutor"
            context_str += f"{role}: {turn['content'][:80]}\n"
        if not context_str:
            context_str = "No prior conversation."

        prompt = LLM_JUDGE_PROMPT.format(
            skill_topic=skill_topic,
            message=user_message,
            context=context_str.strip(),
        )

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,       # very low — we want consistent scores
                max_output_tokens=100,
            ),
        )

        raw = response.text.strip()
        # Strip markdown fences if present
        raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        scores = json.loads(raw)

        # Validate all keys present and in range
        for key in SIGNAL_KEYS:
            if key not in scores:
                return None
            scores[key] = float(max(0, min(100, scores[key])))

        return scores

    except Exception:
        return None  # fall back to regex silently


# ── SignalScorecard ───────────────────────────────────────────────────────────

class SignalScorecard:
    """
    Persistent signal state across all turns.
    Uses LLM judge (Layer 2) when available, falls back to regex (Layer 1).
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.scores: dict[str, float] = {k: NEUTRAL for k in SIGNAL_KEYS}
        self.history: list[dict]      = []
        self.api_key  = api_key
        self.model    = model
        self.judge_success_count = 0
        self.judge_fallback_count = 0

    def update(
        self,
        user_message: str,
        skill_topic: str,
        conversation_history: list = None,
    ) -> dict[str, float]:
        """
        Updates signal scores using LLM judge if available,
        otherwise falls back to regex detection.
        """
        conversation_history = conversation_history or []
        llm_scores = None

        # Layer 2 — try LLM judge first
        if self.api_key and self.model:
            llm_scores = llm_judge_signals(
                user_message, skill_topic,
                conversation_history,
                self.api_key, self.model,
            )

        if llm_scores:
            # LLM judge succeeded — use its scores directly
            # Apply them as absolute values, not boosts
            self.judge_success_count += 1
            for key in SIGNAL_KEYS:
                judge_score = llm_scores[key]
                current     = self.scores[key]
                # Blend: 70% judge, 30% current (smooth transition)
                self.scores[key] = _clamp(0.7 * judge_score + 0.3 * current)
        else:
            # Layer 1 — regex fallback
            self.judge_fallback_count += 1
            boosts = regex_detect(user_message, skill_topic)
            for key in SIGNAL_KEYS:
                if boosts[key] > 0:
                    self.scores[key] = _clamp(self.scores[key] + boosts[key])
                else:
                    self.scores[key] = _decay(self.scores[key])

        snapshot = {k: round(v, 1) for k, v in self.scores.items()}
        self.history.append(snapshot)
        return snapshot

    def is_high(self, signal: str, threshold: float = 65.0) -> bool:
        return self.scores.get(signal, NEUTRAL) >= threshold

    def is_low(self, signal: str, threshold: float = 35.0) -> bool:
        return self.scores.get(signal, NEUTRAL) <= threshold

    def to_dict(self) -> dict:
        return {k: round(v, 1) for k, v in self.scores.items()}

    def stats(self) -> str:
        total = self.judge_success_count + self.judge_fallback_count
        if total == 0: return "no turns yet"
        pct = int(100 * self.judge_success_count / total)
        return f"LLM judge: {self.judge_success_count}/{total} turns ({pct}%)"
