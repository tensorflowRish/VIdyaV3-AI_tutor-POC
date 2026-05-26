"""
streamlit_app.py — Vidya V3 Real-Time AI Tutor — Streamlit UI

Run: streamlit run streamlit_app.py

Features:
- Full chat interface with Vidya V3
- Live signal scorecard with bar charts
- Mastery level tracker
- Phase history timeline
- ICP + session config panel
- Conversation history viewer
- Session logs browser
"""

import streamlit as st
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Vidya V3 — AI Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg:        #0F0F13;
    --bg2:       #16161C;
    --bg3:       #1E1E27;
    --border:    #2A2A38;
    --text:      #E8E8F0;
    --muted:     #6B6B85;
    --accent:    #7C6FF7;
    --green:     #3DD68C;
    --amber:     #F5A623;
    --red:       #FF5C5C;
    --blue:      #4EADFF;
    --model-c:   #4EADFF;
    --coach-c:   #3DD68C;
    --scaffold-c:#F5A623;
    --fade-c:    #B57BFF;
}

html, body, [data-testid="stApp"] {
    background-color: var(--bg) !important;
    font-family: 'DM Sans', sans-serif;
    color: var(--text);
}

[data-testid="stSidebar"] {
    background-color: var(--bg2) !important;
    border-right: 1px solid var(--border);
}

/* Hide streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* Cards */
.v-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
}

/* Chat bubbles */
.chat-user {
    display: flex;
    justify-content: flex-end;
    margin: 8px 0;
}
.chat-user .bubble {
    background: var(--accent);
    color: white;
    padding: 10px 16px;
    border-radius: 18px 18px 4px 18px;
    max-width: 72%;
    font-size: 14px;
    line-height: 1.6;
}
.chat-tutor {
    display: flex;
    justify-content: flex-start;
    margin: 8px 0;
    gap: 10px;
    align-items: flex-start;
}
.chat-tutor .avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
    margin-top: 4px;
}
.chat-tutor .bubble {
    background: var(--bg3);
    border: 1px solid var(--border);
    padding: 10px 16px;
    border-radius: 18px 18px 18px 4px;
    max-width: 72%;
    font-size: 14px;
    line-height: 1.6;
}
.phase-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 99px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'Space Mono', monospace;
    margin-bottom: 4px;
}
.phase-MODEL    { background: rgba(78,173,255,.15); color: var(--model-c); }
.phase-COACH    { background: rgba(61,214,140,.15); color: var(--coach-c); }
.phase-SCAFFOLD { background: rgba(245,166,35,.15);  color: var(--scaffold-c); }
.phase-FADE     { background: rgba(181,123,255,.15); color: var(--fade-c); }

.suggestion {
    font-size: 12px;
    color: var(--accent);
    margin-top: 6px;
    font-style: italic;
}

/* Signal bars */
.signal-row {
    display: grid;
    grid-template-columns: 110px 1fr 48px;
    align-items: center;
    gap: 8px;
    margin: 5px 0;
}
.signal-label { font-size: 12px; color: var(--muted); }
.signal-bar-track {
    height: 6px;
    background: var(--bg3);
    border-radius: 99px;
    overflow: hidden;
    position: relative;
}
.signal-bar-fill {
    height: 100%;
    border-radius: 99px;
    transition: width .4s ease;
}
.signal-val { font-size: 11px; text-align: right; font-family: 'Space Mono', monospace; }

/* Mastery bar */
.mastery-track {
    height: 10px;
    background: var(--bg3);
    border-radius: 99px;
    overflow: hidden;
    margin: 6px 0;
}
.mastery-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--green));
    border-radius: 99px;
    transition: width .5s ease;
}

/* Section header */
.sec-header {
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .08em;
    margin-bottom: 10px;
}

/* Input area */
.stTextInput input, .stSelectbox select, [data-baseweb="select"] {
    background: var(--bg3) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
}

/* Buttons */
.stButton button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
}
.stButton button:hover {
    background: #6B5FD9 !important;
}

/* Metrics */
.metric-box {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 16px;
    text-align: center;
}
.metric-val {
    font-family: 'Space Mono', monospace;
    font-size: 22px;
    font-weight: 700;
    color: var(--text);
}
.metric-label {
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-top: 2px;
}

/* Phase timeline */
.timeline-item {
    display: flex;
    gap: 10px;
    align-items: center;
    padding: 5px 0;
    font-size: 12px;
    border-bottom: 1px solid var(--border);
}
.timeline-item:last-child { border-bottom: none; }
.timeline-turn {
    width: 28px;
    font-family: 'Space Mono', monospace;
    color: var(--muted);
    flex-shrink: 0;
}

