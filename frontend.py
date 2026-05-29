# frontend.py

import os
import streamlit as st
import requests

API_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Your Personal YouTube Bot",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Global CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Base */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 860px; }

/* ── Hero header ── */
.hero {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
    margin-bottom: 1.5rem;
}
.hero h1 {
    font-size: 2.6rem;
    font-weight: 700;
    background: linear-gradient(90deg, #ff6b6b, #feca57, #48dbfb, #ff9ff3);
    background-size: 300% 300%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: gradientShift 4s ease infinite;
    margin: 0 0 0.4rem;
}
.hero p {
    color: rgba(255,255,255,0.55);
    font-size: 1rem;
    margin: 0;
}
@keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* ── Glass card ── */
.glass-card {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    padding: 1.6rem;
    backdrop-filter: blur(12px);
    margin-bottom: 1.2rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}

/* ── Status badge ── */
.badge-ready {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(72, 219, 130, 0.15);
    border: 1px solid rgba(72, 219, 130, 0.4);
    color: #48db82;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.82rem;
    font-weight: 600;
    margin-top: 0.5rem;
}
.badge-idle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(254, 202, 87, 0.12);
    border: 1px solid rgba(254, 202, 87, 0.35);
    color: #feca57;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.82rem;
    font-weight: 600;
    margin-top: 0.5rem;
}

/* ── URL input ── */
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 10px !important;
    color: white !important;
    font-size: 0.95rem !important;
    padding: 0.65rem 1rem !important;
}
.stTextInput > div > div > input::placeholder { color: rgba(255,255,255,0.35) !important; }
.stTextInput > div > div > input:focus {
    border-color: rgba(255, 107, 107, 0.6) !important;
    box-shadow: 0 0 0 3px rgba(255,107,107,0.12) !important;
}
.stTextInput label { color: rgba(255,255,255,0.7) !important; font-size: 0.88rem !important; }

/* ── Button ── */
.stButton > button {
    background: linear-gradient(135deg, #ff6b6b, #ee5a24) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.8rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(255, 107, 107, 0.35) !important;
    width: 100%;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(255,107,107,0.5) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 14px !important;
    margin-bottom: 0.6rem !important;
    padding: 0.8rem 1rem !important;
}
[data-testid="stChatMessage"] p { color: rgba(255,255,255,0.88) !important; }

/* ── Chat input ── */
[data-testid="stChatInput"] textarea {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 12px !important;
    color: white !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: rgba(255,255,255,0.35) !important; }

/* ── Divider ── */
hr { border-color: rgba(255,255,255,0.1) !important; margin: 1rem 0 !important; }

/* ── Alert overrides ── */
.stAlert { border-radius: 10px !important; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: #ff6b6b !important; }

/* ── Video info row ── */
.video-info {
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(255,107,107,0.08);
    border: 1px solid rgba(255,107,107,0.2);
    border-radius: 10px;
    padding: 10px 14px;
    margin-top: 0.8rem;
    font-size: 0.88rem;
    color: rgba(255,255,255,0.75);
    word-break: break-all;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────────────────────────
if "bot_id" not in st.session_state:
    st.session_state.bot_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "video_url" not in st.session_state:
    st.session_state.video_url = ""

# ── Hero ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🎬 Your Personal YouTube Bot</h1>
    <p>Paste any YouTube link and start chatting with the video</p>
</div>
""", unsafe_allow_html=True)

# ── Setup card ───────────────────────────────────────────────────────────────
st.markdown('<div class="glass-card">', unsafe_allow_html=True)

col_label, col_status = st.columns([3, 1])
with col_label:
    st.markdown("#### 📎 Video Setup")
with col_status:
    if st.session_state.bot_id:
        st.markdown('<div class="badge-ready">● Bot Ready</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="badge-idle">○ Not configured</div>', unsafe_allow_html=True)

youtube_url = st.text_input(
    "YouTube URL",
    placeholder="https://www.youtube.com/watch?v=...",
    label_visibility="collapsed"
)

if youtube_url:
    st.markdown(f'<div class="video-info">🔗 &nbsp;{youtube_url}</div>', unsafe_allow_html=True)

col_btn, col_reset = st.columns([3, 1])
with col_btn:
    create_clicked = st.button("⚡ Create Bot", use_container_width=True)
with col_reset:
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.bot_id = None
        st.session_state.messages = []
        st.session_state.video_url = ""
        st.rerun()

if create_clicked:
    if not youtube_url.strip():
        st.error("Please enter a YouTube URL first.")
    else:
        with st.spinner("Processing video transcript and building knowledge base..."):
            try:
                response = requests.post(
                    f"{API_URL}/create-bot",
                    json={"youtube_url": youtube_url},
                    timeout=120
                )
                data = response.json()
            except requests.exceptions.JSONDecodeError:
                st.error("Backend returned an unexpected response. Check if the server is running.")
                data = {}
            except requests.exceptions.ConnectionError:
                st.error(f"Cannot connect to backend at `{API_URL}`. Is the server running?")
                data = {}

        if "bot_id" in data:
            st.session_state.bot_id = data["bot_id"]
            st.session_state.video_url = youtube_url
            st.session_state.messages = []
            st.success("✅ Bot is ready! Start asking questions below.")
            st.rerun()
        elif data:
            st.error(f"❌ {data.get('error', 'Something went wrong')}")

st.markdown('</div>', unsafe_allow_html=True)

# ── Chat area ────────────────────────────────────────────────────────────────
if st.session_state.bot_id:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("#### 💬 Chat with the Video")

    if st.session_state.video_url:
        vid_id = st.session_state.video_url.split("v=")[-1].split("&")[0] if "v=" in st.session_state.video_url else ""
        if vid_id:
            st.markdown(
                f'<a href="{st.session_state.video_url}" target="_blank" style="color:#ff6b6b;font-size:0.82rem;text-decoration:none;">▶ {st.session_state.video_url}</a>',
                unsafe_allow_html=True
            )

    st.markdown("<hr>", unsafe_allow_html=True)

    # Render history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    st.markdown('</div>', unsafe_allow_html=True)

    # Chat input (outside card so it pins to bottom)
    user_question = st.chat_input("Ask something about this video...")

    if user_question:
        st.session_state.messages.append({"role": "user", "content": user_question})

        with st.chat_message("user"):
            st.write(user_question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        f"{API_URL}/chat",
                        json={
                            "bot_id": st.session_state.bot_id,
                            "question": user_question
                        },
                        timeout=60
                    )
                    answer = response.json().get("answer", "Sorry, I couldn't get an answer.")
                except Exception as e:
                    answer = f"Error: {e}"

            st.write(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})

else:
    # Empty state illustration
    st.markdown("""
    <div style="text-align:center; padding: 3rem 1rem; color: rgba(255,255,255,0.3);">
        <div style="font-size: 3.5rem; margin-bottom: 1rem;">🎥</div>
        <div style="font-size: 1rem; font-weight: 500;">Paste a YouTube URL above and click <b style="color:rgba(255,255,255,0.5)">Create Bot</b> to begin</div>
    </div>
    """, unsafe_allow_html=True)