"""
utils.py — Terminal colors, banner, and small helper utilities.
"""

import textwrap


# ── ANSI color codes ──────────────────────────────────────────────────────────

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    # Colors
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    MAGENTA = "\033[95m"
    BLUE    = "\033[94m"
    WHITE   = "\033[97m"
    GREY    = "\033[90m"


def banner():
    """Prints the Vidya V3 terminal banner."""
    print(f"\n{C.CYAN}{C.BOLD}")
    print("╔══════════════════════════════════════════════════════╗")
    print("║          VIDYA V3 — REAL-TIME AI TUTOR               ║")
    print("║     Powered by Gemini  •  Cognitive Apprenticeship   ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"{C.RESET}")


def print_tutor(text: str, phase: str):
    """Prints the tutor response with phase label."""
    phase_colors = {
        "MODEL":    C.BLUE,
        "COACH":    C.GREEN,
        "SCAFFOLD": C.YELLOW,
        "FADE":     C.MAGENTA,
    }
    color = phase_colors.get(phase, C.CYAN)
    phase_label = f"[{phase}]"

    wrapped = textwrap.fill(text, width=72)
    print(f"\n{color}{C.BOLD}🎓 Vidya {phase_label}{C.RESET}")
    print(f"{C.WHITE}{wrapped}{C.RESET}\n")


def print_debug(signals: dict, phase_reason: str = ""):
    """Prints debug signal info in dim grey."""
    active = [k for k, v in signals.items() if v]
    signal_str = ", ".join(active) if active else "none"
    print(f"{C.GREY}[DEBUG] signals={signal_str}", end="")
    if phase_reason:
        print(f"  |  phase_reason={phase_reason}", end="")
    print(f"{C.RESET}")


def print_suggestion(action: str):
    """Prints the suggested next action."""
    print(f"{C.CYAN}💡 Next: {action}{C.RESET}")


def print_warning(msg: str):
    print(f"{C.YELLOW}⚠️  {msg}{C.RESET}")


def print_error(msg: str):
    print(f"{C.RED}❌ {msg}{C.RESET}")


def print_success(msg: str):
    print(f"{C.GREEN}✅ {msg}{C.RESET}")


def count_words(text: str) -> int:
    return len(text.split())


def prompt_choice(label: str, choices: list[str]) -> str:
    """
    Prompts the user to pick from a numbered list.
    Returns the chosen string value.
    """
    print(f"\n{C.CYAN}{label}{C.RESET}")
    for i, choice in enumerate(choices, 1):
        print(f"  {C.BOLD}{i}.{C.RESET} {choice}")

    while True:
        raw = input(f"{C.YELLOW}Enter number (1-{len(choices)}): {C.RESET}").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            selected = choices[int(raw) - 1]
            print(f"  → {C.GREEN}{selected}{C.RESET}")
            return selected
        print_warning(f"Please enter a number between 1 and {len(choices)}.")


def prompt_float(label: str, lo: float, hi: float) -> float:
    """Prompts the user for a float in [lo, hi]."""
    while True:
        raw = input(f"{C.YELLOW}{label} ({lo}–{hi}): {C.RESET}").strip()
        try:
            val = float(raw)
            if lo <= val <= hi:
                return val
            print_warning(f"Value must be between {lo} and {hi}.")
        except ValueError:
            print_warning("Please enter a decimal number like 0.3 or 0.8.")


def prompt_text(label: str) -> str:
    """Prompts the user for a non-empty string."""
    while True:
        raw = input(f"{C.YELLOW}{label}: {C.RESET}").strip()
        if raw:
            return raw
        print_warning("This field cannot be empty.")