/* Scrollable chat area */
.chat-scroll {
    max-height: 520px;
    overflow-y: auto;
    padding-right: 4px;
}

/* Slider */
[data-testid="stSlider"] {
    color: var(--accent) !important;
}

/* Divider */
hr { border-color: var(--border) !important; }

</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def signal_color(score: float) -> str:
    if score >= 65: return "#FF5C5C" if score >= 80 else "#F5A623"
    if score <= 35: return "#3DD68C"
    return "#6B6B85"

def phase_color(phase: str) -> str:
    return {"MODEL": "#4EADFF", "COACH": "#3DD68C",
            "SCAFFOLD": "#F5A623", "FADE": "#B57BFF"}.get(phase, "#6B6B85")

def phase_emoji(phase: str) -> str:
    return {"MODEL": "📖", "COACH": "💬", "SCAFFOLD": "🧩", "FADE": "🚀"}.get(phase, "🎓")

def render_signal_bar(label: str, score: float):
    color = signal_color(score)
    pct   = score
    st.markdown(f"""
    <div class="signal-row">
        <div class="signal-label">{label}</div>
        <div class="signal-bar-track">
            <div class="signal-bar-fill" style="width:{pct}%;background:{color}"></div>
        </div>
        <div class="signal-val" style="color:{color}">{score:.0f}</div>
    </div>
    """, unsafe_allow_html=True)

