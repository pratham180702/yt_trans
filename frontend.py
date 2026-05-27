# frontend.py

import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="YouTube Chat Bot", page_icon="🎥")

st.title("YouTube RAG Chatbot")

youtube_url = st.text_input("Enter YouTube URL")

if "bot_id" not in st.session_state:
    st.session_state.bot_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if st.button("Create Bot"):
    response = requests.post(
        f"{API_URL}/create-bot",
        json={"youtube_url": youtube_url}
    )

    st.write("Status code:", response.status_code)
    st.write("Raw response:", response.text)

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError:
        st.error("Backend did not return JSON")
        st.stop()

    data = response.json()

    if "bot_id" in data:
        st.session_state.bot_id = data["bot_id"]
        st.success("Bot created successfully!")
    else:
        st.error(data.get("error", "Something went wrong"))

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if st.session_state.bot_id:
    user_question = st.chat_input("Ask something from this video...")

    if user_question:
        st.session_state.messages.append({
            "role": "user",
            "content": user_question
        })

        with st.chat_message("user"):
            st.write(user_question)

        response = requests.post(
            f"{API_URL}/chat",
            json={
                "bot_id": st.session_state.bot_id,
                "question": user_question
            }
        )

        answer = response.json()["answer"]

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })

        with st.chat_message("assistant"):
            st.write(answer)