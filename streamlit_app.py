"""
streamlit_app.py — Vidya V3 Real-Time AI Tutor — Streamlit UI
Run: streamlit run streamlit_app.py
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="Vidya V3 — AI Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",   # we handle our own panel
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg:#0F0F13; --bg2:#16161C; --bg3:#1E1E27; --border:#2A2A38;
    --text:#E8E8F0; --muted:#6B6B85; --accent:#7C6FF7;
    --green:#3DD68C; --amber:#F5A623; --red:#FF5C5C; --blue:#4EADFF;
    --model-c:#4EADFF; --coach-c:#3DD68C; --scaffold-c:#F5A623; --fade-c:#B57BFF;
}
html, body, [data-testid="stApp"] {
    background-color:var(--bg) !important;
    font-family:'DM Sans',sans-serif; color:var(--text);
}
/* Hide ALL native streamlit chrome including sidebar toggle */
#MainMenu, footer, header { visibility:hidden; }
[data-testid="stToolbar"] { display:none; }
[data-testid="stSidebar"] { display:none !important; }
[data-testid="collapsedControl"] { display:none !important; }
section[data-testid="stSidebar"] { display:none !important; }

/* Remove default padding */
.block-container { padding:1rem 1.5rem !important; max-width:100% !important; }

/* Cards */
.v-card {
    background:var(--bg2); border:1px solid var(--border);
    border-radius:12px; padding:14px 18px; margin-bottom:10px;
}
/* Panel (our custom sidebar) */
.panel {
    background:var(--bg2); border-right:1px solid var(--border);
    height:100vh; overflow-y:auto; padding:16px;
    position:sticky; top:0;
}
/* Chat bubbles */
.chat-user { display:flex; justify-content:flex-end; margin:8px 0; }
.chat-user .bubble {
    background:var(--accent); color:white;
    padding:10px 16px; border-radius:18px 18px 4px 18px;
    max-width:75%; font-size:14px; line-height:1.6;
}
.chat-tutor { display:flex; justify-content:flex-start; margin:8px 0; gap:10px; align-items:flex-start; }
.tutor-avatar {
    width:32px; height:32px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:15px; flex-shrink:0; margin-top:4px;
}
.chat-tutor .bubble {
    background:var(--bg3); border:1px solid var(--border);
    padding:10px 16px; border-radius:18px 18px 18px 4px;
    max-width:75%; font-size:14px; line-height:1.6;
}
.phase-badge {
    display:inline-block; padding:2px 8px; border-radius:99px;
    font-size:11px; font-weight:600; font-family:'Space Mono',monospace; margin-bottom:4px;
}
.phase-MODEL    { background:rgba(78,173,255,.15); color:var(--model-c); }
.phase-COACH    { background:rgba(61,214,140,.15); color:var(--coach-c); }
.phase-SCAFFOLD { background:rgba(245,166,35,.15); color:var(--scaffold-c); }
.phase-FADE     { background:rgba(181,123,255,.15); color:var(--fade-c); }
.suggestion { font-size:12px; color:var(--accent); margin-top:5px; font-style:italic; }

/* Signal bars */
.sig-row { display:grid; grid-template-columns:100px 1fr 42px; align-items:center; gap:6px; margin:4px 0; }
.sig-lbl { font-size:11px; color:var(--muted); }
.sig-track { height:5px; background:var(--bg3); border-radius:99px; overflow:hidden; }
.sig-fill { height:100%; border-radius:99px; }
.sig-val { font-size:10px; text-align:right; font-family:'Space Mono',monospace; }

/* Mastery bar */
.mast-track { height:8px; background:var(--bg3); border-radius:99px; overflow:hidden; margin:5px 0; }
.mast-fill { height:100%; background:linear-gradient(90deg,var(--accent),var(--green)); border-radius:99px; }

/* Section header */
.sec-hdr {
    font-family:'Space Mono',monospace; font-size:10px; font-weight:700;
    color:var(--muted); text-transform:uppercase; letter-spacing:.08em; margin-bottom:8px;
}
/* Metric box */
.mbox { background:var(--bg3); border:1px solid var(--border); border-radius:10px; padding:10px; text-align:center; }
.mbox-val { font-family:'Space Mono',monospace; font-size:20px; font-weight:700; }
.mbox-lbl { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; margin-top:2px; }

/* Timeline */
.tl-item { display:flex; gap:8px; align-items:center; padding:4px 0; border-bottom:1px solid var(--border); font-size:11px; }
.tl-item:last-child { border-bottom:none; }
.tl-turn { width:24px; font-family:'Space Mono',monospace; color:var(--muted); flex-shrink:0; }

/* Toggle button */
.toggle-btn {
    background:var(--bg3); border:1px solid var(--border); border-radius:8px;
    padding:6px 12px; cursor:pointer; font-size:13px; color:var(--text);
    font-family:'DM Sans',sans-serif; transition:all .2s;
}
.toggle-btn:hover { background:var(--border); border-color:var(--accent); }

/* Streamlit button override */
.stButton button {
    background:var(--accent) !important; color:white !important;
    border:none !important; border-radius:8px !important;
    font-family:'DM Sans',sans-serif !important; font-weight:500 !important;
}
.stButton button:hover { background:#6B5FD9 !important; }
div[data-testid="stForm"] button {
    background:var(--accent) !important; color:white !important;
    border:none !important; border-radius:8px !important;
}
/* Input fields */
.stTextInput input {
    background:var(--bg3) !important; border-color:var(--border) !important;
    color:var(--text) !important; border-radius:8px !important;
}
.stSelectbox > div, [data-baseweb="select"] > div {
    background:var(--bg3) !important; border-color:var(--border) !important;
    color:var(--text) !important; border-radius:8px !important;
}
hr { border-color:var(--border) !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def sig_color(s):
    if s >= 80: return "#FF5C5C"
    if s >= 65: return "#F5A623"
    if s <= 35: return "#3DD68C"
    return "#6B6B85"

def phase_color(p):
    return {"MODEL":"#4EADFF","COACH":"#3DD68C","SCAFFOLD":"#F5A623","FADE":"#B57BFF"}.get(p,"#6B6B85")

def phase_emoji(p):
    return {"MODEL":"📖","COACH":"💬","SCAFFOLD":"🧩","FADE":"🚀"}.get(p,"🎓")

def sig_bar(label, score):
    c = sig_color(score)
    st.markdown(f"""
    <div class="sig-row">
        <div class="sig-lbl">{label}</div>
        <div class="sig-track"><div class="sig-fill" style="width:{score}%;background:{c}"></div></div>
        <div class="sig-val" style="color:{c}">{score:.0f}</div>
    </div>""", unsafe_allow_html=True)

def mast_bar(m):
    st.markdown(f"""
    <div class="mast-track">
        <div class="mast-fill" style="width:{m*100:.1f}%"></div>
    </div>""", unsafe_allow_html=True)


# ── State init ────────────────────────────────────────────────────────────────
for k, v in {
    "session": None, "messages": [], "phase_history": [],
    "mastery_history": [], "configured": False,
    "turn_count": 0, "panel_open": True,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Layout: toggle button + two columns ──────────────────────────────────────
# Top bar
top_left, top_mid, top_right = st.columns([1, 6, 1])
with top_left:
    label = "◀ Panel" if st.session_state.panel_open else "▶ Panel"
    if st.button(label, key="panel_toggle"):
        st.session_state.panel_open = not st.session_state.panel_open
        st.rerun()

with top_mid:
    st.markdown("""
    <div style="text-align:center;padding:2px 0">
        <span style="font-family:'Space Mono',monospace;font-size:16px;font-weight:700;color:#7C6FF7">
            VIDYA V3
        </span>
        <span style="color:#6B6B85;font-size:12px;margin-left:10px">Real-Time AI Tutor</span>
    </div>""", unsafe_allow_html=True)

with top_right:
    if st.session_state.configured and st.session_state.session:
        sess = st.session_state.session
        phase = sess.current_phase
        st.markdown(f"""
        <div style="text-align:right;font-size:12px">
            <span style="color:{phase_color(phase)};font-family:'Space Mono',monospace;font-weight:700">
                {phase_emoji(phase)} {phase}
            </span>
        </div>""", unsafe_allow_html=True)

st.markdown("<hr style='margin:6px 0 12px'>", unsafe_allow_html=True)

# ── Main columns ──────────────────────────────────────────────────────────────
if st.session_state.panel_open:
    col_panel, col_chat = st.columns([1, 3])
else:
    col_panel = None
    col_chat = st.container()

# ── LEFT PANEL ────────────────────────────────────────────────────────────────
def render_panel():
    st.markdown('<div class="sec-hdr">Session Config</div>', unsafe_allow_html=True)

    disabled = st.session_state.configured

    skill_topic = st.text_input("Skill Topic", value="Python functions", disabled=disabled)
    mastery_input = st.slider("Starting Mastery", 0.0, 1.0, 0.2, 0.05, disabled=disabled)
    icp_type = st.selectbox("ICP Type", ["low_wage", "high_wage"],
        format_func=lambda x: {"low_wage":"🌱 Low Wage","high_wage":"🚀 High Wage"}[x],
        disabled=disabled)
    language = st.selectbox("Language", ["en", "hi", "mixed"],
        format_func=lambda x: {"en":"🇬🇧 English","hi":"🇮🇳 Hindi","mixed":"🔀 Mixed"}[x],
        disabled=disabled)

    if not disabled:
        if st.button("🚀 Start Session", use_container_width=True):
            try:
                from src.schemas import SessionConfig
                from src.phase_manager import suggest_starting_phase
                from src.tutor_session import TutorSession
                auto_phase = suggest_starting_phase(mastery_input, icp_type)
                config = SessionConfig(
                    skill_topic=skill_topic, mastery_level=mastery_input,
                    icp_type=icp_type, ca_phase=auto_phase, language_preference=language,
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

    if st.session_state.configured and st.session_state.session:
        sess = st.session_state.session
        st.markdown("---")
        st.markdown('<div class="sec-hdr">Signal Scorecard</div>', unsafe_allow_html=True)
        scores = sess.scorecard.to_dict()
        for sig in ["confidence","effort","confusion","frustration","answer_seeking","off_topic"]:
            sig_bar(sig, scores.get(sig, 50))

        st.markdown("---")
        st.markdown('<div class="sec-hdr">Mastery Level</div>', unsafe_allow_html=True)
        mastery = sess.mastery_level
        mast_bar(mastery)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""<div class="mbox">
                <div class="mbox-val">{mastery:.3f}</div>
                <div class="mbox-lbl">Mastery</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            p = sess.current_phase
            st.markdown(f"""<div class="mbox">
                <div class="mbox-val" style="color:{phase_color(p)};font-size:16px">{phase_emoji(p)} {p}</div>
                <div class="mbox-lbl">Phase</div>
            </div>""", unsafe_allow_html=True)

        if st.session_state.phase_history:
            st.markdown("---")
            st.markdown('<div class="sec-hdr">Phase Timeline</div>', unsafe_allow_html=True)
            for turn, phase in st.session_state.phase_history[-8:]:
                st.markdown(f"""
                <div class="tl-item">
                    <div class="tl-turn">T{turn}</div>
                    <span class="phase-badge phase-{phase}">{phase_emoji(phase)} {phase}</span>
                </div>""", unsafe_allow_html=True)

        if hasattr(sess.scorecard, 'stats'):
            st.markdown("---")
            st.caption(f"🔍 {sess.scorecard.stats()}")


if st.session_state.panel_open:
    with col_panel:
        render_panel()
else:
    # Render nothing — panel is hidden
    pass


# ── RIGHT CHAT AREA ───────────────────────────────────────────────────────────
def render_chat():
    sess = st.session_state.session if st.session_state.configured else None

    if not st.session_state.configured:
        # Welcome
        st.markdown("""
        <div style="text-align:center;padding:60px 0 30px">
            <div style="font-size:48px;margin-bottom:12px">🎓</div>
            <div style="font-family:'Space Mono',monospace;font-size:22px;font-weight:700;color:#E8E8F0;margin-bottom:6px">
                VIDYA V3
            </div>
            <div style="font-size:14px;color:#6B6B85">
                Configure your session in the panel and click Start Session.
            </div>
        </div>""", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        for col, icon, title, desc in [
            (c1,"📊","Signal Scoring","6 signals tracked as rolling 0–100 scores"),
            (c2,"🎯","ICP Adaptation","low_wage vs high_wage — different tone and phase"),
            (c3,"🔄","Phase Control","Mastery drives phase — Gemini can't jump ahead"),
        ]:
            with col:
                st.markdown(f"""<div class="v-card" style="text-align:center">
                    <div style="font-size:24px;margin-bottom:6px">{icon}</div>
                    <div style="font-weight:600;margin-bottom:4px;font-size:14px">{title}</div>
                    <div style="font-size:12px;color:#6B6B85">{desc}</div>
                </div>""", unsafe_allow_html=True)
        return

    # Header metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""<div class="mbox">
            <div class="mbox-val" style="font-size:14px">{sess.config.skill_topic[:20]}</div>
            <div class="mbox-lbl">Topic</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div class="mbox">
            <div class="mbox-val">{st.session_state.turn_count}</div>
            <div class="mbox-lbl">Turns</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""<div class="mbox">
            <div class="mbox-val">{sess.mastery_level:.3f}</div>
            <div class="mbox-lbl">Mastery</div>
        </div>""", unsafe_allow_html=True)
    with m4:
        p = sess.current_phase
        st.markdown(f"""<div class="mbox">
            <div class="mbox-val" style="color:{phase_color(p)};font-size:15px">{phase_emoji(p)} {p}</div>
            <div class="mbox-lbl">Phase</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin:10px 0'></div>", unsafe_allow_html=True)

    # Chat messages
    if not st.session_state.messages:
        st.markdown("""<div style="text-align:center;padding:30px;color:#6B6B85;font-size:14px">
            Session started. Type your first message below. 👇
        </div>""", unsafe_allow_html=True)

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="chat-user">
                <div class="bubble">{msg["content"]}</div>
            </div>""", unsafe_allow_html=True)
        else:
            phase     = msg.get("phase","MODEL")
            mastery   = msg.get("mastery", 0.0)
            suggestion= msg.get("suggestion","")
            pc        = phase_color(phase)
            st.markdown(f"""
            <div class="chat-tutor">
                <div class="tutor-avatar" style="background:{pc}22;color:{pc}">{phase_emoji(phase)}</div>
                <div>
                    <div>
                        <span class="phase-badge phase-{phase}">{phase}</span>
                        <span style="font-size:11px;color:#6B6B85;margin-left:6px">mastery {mastery:.3f}</span>
                    </div>
                    <div class="bubble">{msg["content"]}</div>
                    {f'<div class="suggestion">💡 {suggestion}</div>' if suggestion else ''}
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

    # Input
    with st.form("chat_form", clear_on_submit=True):
        ci, cb = st.columns([5,1])
        with ci:
            user_input = st.text_input("Message", placeholder="Type your message...",
                                       label_visibility="collapsed")
        with cb:
            submitted = st.form_submit_button("Send →", use_container_width=True)

    if submitted and user_input.strip():
        with st.spinner("Vidya is thinking..."):
            try:
                output = sess.process_turn(user_input.strip())
                st.session_state.turn_count += 1
                turn = st.session_state.turn_count

                st.session_state.messages.append({"role":"user","content":user_input.strip()})

                # Check if this is an error response (rate limit etc)
                is_error = output.get("_is_error_response", False)
                retry_after = output.get("_retry_after", 0)

                st.session_state.messages.append({
                    "role":"assistant",
                    "content":output["tutor_response"],
                    "phase":output["updated_ca_phase"],
                    "mastery":sess.mastery_level,
                    "suggestion":output.get("suggested_next_action",""),
                    "signals":output["_debug"].get("signal_scores", {}),
                    "is_error": is_error,
                    "retry_after": retry_after,
                })
                st.session_state.phase_history.append((turn, output["updated_ca_phase"]))
                st.session_state.mastery_history.append((turn, sess.mastery_level))

                if not output.get("on_topic_flag", True):
                    st.warning("⚠️ Off-topic — Vidya redirected to skill topic.")

                if is_error and retry_after:
                    st.info(f"⏱️ Vidya will be ready again in ~{retry_after} seconds. Please wait before sending the next message.")

                st.rerun()
            except Exception as e:
                st.error(f"Something went wrong. Please try again in a moment.")

    # Bottom tabs
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📈 Mastery Chart", "🔍 Signal Debug", "📋 Session Log"])

    with tab1:
        if st.session_state.mastery_history:
            import pandas as pd
            df = pd.DataFrame(st.session_state.mastery_history, columns=["Turn","Mastery"])
            st.line_chart(df.set_index("Turn"), color="#7C6FF7", height=180)
            from src.icp_profiles import get_icp
            profile = get_icp(sess.config.icp_type)
            thresholds = profile["phase_thresholds"]
            st.markdown(" &nbsp; ".join(
                f'<span style="font-size:11px;color:{phase_color(p)}">{p}: {lo:.2f}–{hi:.2f}</span>'
                for p,(lo,hi) in thresholds.items()
            ), unsafe_allow_html=True)
        else:
            st.caption("Start chatting to see mastery chart.")

    with tab2:
        if st.session_state.messages:
            last = next((m for m in reversed(st.session_state.messages) if m["role"]=="assistant"), None)
            if last and "signals" in last:
                cols = st.columns(3)
                for i,(sig,val) in enumerate(last["signals"].items()):
                    with cols[i%3]:
                        c = sig_color(val)
                        st.markdown(f"""<div class="mbox" style="margin-bottom:8px">
                            <div class="mbox-val" style="color:{c};font-size:18px">{val:.0f}</div>
                            <div class="mbox-lbl">{sig}</div>
                        </div>""", unsafe_allow_html=True)
        else:
            st.caption("Debug info appears after first message.")

    with tab3:
        if st.session_state.messages:
            log = {
                "config": sess.config.model_dump(),
                "final_phase": sess.current_phase,
                "final_mastery": round(sess.mastery_level,3),
                "turns": st.session_state.turn_count,
                "signal_scorecard": sess.scorecard.to_dict(),
                "conversation":[{"role":m["role"],"content":m["content"]} for m in st.session_state.messages],
            }
            st.json(log)
            if st.button("💾 Save Log"):
                try:
                    sess.save_log()
                    st.success("Saved to logs/conversations.json")
                except Exception as e:
                    st.error(f"Save failed: {e}")
        else:
            st.caption("Session log appears after first message.")


if st.session_state.panel_open:
    with col_chat:
        render_chat()
else:
    render_chat()

