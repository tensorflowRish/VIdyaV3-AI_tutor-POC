"""
main.py — Vidya V3 Real-Time AI Tutor — Terminal Entry Point.
Run: python src/main.py  [--debug]
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import VALID_LANGUAGES
from src.schemas import SessionConfig
from src.icp_profiles import mastery_to_phase, VALID_ICP_TYPES
from src.tutor_session import TutorSession
from src.utils import (
    banner, print_tutor, print_suggestion, print_debug,
    print_warning, print_error, print_success,
    prompt_choice, prompt_float, prompt_text, C,
)


# ── Setup wizard ──────────────────────────────────────────────────────────────

def run_setup() -> SessionConfig:
    print(f"{C.CYAN}{C.BOLD}── Session Setup ──────────────────────────────{C.RESET}")
    print(f"{C.DIM}Answer a few questions to personalise your tutor.{C.RESET}\n")

    skill_topic = prompt_text("What skill do you want to learn? (e.g. Python functions)")

    mastery_level = prompt_float(
        "Your current mastery level (0.0 = complete beginner, 1.0 = expert)", 0.0, 1.0
    )

    icp_type = prompt_choice(
        "Which best describes you?",
        [
            "low_wage  — Early-career / reskilling (delivery, data entry, CX, gig work)",
            "high_wage — Professional / aspirational (CS student, engineer, product company)",
        ],
    )
    icp_type = icp_type.split(" ")[0]   # extract "low_wage" or "high_wage"

    # Auto-assign starting phase from mastery + ICP (no manual selection needed)
    auto_phase = mastery_to_phase(mastery_level, icp_type)
    print(f"\n  {C.DIM}Starting phase auto-assigned from mastery level:{C.RESET} "
          f"{C.BOLD}{C.GREEN}{auto_phase}{C.RESET}")

    language_preference = prompt_choice(
        "Language preference",
        [
            "en    — English only",
            "hi    — Hindi / Hinglish",
            "mixed — Mix of Hindi and English",
        ],
    )
    language_preference = language_preference.split(" ")[0]

    config = SessionConfig(
        skill_topic=skill_topic,
        mastery_level=mastery_level,
        icp_type=icp_type,
        ca_phase=auto_phase,
        language_preference=language_preference,
    )

    print(f"\n{C.GREEN}{C.BOLD}✓ Session ready!{C.RESET}")
    print(f"  Topic   : {C.WHITE}{config.skill_topic}{C.RESET}")
    print(f"  ICP     : {C.WHITE}{config.icp_type}{C.RESET}")
    print(f"  Mastery : {C.WHITE}{config.mastery_level}{C.RESET}")
    print(f"  Phase   : {C.WHITE}{config.ca_phase}{C.RESET} (auto from mastery)")
    print(f"  Lang    : {C.WHITE}{config.language_preference}{C.RESET}")
    return config


# ── Chat loop ─────────────────────────────────────────────────────────────────

def run_chat(session: TutorSession, debug: bool):
    print(f"\n{C.CYAN}{'─'*54}{C.RESET}")
    print(f"{C.DIM}Type your message and press Enter.{C.RESET}")
    print(f"{C.DIM}Commands: {C.RESET}"
          f"{C.BOLD}exit{C.RESET}{C.DIM} · {C.RESET}"
          f"{C.BOLD}debug{C.RESET}{C.DIM} (toggle signals) · {C.RESET}"
          f"{C.BOLD}scores{C.RESET}{C.DIM} (show signal scorecard){C.RESET}")
    print(f"{C.CYAN}{'─'*54}{C.RESET}\n")

    while True:
        try:
            raw = input(f"{C.YELLOW}You: {C.RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not raw:
            continue

        if raw.lower() == "exit":
            break

        if raw.lower() == "debug":
            debug = not debug
            print(f"{C.GREY}[DEBUG mode {'ON' if debug else 'OFF'}]{C.RESET}")
            continue

        if raw.lower() == "scores":
            scores = session.scorecard.to_dict()
            print(f"\n{C.CYAN}── Signal Scorecard (0–100, neutral=50) ──{C.RESET}")
            for k, v in scores.items():
                bar_len = int(v / 5)
                bar = "█" * bar_len + "░" * (20 - bar_len)
                color = C.RED if v >= 65 else (C.GREEN if v <= 35 else C.WHITE)
                print(f"  {k:<15} {color}{bar}{C.RESET} {v:5.1f}")
            print(f"  {'mastery_level':<15} {C.MAGENTA}{'█' * int(session.mastery_level * 20)}"
                  f"{'░' * (20 - int(session.mastery_level * 20))}{C.RESET} "
                  f"{session.mastery_level:.3f}")
            print(f"  {C.GREY}signal detection: {session.scorecard.stats()}{C.RESET}")
            print()
            continue

        # ── Call the tutor ────────────────────────────────────────────────────
        print(f"{C.DIM}  Thinking…{C.RESET}", end="\r")
        try:
            output = session.process_turn(raw, debug=debug)
        except Exception as e:
            print(" " * 30, end="\r")
            print_warning("Something went wrong. Please try again in a moment.")
            continue

        print(" " * 30, end="\r")

        # ── Print tutor response ──────────────────────────────────────────────
        print_tutor(output["tutor_response"], output["updated_ca_phase"])

        if not output.get("on_topic_flag", True):
            print_warning("Off-topic detected — redirecting to your skill topic.")

        print_suggestion(output["suggested_next_action"])

        # ── Mastery indicator ─────────────────────────────────────────────────
        d = output["_debug"]
        mastery_arrow = "↑" if d["mastery_after"] > d["mastery_before"] else \
                        "↓" if d["mastery_after"] < d["mastery_before"] else "→"
        print(f"{C.DIM}  mastery: {d['mastery_before']:.3f} {mastery_arrow} "
              f"{d['mastery_after']:.3f}  |  phase: {d['final_phase']}{C.RESET}")

        # ── Debug panel ───────────────────────────────────────────────────────
        if debug:
            scores = d["signal_scores"]
            active = [f"{k}={v:.0f}" for k, v in scores.items() if v >= 65]
            inactive = [f"{k}={v:.0f}" for k, v in scores.items() if v <= 35]
            print(f"{C.GREY}[DEBUG] turn={d['turn']}{C.RESET}")
            if active:
                print(f"{C.GREY}  HIGH signals : {', '.join(active)}{C.RESET}")
            if inactive:
                print(f"{C.GREY}  LOW signals  : {', '.join(inactive)}{C.RESET}")
            print(f"{C.GREY}  mastery_phase={d['mastery_phase']}  final_phase={d['final_phase']}{C.RESET}")

        print(f"{C.GREY}{'─'*54}{C.RESET}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    banner()
    debug_mode = "--debug" in sys.argv

    try:
        config = run_setup()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Setup cancelled.{C.RESET}")
        sys.exit(0)

    session = TutorSession(config)

    try:
        run_chat(session, debug=debug_mode)
    finally:
        try:
            session.save_log()
            print_success(
                f"Session saved to logs/conversations.json  "
                f"({session.turn_count} turns | "
                f"final mastery: {session.mastery_level:.3f} | "
                f"final phase: {session.current_phase})"
            )
        except Exception as e:
            print_warning(f"Could not save log: {e}")

        print(f"\n{C.CYAN}Thank you for learning with Vidya V3. Keep going! 🚀{C.RESET}\n")


if __name__ == "__main__":
    main()
