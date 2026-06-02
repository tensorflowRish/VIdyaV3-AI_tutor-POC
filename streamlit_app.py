"""
streamlit_app.py — Vidya V3 Real-Time AI Tutor — Streamlit UI
Run: streamlit run streamlit_app.py
"""

import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.schemas import SessionConfig
from src.phase_manager import suggest_starting_phase
from src.tutor_session import TutorSession
from src.icp_profiles import get_icp
from src.gemini_client import GeminiUnavailableError, transcribe_audio_bytes

st.set_page_config(
    page_title="Vidya V3 — AI Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
:root {
    --bg:#0F0F13; --bg2:#16161C; --bg3:#1E1E27; --border:#2A2A38;
    --text:#E8E8F0; --muted:#6B6B85; --accent:#7C6FF7;
    --green:#3DD68C; --amber:#F5A623; --red:#FF5C5C; --blue:#4EADFF;
    --model-c:#4EADFF; --coach-c:#3DD68C; --scaffold-c:#F5A623; --fade-c:#B57BFF;
}
html, body, [data-testid="stApp"] { background-color:var(--bg) !important; color:var(--text); }
#MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stSidebar"], [data-testid="collapsedControl"] { display:none !important; }
.block-container { padding:1rem 1.5rem !important; max-width:100% !important; }
.v-card { background:var(--bg2); border:1px solid var(--border); border-radius:12px; padding:14px 18px; margin-bottom:10px; }
.chat-user { display:flex; justify-content:flex-end; margin:8px 0; }
.chat-user .bubble { background:var(--accent); color:white; padding:10px 16px; border-radius:18px 18px 4px 18px; max-width:75%; font-size:14px; line-height:1.6; }
.chat-tutor { display:flex; justify-content:flex-start; margin:8px 0; gap:10px; align-items:flex-start; }
.tutor-avatar { width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:15px; flex-shrink:0; margin-top:4px; }
.chat-tutor .bubble { background:var(--bg3); border:1px solid var(--border); padding:10px 16px; border-radius:18px 18px 18px 4px; max-width:75%; font-size:14px; line-height:1.6; }
.phase-badge { display:inline-block; padding:2px 8px; border-radius:99px; font-size:11px; font-weight:600; margin-bottom:4px; }
.phase-MODEL { background:rgba(78,173,255,.15); color:var(--model-c); }
.phase-COACH { background:rgba(61,214,140,.15); color:var(--coach-c); }
.phase-SCAFFOLD { background:rgba(245,166,35,.15); color:var(--scaffold-c); }
.phase-FADE { background:rgba(181,123,255,.15); color:var(--fade-c); }
.mbox { background:var(--bg3); border:1px solid var(--border); border-radius:10px; padding:10px; text-align:center; }
.mbox-val { font-size:20px; font-weight:700; }
.mbox-lbl { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; margin-top:2px; }
.stButton button { background:var(--accent) !important; color:white !important; border:none !important; border-radius:8px !important; }
</style>
""",
    unsafe_allow_html=True,
)


def phase_color(p):
    return {"MODEL": "#4EADFF", "COACH": "#3DD68C", "SCAFFOLD": "#F5A623", "FADE": "#B57BFF"}.get(p, "#6B6B85")


def phase_emoji(p):
    return {"MODEL": "📖", "COACH": "💬", "SCAFFOLD": "🧩", "FADE": "🚀"}.get(p, "🎓")


def speak_text(text: str):
    safe = json.dumps(text)
    components.html(
        f"""
        <script>
          if (window.speechSynthesis) {{
            window.speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance({safe});
            window.speechSynthesis.speak(u);
          }}
        </script>
        """,
        height=0,
    )


for k, v in {
    "session": None, "messages": [], "phase_history": [],
    "mastery_history": [], "configured": False, "turn_count": 0,
    "panel_open": True, "voice_input_enabled": True, "voice_output_enabled": False,
    "pending_tts_text": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.voice_output_enabled and st.session_state.pending_tts_text:
    speak_text(st.session_state.pending_tts_text)
    st.session_state.pending_tts_text = ""


top_left, top_mid, top_right = st.columns([1, 6, 1])
with top_left:
    label = "◀ Panel" if st.session_state.panel_open else "▶ Panel"
    if st.button(label, key="panel_toggle"):
        st.session_state.panel_open = not st.session_state.panel_open
        st.rerun()

with top_mid:
    st.markdown(
        """
    <div style="text-align:center;padding:2px 0">
      <span style="font-size:16px;font-weight:700;color:#7C6FF7">VIDYA V3</span>
      <span style="color:#6B6B85;font-size:12px;margin-left:10px">Real-Time AI Tutor</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with top_right:
    if st.session_state.configured and st.session_state.session:
        p = st.session_state.session.current_phase
        st.markdown(
            f"""<div style="text-align:right;font-size:12px;color:{phase_color(p)};font-weight:700">{phase_emoji(p)} {p}</div>""",
            unsafe_allow_html=True,
        )

st.markdown("<hr style='margin:6px 0 12px'>", unsafe_allow_html=True)

if st.session_state.panel_open:
    col_panel, col_chat = st.columns([1, 3])
else:
    col_panel = None
    col_chat = st.container()


def process_user_message(user_text: str):
    sess = st.session_state.session
    try:
        with st.spinner("Vidya is thinking..."):
            output = sess.process_turn(user_text.strip())
    except Exception:
        st.error("Something went wrong. Please try again in a moment.")
        return

    st.session_state.turn_count += 1
    turn = st.session_state.turn_count
    st.session_state.messages.append({"role": "user", "content": user_text.strip()})
    st.session_state.messages.append({
        "role": "assistant",
        "content": output["tutor_response"],
        "phase": output["updated_ca_phase"],
        "mastery": sess.mastery_level,
        "suggestion": output.get("suggested_next_action", ""),
        "signals": output.get("_debug", {}).get("signal_scores", {}),
    })
    st.session_state.phase_history.append((turn, output["updated_ca_phase"]))
    st.session_state.mastery_history.append((turn, sess.mastery_level))

    if st.session_state.voice_output_enabled:
        st.session_state.pending_tts_text = output["tutor_response"]

    st.rerun()


def render_panel():
    disabled = st.session_state.configured
    st.markdown("#### Session Config")
    skill_topic = st.text_input("Skill Topic", value="Python functions", disabled=disabled)
    mastery_input = st.slider("Starting Mastery", 0.0, 1.0, 0.2, 0.05, disabled=disabled)
    icp_type = st.selectbox("ICP Type", ["low_wage", "high_wage"], disabled=disabled)
    language = st.selectbox("Language", ["en", "hi", "mixed"], disabled=disabled)

    st.markdown("#### Voice")
    st.session_state.voice_input_enabled = st.toggle("Voice Input", value=st.session_state.voice_input_enabled, disabled=not st.session_state.configured)
    st.session_state.voice_output_enabled = st.toggle("Voice Output", value=st.session_state.voice_output_enabled, disabled=not st.session_state.configured)

    if not disabled:
        if st.button("🚀 Start Session", use_container_width=True):
            try:
                auto_phase = suggest_starting_phase(mastery_input, icp_type)
                config = SessionConfig(
                    skill_topic=skill_topic, mastery_level=mastery_input,
                    icp_type=icp_type, ca_phase=auto_phase, language_preference=language,
                )
                st.session_state.session = TutorSession(config)
                st.session_state.configured = True
                st.session_state.phase_history = [(0, auto_phase)]
                st.session_state.mastery_history = [(0, mastery_input)]
                st.rerun()
            except Exception as e:
                st.error(f"Setup failed: {e}")
    else:
        if st.button("🔄 New Session", use_container_width=True):
            for k in ["session", "messages", "phase_history", "mastery_history", "configured", "turn_count"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()


def render_chat():
    if not st.session_state.configured:
        st.markdown(
            """
            <div style="text-align:center;padding:60px 0 30px">
                <div style="font-size:48px;margin-bottom:12px">🎓</div>
                <div style="font-size:22px;font-weight:700;color:#E8E8F0;margin-bottom:6px">VIDYA V3</div>
                <div style="font-size:14px;color:#6B6B85">Configure your session in the panel and click Start Session.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    sess = st.session_state.session
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""<div class="mbox"><div class="mbox-val" style="font-size:14px">{sess.config.skill_topic[:20]}</div><div class="mbox-lbl">Topic</div></div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div class="mbox"><div class="mbox-val">{st.session_state.turn_count}</div><div class="mbox-lbl">Turns</div></div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""<div class="mbox"><div class="mbox-val">{sess.mastery_level:.3f}</div><div class="mbox-lbl">Mastery</div></div>""", unsafe_allow_html=True)
    with m4:
        p = sess.current_phase
        st.markdown(f"""<div class="mbox"><div class="mbox-val" style="color:{phase_color(p)};font-size:15px">{phase_emoji(p)} {p}</div><div class="mbox-lbl">Phase</div></div>""", unsafe_allow_html=True)

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"""<div class="chat-user"><div class="bubble">{msg["content"]}</div></div>""", unsafe_allow_html=True)
        else:
            phase = msg.get("phase", "MODEL")
            mastery = msg.get("mastery", 0.0)
            suggestion = msg.get("suggestion", "")
            pc = phase_color(phase)
            st.markdown(
                f"""<div class="chat-tutor"><div class="tutor-avatar" style="background:{pc}22;color:{pc}">{phase_emoji(phase)}</div>
                <div><div><span class="phase-badge phase-{phase}">{phase}</span><span style="font-size:11px;color:#6B6B85;margin-left:6px">mastery {mastery:.3f}</span></div>
                <div class="bubble">{msg["content"]}</div>{f'<div style="font-size:12px;color:#7C6FF7;margin-top:5px;font-style:italic;">💡 {suggestion}</div>' if suggestion else ''}</div></div>""",
                unsafe_allow_html=True,
            )

    with st.form("chat_form", clear_on_submit=True):
        ci, cb = st.columns([5, 1])
        with ci:
            user_input = st.text_input("Message", placeholder="Type your message...", label_visibility="collapsed")
        with cb:
            submitted = st.form_submit_button("Send →", use_container_width=True)
    if submitted and user_input.strip():
        process_user_message(user_input)

    if st.session_state.voice_input_enabled:
        st.markdown("#### 🎤 Voice Input")
        audio_file = st.audio_input("Record your message")
        if st.button("Transcribe & Send Voice"):
            if audio_file is None:
                st.warning("Please record audio first.")
            else:
                try:
                    transcript = transcribe_audio_bytes(audio_file.read(), mime_type=(audio_file.type or "audio/wav"))
                except GeminiUnavailableError:
                    transcript = ""
                if not transcript:
                    st.warning("Could not detect speech. Please try again.")
                else:
                    st.info(f"Transcribed: {transcript}")
                    process_user_message(transcript)

    st.markdown("---")
    tab1, tab2 = st.tabs(["📈 Mastery Chart", "📋 Session Log"])
    with tab1:
        if st.session_state.mastery_history:
            df = pd.DataFrame(st.session_state.mastery_history, columns=["Turn", "Mastery"])
            st.line_chart(df.set_index("Turn"), color="#7C6FF7", height=180)
            profile = get_icp(sess.config.icp_type)
            thresholds = profile["phase_thresholds"]
            st.markdown(" &nbsp; ".join(f'<span style="font-size:11px;color:{phase_color(p)}">{p}: {lo:.2f}-{hi:.2f}</span>' for p, (lo, hi) in thresholds.items()), unsafe_allow_html=True)
    with tab2:
        log = {
            "config": sess.config.model_dump(),
            "final_phase": sess.current_phase,
            "final_mastery": round(sess.mastery_level, 3),
            "turns": st.session_state.turn_count,
            "signal_scorecard": sess.scorecard.to_dict(),
            "conversation": [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
        }
        st.json(log)
        if st.button("💾 Save Log"):
            try:
                sess.save_log()
                st.success("Saved to logs/conversations.json")
            except Exception as e:
                st.error(f"Save failed: {e}")


if st.session_state.panel_open and col_panel is not None:
    with col_panel:
        render_panel()
with col_chat:
    render_chat()

