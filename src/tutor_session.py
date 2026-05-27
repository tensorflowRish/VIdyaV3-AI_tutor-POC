"""
tutor_session.py — Manages one full tutor session end-to-end.

What's new vs v1:
- SignalScorecard: persistent 0-100 scores per signal, updated every turn
- mastery_level updates dynamically from signal scores each turn
- ca_phase re-evaluated from mastery after each mastery update
- ICP profile (low_wage / high_wage) injected into every Gemini call
- Full scorecard history saved in logs/conversations.json
"""

import json
import re

from src.config import SYSTEM_PROMPT_PATH, CONVERSATION_LOG_PATH
import src.config as config_module
from src.schemas import SessionConfig, TutorOutput, fallback_output
from src.gemini_client import call_gemini, GeminiUnavailableError
from src.phase_manager import (
    validate_phase,
    fallback_phase_update,
    update_mastery,
    suggest_starting_phase,
)
from src.signal_extractor import SignalScorecard
from src.icp_profiles import get_icp
from src.utils import print_warning


# ── Score label helper (used in learner_state sent to Gemini) ────────────────

def _score_label(score: float) -> str:
    """Converts a 0–100 signal score to a plain-English label for Gemini."""
    if score >= 80:  return f"very high ({score:.0f})"
    if score >= 65:  return f"high ({score:.0f})"
    if score >= 35:  return f"neutral ({score:.0f})"
    if score >= 20:  return f"low ({score:.0f})"
    return f"very low ({score:.0f})"


# ── Load system prompt once ───────────────────────────────────────────────────

def _load_system_prompt() -> str:
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()

_SYSTEM_PROMPT = _load_system_prompt()


# ── JSON extraction helper ────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    return json.loads(cleaned)


# ── Main session class ────────────────────────────────────────────────────────

