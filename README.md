# Vidya V3 — Real-Time AI Tutor (Terminal POC)

A modular, terminal-based AI tutoring system powered by **Google Gemini** and
**Cognitive Apprenticeship (CA)** pedagogy. Zero UI, zero server — just Python
and a terminal.

---

## Architecture

```
vidya-realtime-ai-tutor/
├── src/
│   ├── main.py            ← entry point + REPL loop
│   ├── config.py          ← env vars + constants
│   ├── gemini_client.py   ← Gemini API (google-genai SDK)
│   ├── tutor_session.py   ← per-turn orchestration
│   ├── schemas.py         ← Pydantic input/output models
│   ├── signal_extractor.py← local debug signal detector
│   ├── phase_manager.py   ← fallback CA phase logic
│   └── utils.py           ← terminal colors + helpers
├── prompts/
│   └── system_prompt.txt  ← Gemini's identity + rules
├── logs/
│   └── conversations.json ← auto-saved session logs
├── requirements.txt
└── .env.example
```

---

## Quickstart

```bash
# 1. Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up API key
copy .env.example .env        # Windows
cp .env.example .env          # macOS/Linux

# Edit .env and paste your Gemini API key:
# GEMINI_API_KEY=your_key_here

# 4. Run the tutor
python src/main.py

# Optional: enable debug signal view on startup
python src/main.py --debug
```

---

## Getting a Gemini API Key

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click **Create API key**
4. Paste it into your `.env` file

---

## Session Setup (one-time per run)

When you run the app you'll be asked:

| Question | Example inputs |
|---|---|
| Skill topic | `Python functions`, `SQL joins`, `OOP concepts` |
| Mastery level | `0.0` (beginner) → `1.0` (expert), e.g. `0.2` |
| Who are you? | `1` for student, `2` for service engineer |
| Starting phase | `1` MODEL, `2` COACH, `3` SCAFFOLD, `4` FADE |
| Language | `1` English, `2` Hindi, `3` Mixed |

---

## Demo Conversation (Python Functions, student, en)

```
You: I don't understand what a function is.
🎓 Vidya [MODEL]
A function is a reusable block of code. Think of it like a recipe:
def greet(name):
    return f"Hello, {name}!"
greet("Riya") → "Hello, Riya!"
The def keyword defines it; you call it by name.
💡 Next: Try writing a function that adds two numbers.

You: Just tell me the answer.
🎓 Vidya [COACH]
I'd love to help — but you'll learn much more by trying first!
What would the function signature look like? What inputs would it take?
💡 Next: Start with: def add(a, b): and see what you can fill in.

You: Can you teach me cricket?
🎓 Vidya [COACH]
That's a fun topic! But right now we're focused on Python functions —
and you're doing well! Let's stick with it. What part of functions
feels most unclear?
💡 Next: Come back to Python functions — you're almost there!

You: exit
✅ Conversation saved to logs/conversations.json (3 turns)
```

---

## Cognitive Apprenticeship Phases

| Phase | Tutor Behaviour |
|---|---|
| **MODEL** | Shows a worked example, thinks out loud |
| **COACH** | Asks guiding questions, no direct answers |
| **SCAFFOLD** | Partial hints, fills gaps not full solutions |
| **FADE** | Learner leads, tutor lightly nudges |

Gemini decides which phase to advance/hold/regress based on your responses.

---

## Debug Mode

Type `debug` at any point during the chat to toggle signal visibility:

```
[DEBUG] signals=confusion, answer_seeking  |  phase_reason=turn 3
```

Or start with `--debug` for it enabled from the first turn.

---

## Swapping LLM Provider

The Gemini call is isolated in `src/gemini_client.py`. To swap to OpenAI or
Anthropic Claude:

1. Open `src/gemini_client.py`
2. Replace the `call_gemini()` function body with your provider's SDK call
3. Keep the same function signature and return type (raw string)
4. Update `requirements.txt` with the new SDK
5. Add the new `*_API_KEY` to `.env.example`

`tutor_session.py`, `main.py`, and everything else stay unchanged.

---

## Log Format (`logs/conversations.json`)

```json
[
  {
    "config": { "skill_topic": "...", "mastery_level": 0.2, ... },
    "final_phase": "COACH",
    "turns": 5,
    "conversation": [
      { "role": "user", "content": "..." },
      { "role": "assistant", "content": "..." }
    ]
  }
]
```

---

## Requirements

- Python 3.10+
- Google Gemini API key (free tier available)
- Dependencies: `google-genai`, `python-dotenv`, `pydantic`