def render_mastery_bar(mastery: float):
    pct = mastery * 100
    st.markdown(f"""
    <div class="mastery-track">
        <div class="mastery-fill" style="width:{pct}%"></div>
    </div>
    """, unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "session":        None,
        "messages":       [],   # [{role, content, phase, mastery, signals, suggestion}]
        "phase_history":  [],   # [(turn, phase)]
        "mastery_history":[],   # [(turn, mastery)]
        "configured":     False,
        "turn_count":     0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ── Sidebar — Session Config ──────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:16px 0 8px">
        <div style="font-family:'Space Mono',monospace;font-size:20px;font-weight:700;color:#7C6FF7">
            VIDYA V3
        </div>
        <div style="font-size:12px;color:#6B6B85;margin-top:2px">Real-Time AI Tutor</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="sec-header">Session Config</div>', unsafe_allow_html=True)

    skill_topic = st.text_input(
        "Skill Topic",
        value="Python functions",
        placeholder="e.g. Python functions",
        disabled=st.session_state.configured,
    )

    mastery_input = st.slider(
        "Starting Mastery Level",
        0.0, 1.0, 0.2, 0.05,
        disabled=st.session_state.configured,
    )

    icp_type = st.selectbox(
        "ICP Type",
        ["low_wage", "high_wage"],
        format_func=lambda x: {
            "low_wage":  "🌱 Low Wage — Early career / reskilling",
            "high_wage": "🚀 High Wage — Professional / aspirational",
        }[x],
        disabled=st.session_state.configured,
    )

    language = st.selectbox(
        "Language",
        ["en", "hi", "mixed"],
        format_func=lambda x: {"en": "🇬🇧 English", "hi": "🇮🇳 Hindi/Hinglish", "mixed": "🔀 Mixed"}[x],
        disabled=st.session_state.configured,
    )

    if not st.session_state.configured:
        if st.button("🚀 Start Session", use_container_width=True):
            try:
                from src.schemas import SessionConfig
                from src.icp_profiles import mastery_to_phase
                from src.tutor_session import TutorSession

                auto_phase = mastery_to_phase(mastery_input, icp_type)
                config = SessionConfig(
                    skill_topic=skill_topic,
                    mastery_level=mastery_input,
                    icp_type=icp_type,
                    ca_phase=auto_phase,
                    language_preference=language,
                )
                st.session_state.session        = TutorSession(config)
                st.session_state.configured     = True
                st.session_state.phase_history  = [(0, auto_phase)]
                st.session_state.mastery_history= [(0, mastery_input)]
                st.rerun()
            except Exception as e:
                st.error(f"Setup failed: {e}")
    else:
        if st.button("🔄 New Session", use_container_width=True):
            for k in ["session","messages","phase_history","mastery_history","configured","turn_count"]:
                del st.session_state[k]
            st.rerun()

    st.markdown("---")

    # Live signal scorecard
    if st.session_state.configured and st.session_state.session:
        sess = st.session_state.session
        st.markdown('<div class="sec-header">Signal Scorecard</div>', unsafe_allow_html=True)
        scores = sess.scorecard.to_dict()
        for sig in ["confidence", "effort", "confusion", "frustration", "answer_seeking", "off_topic"]:
            render_signal_bar(sig, scores.get(sig, 50))

        st.markdown("---")
        st.markdown('<div class="sec-header">Mastery Level</div>', unsafe_allow_html=True)
        mastery = sess.mastery_level
        render_mastery_bar(mastery)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-val">{mastery:.3f}</div>
                <div class="metric-label">Mastery</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            phase = sess.current_phase
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-val" style="color:{phase_color(phase)}">{phase}</div>
                <div class="metric-label">Phase</div>
            </div>""", unsafe_allow_html=True)

        # Phase timeline
        if st.session_state.phase_history:
            st.markdown("---")
            st.markdown('<div class="sec-header">Phase Timeline</div>', unsafe_allow_html=True)
            for turn, phase in st.session_state.phase_history[-8:]:
                st.markdown(f"""
                <div class="timeline-item">
                    <div class="timeline-turn">T{turn}</div>
                    <span class="phase-badge phase-{phase}">{phase_emoji(phase)} {phase}</span>
                </div>""", unsafe_allow_html=True)

        # Judge stats
        if hasattr(sess.scorecard, 'stats'):
            st.markdown("---")
            st.caption(f"🔍 {sess.scorecard.stats()}")


# ── Main area ─────────────────────────────────────────────────────────────────

if not st.session_state.configured:
    # Welcome screen
    st.markdown("""
    <div style="text-align:center;padding:80px 0 40px">
        <div style="font-size:56px;margin-bottom:16px">🎓</div>
        <div style="font-family:'Space Mono',monospace;font-size:28px;font-weight:700;color:#E8E8F0;margin-bottom:8px">
            VIDYA V3
        </div>
        <div style="font-size:16px;color:#6B6B85;margin-bottom:32px">
            Real-Time AI Tutor · Cognitive Apprenticeship · Signal-Driven Adaptation
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    for col, icon, title, desc in [
        (c1, "📊", "Signal Scoring", "6 signals tracked as rolling 0–100 scores across turns"),
        (c2, "🎯", "ICP Adaptation", "low_wage vs high_wage — different tone, pace, and phase thresholds"),
        (c3, "🔄", "Phase Control", "Mastery level drives phase. Gemini cannot jump ahead of what's earned"),
    ]:
        with col:
            st.markdown(f"""
            <div class="v-card" style="text-align:center">
                <div style="font-size:28px;margin-bottom:8px">{icon}</div>
                <div style="font-weight:600;margin-bottom:4px">{title}</div>
                <div style="font-size:13px;color:#6B6B85">{desc}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;margin-top:32px;color:#6B6B85;font-size:13px">
        Configure your session in the sidebar and click <strong style="color:#7C6FF7">Start Session</strong>
    </div>
    """, unsafe_allow_html=True)

else:
    sess = st.session_state.session

    # Header row
    col_h1, col_h2, col_h3, col_h4 = st.columns([3,1,1,1])
    with col_h1:
        st.markdown(f"""
        <div style="padding:4px 0">
            <span style="font-family:'Space Mono',monospace;font-size:14px;color:#7C6FF7;font-weight:700">
                {sess.config.skill_topic.upper()}
            </span>
            <span style="color:#6B6B85;font-size:13px;margin-left:12px">
                {sess.config.icp_type} · {sess.config.language_preference}
            </span>
        </div>
        """, unsafe_allow_html=True)
    with col_h2:
        st.markdown(f"""<div class="metric-box">
            <div class="metric-val">{st.session_state.turn_count}</div>
            <div class="metric-label">Turns</div>
        </div>""", unsafe_allow_html=True)
    with col_h3:
        st.markdown(f"""<div class="metric-box">
            <div class="metric-val">{sess.mastery_level:.2f}</div>
            <div class="metric-label">Mastery</div>
        </div>""", unsafe_allow_html=True)
    with col_h4:
        phase = sess.current_phase
        st.markdown(f"""<div class="metric-box">
            <div class="metric-val" style="color:{phase_color(phase)};font-size:16px">
                {phase_emoji(phase)} {phase}
            </div>
            <div class="metric-label">Phase</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

    # ── Chat area ─────────────────────────────────────────────────────────────
    chat_container = st.container()

    with chat_container:
        st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)

        if not st.session_state.messages:
            st.markdown("""
            <div style="text-align:center;padding:40px;color:#6B6B85;font-size:14px">
                Session started. Type your first message below.
            </div>""", unsafe_allow_html=True)

        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="chat-user">
                    <div class="bubble">{msg["content"]}</div>
                </div>""", unsafe_allow_html=True)
            else:
                phase     = msg.get("phase", "MODEL")
                mastery   = msg.get("mastery", 0.0)
                suggestion= msg.get("suggestion", "")
                st.markdown(f"""
                <div class="chat-tutor">
                    <div class="avatar" style="background:{phase_color(phase)}22;color:{phase_color(phase)}">
                        {phase_emoji(phase)}
                    </div>
                    <div>
                        <div><span class="phase-badge phase-{phase}">{phase}</span>
                        <span style="font-size:11px;color:#6B6B85;margin-left:6px">
                            mastery {mastery:.3f}
                        </span></div>
                        <div class="bubble">{msg["content"]}</div>
                        {f'<div class="suggestion">💡 {suggestion}</div>' if suggestion else ''}
                    </div>
                </div>""", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

    # ── Input area ────────────────────────────────────────────────────────────
    with st.form("chat_form", clear_on_submit=True):
        col_inp, col_btn = st.columns([5, 1])
        with col_inp:
            user_input = st.text_input(
                "Message",
                placeholder="Type your message here...",
                label_visibility="collapsed",
            )
        with col_btn:
            submitted = st.form_submit_button("Send →", use_container_width=True)

    if submitted and user_input.strip():
        with st.spinner("Vidya is thinking..."):
            try:
                output = sess.process_turn(user_input.strip())
                st.session_state.turn_count += 1
                turn = st.session_state.turn_count

                # Save messages
                st.session_state.messages.append({
                    "role": "user", "content": user_input.strip()
                })
                st.session_state.messages.append({
                    "role":       "assistant",
                    "content":    output["tutor_response"],
                    "phase":      output["updated_ca_phase"],
                    "mastery":    sess.mastery_level,
                    "suggestion": output.get("suggested_next_action", ""),
                    "signals":    output["_debug"]["signal_scores"],
                })

                # Track history
                st.session_state.phase_history.append((turn, output["updated_ca_phase"]))
                st.session_state.mastery_history.append((turn, sess.mastery_level))

                # Show off-topic warning
                if not output.get("on_topic_flag", True):
                    st.warning("⚠️ Off-topic detected — Vidya redirected to the skill topic.")

                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")

    # ── Bottom tabs ───────────────────────────────────────────────────────────
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📈 Mastery Chart", "🔍 Debug Output", "📋 Session Log"])

    with tab1:
        if st.session_state.mastery_history:
            import pandas as pd
            df = pd.DataFrame(st.session_state.mastery_history, columns=["Turn", "Mastery"])
            # Add phase boundaries
            st.line_chart(df.set_index("Turn"), color="#7C6FF7", height=200)

            # ICP threshold reference
            icp = sess.config.icp_type
            from src.icp_profiles import get_icp
            profile = get_icp(icp)
            thresholds = profile["phase_thresholds"]
            st.markdown(f"""
            <div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:8px">
                {''.join(f'<span style="font-size:12px;color:{phase_color(p)}">{p}: {lo:.2f}–{hi:.2f}</span>'
                for p, (lo, hi) in thresholds.items())}
            </div>""", unsafe_allow_html=True)
        else:
            st.caption("Start chatting to see mastery chart.")

    with tab2:
        if st.session_state.messages:
            last_tutor = next(
                (m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None
            )
            if last_tutor and "signals" in last_tutor:
                st.markdown('<div class="sec-header">Last Turn Signal Scores</div>', unsafe_allow_html=True)
                sigs = last_tutor["signals"]
                cols = st.columns(3)
                for i, (sig, val) in enumerate(sigs.items()):
                    with cols[i % 3]:
                        color = signal_color(val)
                        st.markdown(f"""
                        <div class="metric-box" style="margin-bottom:8px">
                            <div class="metric-val" style="color:{color};font-size:18px">{val:.0f}</div>
                            <div class="metric-label">{sig}</div>
                        </div>""", unsafe_allow_html=True)
        else:
            st.caption("Debug info appears after first message.")

    with tab3:
        if st.session_state.messages:
            log_data = {
                "config": sess.config.model_dump(),
                "final_phase": sess.current_phase,
                "final_mastery": round(sess.mastery_level, 3),
                "turns": st.session_state.turn_count,
                "signal_scorecard": sess.scorecard.to_dict(),
                "conversation": [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
            }
            st.json(log_data)

            if st.button("💾 Save Session Log"):
                try:
                    sess.save_log()
                    st.success("Saved to logs/conversations.json")
                except Exception as e:
                    st.error(f"Save failed: {e}")
        else:
            st.caption("Session log appears after first message.")