class TutorSession:
    def __init__(self, config: SessionConfig):
        self.config          = config
        self.mastery_level   = config.mastery_level          # live, updates each turn
        self.current_phase   = config.ca_phase               # suggested from mastery, Gemini may change from Turn 1
        self.conversation_history: list[dict] = []
        self.turn_count      = 0
        self.scorecard       = SignalScorecard(               # persistent signal scores
            api_key=config_module.GEMINI_API_KEY,
            model=config_module.GEMINI_MODEL,
        )
        self.icp_profile     = get_icp(config.icp_type)      # tone + example rules

    # ── Session config dict sent to Gemini every turn ────────────────────────

    def _session_config_dict(self, signal_scores: dict) -> dict:
        """
        Packages full session state + signal scores + ICP tone rules.
        Everything Gemini needs to give a perfectly adapted response.
        """
        ast = self.icp_profile.get("anti_stereotype_threat")
        return {
            "skill_topic":         self.config.skill_topic,
            "mastery_level":       round(self.mastery_level, 3),
            "ca_phase":            self.current_phase,
            "language_preference": self.config.language_preference,

            # ── Full ICP context (who this learner is + how to teach them) ────
            "icp": {
                "type":                   self.config.icp_type,
                "tone":                   self.icp_profile["tone"],
                "tone_rules":             self.icp_profile["tone_rules"],
                "scaffold_level":         self.icp_profile["scaffold_level"],
                "worked_examples":        self.icp_profile["worked_examples"],
                "language_default":       self.icp_profile["language_default"],
                "explanation_depth":      self.icp_profile["explanation_depth"],
                "challenge_level":        self.icp_profile["challenge_level"],
                "goal_framing":           self.icp_profile["goal_framing"],
                "pacing":                 self.icp_profile["pacing"],
                "encouragement":          self.icp_profile["encouragement"],
                "anti_stereotype_threat": ast if ast else "not applicable",
                "learner_goals":          self.icp_profile["goals"],
            },

            # ── Signal scores (0–100 each, rolling across turns) ──────────────
            "signal_scores": {
                k: round(v, 1) for k, v in signal_scores.items()
            },

            # ── Plain-English labels for Gemini ───────────────────────────────
            "learner_state": {
                k: _score_label(v)
                for k, v in signal_scores.items()
            },
        }

    # ── JSON parse + validate with one retry ─────────────────────────────────

    def _friendly_error_response(self, error: "GeminiUnavailableError") -> dict:
        """
        Returns a warm, user-friendly response when Gemini is unavailable.
        Never exposes raw API errors to the user.
        """
        lang = self.config.language_preference
        icp  = self.config.icp_type

        if error.reason == "rate_limit":
            wait = error.retry_after
            if lang == "hi":
                msg = (f"Thoda sa wait karo — main abhi bahut busy hoon! "
                       f"Approximately {wait} seconds mein try karo. "
                       f"Tab tak apne notes review karo. 😊")
            elif lang == "mixed":
                msg = (f"Ek second — I'm a bit overwhelmed right now! "
                       f"Please try again in about {wait} seconds. "
                       f"Tab tak jo seekha hai usse revise karo. 😊")
            else:
                if icp == "high_wage":
                    msg = (f"I'm hitting my rate limit — please retry in ~{wait} seconds. "
                           f"Use the time to review what we covered.")
                else:
                    msg = (f"I need a quick breather! Please try again in about {wait} seconds. "
                           f"You're doing great — don't stop now! 😊")

        elif error.reason == "server_error":
            if lang in ["hi", "mixed"]:
                msg = "Kuch technical issue aa gaya hai — thodi der baad try karo. Main yahan hoon! 🙏"
            else:
                msg = "I ran into a small technical hiccup. Please try again in a moment — I'm still here! 🙏"

        else:
            if lang in ["hi", "mixed"]:
                msg = "Kuch nahi hua — dobara try karo please. Main ready hoon! 😊"
            else:
                msg = "Something went wrong on my end. Please try again — I'm ready when you are! 😊"

        return {
            "tutor_response":      msg,
            "updated_ca_phase":    self.current_phase,   # phase unchanged
            "on_topic_flag":       True,
            "suggested_next_action": f"Please try again in {error.retry_after} seconds." if error.retry_after else "Please try again.",
            "_is_error_response":  True,
            "_retry_after":        error.retry_after,
        }

    def _parse_and_validate(self, raw_text: str) -> dict:
        # Attempt 1
        try:
            data = _extract_json(raw_text)
            return TutorOutput(**data).model_dump()
        except Exception:
            pass

        # Attempt 2: repair
        print_warning("Gemini returned unexpected format. Retrying once…")
        repair_prompt = (
            f"Fix the following into valid JSON matching this schema exactly:\n"
            f'{{"tutor_response":"...","updated_ca_phase":"...","on_topic_flag":true/false,'
            f'"suggested_next_action":"..."}}\n\nReturn ONLY raw JSON:\n\n{raw_text}'
        )
        try:
            raw2 = call_gemini(
                system_prompt=_SYSTEM_PROMPT,
                session_config={},
                conversation_history=[],
                user_message=repair_prompt,
            )
            return TutorOutput(**_extract_json(raw2)).model_dump()
        except Exception:
            pass

        print_warning("Repair failed. Using safe fallback response.")
        return fallback_output(self.current_phase)

    # ── Main turn processor ───────────────────────────────────────────────────

    def process_turn(self, user_message: str, debug: bool = False) -> dict:
        """
        Processes one user turn.
        Phase is 100% Gemini's decision.
        Mastery tracks skill level only — does not gate phase.
        """
        self.turn_count += 1

        # 1. Update signal scorecard
        signal_scores = self.scorecard.update(
            user_message, self.config.skill_topic,
            self.conversation_history,
        )

        # 2. Update mastery (skill tracker only — never gates phase)
        old_mastery = self.mastery_level
        self.mastery_level = update_mastery(self.mastery_level, signal_scores)

        # 3. Call Gemini with full context
        try:
            raw_response = call_gemini(
                system_prompt=_SYSTEM_PROMPT,
                session_config=self._session_config_dict(signal_scores),
                conversation_history=self.conversation_history,
                user_message=user_message,
            )
        except GeminiUnavailableError as e:
            output = self._friendly_error_response(e)
            output["_debug"] = {
                "signal_scores":  signal_scores,
                "mastery_before": round(old_mastery, 3),
                "mastery_after":  round(self.mastery_level, 3),
                "final_phase":    self.current_phase,
                "turn":           self.turn_count,
                "error":          e.reason,
                "retry_after":    e.retry_after,
            }
            return output

        # 4. Parse + validate Gemini output
        output = self._parse_and_validate(raw_response)

        # 5. Apply Gemini's phase — Gemini owns phase fully, no overrides
        proposed_phase = output.get("updated_ca_phase", self.current_phase)
        safe_phase     = validate_phase(proposed_phase, self.current_phase)

        if safe_phase != proposed_phase:
            # Gemini returned invalid phase string → signal-based fallback
            safe_phase = fallback_phase_update(self.current_phase, signal_scores)
            print_warning(f"Invalid phase from Gemini → fallback: {safe_phase}")

        self.current_phase = safe_phase
        output["updated_ca_phase"] = safe_phase

        # 6. Update conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": output["tutor_response"]})

        # 7. Attach debug info
        output["_debug"] = {
            "signal_scores":  signal_scores,
            "mastery_before": round(old_mastery, 3),
            "mastery_after":  round(self.mastery_level, 3),
            "final_phase":    safe_phase,
            "turn":           self.turn_count,
        }

        return output

    def save_log(self):
        """Appends full session to logs/conversations.json."""
        CONVERSATION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        existing: list = []
        if CONVERSATION_LOG_PATH.exists():
            try:
                with open(CONVERSATION_LOG_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    if not isinstance(existing, list):
                        existing = []
            except json.JSONDecodeError:
                existing = []

        session_record = {
            "config":             self.config.model_dump(),
            "final_phase":        self.current_phase,
            "final_mastery":      round(self.mastery_level, 3),
            "turns":              self.turn_count,
            "conversation":       self.conversation_history,
            "signal_scorecard":   self.scorecard.to_dict(),
            "signal_history":     self.scorecard.history,
        }
        existing.append(session_record)

        with open(CONVERSATION_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
