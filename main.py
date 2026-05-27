# main.py

from fastapi import FastAPI
from pydantic import BaseModel

from database import create_tables, insert_bot, get_bot_by_id, save_chat_message
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


@app.post("/chat")
def chat(request: ChatRequest):
    bot = get_bot_by_id(request.bot_id)

    if not bot:
        return {"error": "Bot not found"}

    youtube_url = bot[1]

    rag_chain = make_yt_video_rag(youtube_url)

    answer = rag_chain.invoke(request.question)

    save_chat_message(request.bot_id, "user", request.question)
    save_chat_message(request.bot_id, "assistant", answer)

    return {
        "answer": answer
    }