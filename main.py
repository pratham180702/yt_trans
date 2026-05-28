# main.py

from fastapi import FastAPI
from pydantic import BaseModel

from database import create_tables, insert_bot, get_bot_by_id, save_chat_message, get_chat_messages
from utils.rag import get_youtube_video_id, make_yt_video_rag

app = FastAPI()

create_tables()


class CreateBotRequest(BaseModel):
    youtube_url: str


class ChatRequest(BaseModel):
    bot_id: int
    question: str


@app.post("/create-bot")
def create_bot(request: CreateBotRequest):
    video_id = get_youtube_video_id(request.youtube_url)

    if not video_id:
        return {"error": "Invalid YouTube URL"}

    rag_chain = make_yt_video_rag(request.youtube_url)

    bot = insert_bot(request.youtube_url, video_id)

    return {
        "message": "Bot created successfully",
        "bot_id": bot[0],
        "video_id": video_id
    }


def get_chat_history(bot_id, limit=10):
    messages = get_chat_messages(bot_id, limit=limit)

    history = []

    for msg in messages:
        role = msg["role"]          # user / assistant
        content = msg["content"]

        if role == "user":
            history.append(f"User: {content}")
        elif role == "assistant":
            history.append(f"Assistant: {content}")

    return "\n".join(history)


@app.post("/chat")
def chat(request: ChatRequest):
    bot = get_bot_by_id(request.bot_id)

    if not bot:
        return {"error": "Bot not found"}

    youtube_url = bot[1]

    rag_chain = make_yt_video_rag(youtube_url)

    chat_history = get_chat_history(request.bot_id, limit=10)

    answer = rag_chain.invoke({
        "user_query": request.question,
        "chat_history": chat_history
    })

    save_chat_message(request.bot_id, "user", request.question)
    save_chat_message(request.bot_id, "assistant", answer)

    return {
        "answer": answer
    }