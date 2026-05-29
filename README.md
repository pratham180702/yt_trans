# YouTube RAG Chatbot

A Retrieval-Augmented Generation (RAG) application that lets you have a conversation with any YouTube video. Paste a YouTube URL, and the system fetches the transcript, indexes it in Pinecone, and lets you ask questions answered by the video content.

---

## Architecture Overview

```
frontend.py  (Streamlit)
     |
     | HTTP
     v
main.py  (FastAPI backend)
     |
     |-- database.py  (SQLite — stores bots & chat history)
     |-- utils/rag.py (transcript fetch, Pinecone indexing, RAG chain)
```

- **Backend**: FastAPI serving two endpoints — `/create-bot` and `/chat`
- **Frontend**: Streamlit UI that talks to the backend over HTTP
- **Vector Store**: Pinecone (Serverless, AWS us-east-1)
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` via HuggingFace Inference API
- **LLM**: `llama-3.3-70b-versatile` via Groq
- **Database**: SQLite (`youtube_rag.db`) for persisting bot metadata and chat history

---

## Prerequisites

Before you begin, make sure you have the following installed and available:

- Python 3.10 or higher
- `pip` (comes with Python)
- Git (optional, for cloning)
- Internet access (for API calls to Groq, Pinecone, and HuggingFace)

---

## Step 1 — Clone the Repository

```bash
git clone <your-repo-url>
cd yt_transcription
```

If you already have the project folder locally, navigate into it:

```bash
cd path/to/yt_transcription
```

---

## Step 2 — Create a Virtual Environment

It is strongly recommended to use a virtual environment to avoid dependency conflicts.

**On Windows:**

```bash
python -m venv yt_trans_env
yt_trans_env\Scripts\activate
```

**On macOS / Linux:**

```bash
python -m venv yt_trans_env
source yt_trans_env/bin/activate
```

You should see `(yt_trans_env)` at the beginning of your terminal prompt after activation.

---

## Step 3 — Install Dependencies

With the virtual environment active, install all required packages:

```bash
pip install -r requirements.txt
```

> Note: Installing `torch` and `sentence-transformers` can take a few minutes depending on your internet speed. This is expected.

---

## Step 4 — Obtain API Keys

This project requires four API keys. Follow the instructions below to get each one.

### Groq API Key

1. Go to [https://console.groq.com](https://console.groq.com) and create a free account.
2. Navigate to **API Keys** in the left sidebar.
3. Click **Create API Key** and copy it.

### Pinecone API Key

1. Go to [https://www.pinecone.io](https://www.pinecone.io) and sign up for a free account.
2. From the dashboard, click **API Keys** in the left panel.
3. Copy the default API key or create a new one.

> Note: The free Starter plan allows a maximum of 5 indexes. The application automatically manages this limit by deleting the oldest index when the cap is reached.

### HuggingFace API Key

1. Go to [https://huggingface.co](https://huggingface.co) and create a free account.
2. Go to your **Profile > Settings > Access Tokens**.
3. Click **New Token**, choose a name, set the role to **Read**, and copy the token.

### Tavily API Key (optional)

> Tavily is referenced in the `.env` template but is not currently used by the core application. You may leave this blank or skip it.

1. Go to [https://tavily.com](https://tavily.com) and sign up.
2. Copy your API key from the dashboard.

---

## Step 5 — Configure Environment Variables

Create a `.env` file in the root of the project directory:

```bash
# On Windows
copy NUL .env

# On macOS / Linux
touch .env
```

Open the `.env` file and add the following content, replacing the placeholder values with your actual API keys:

```
GROQ_API_KEY=your_groq_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
HUGGINGFACE_API_KEY=your_huggingface_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

> The `.env` file is listed in `.gitignore` and will not be committed to version control.

---

## Step 6 — Run the Backend (FastAPI)

Open a terminal, activate the virtual environment, and start the FastAPI server:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

You should see output similar to:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

The backend will also automatically create the SQLite database (`youtube_rag.db`) and the required tables on first run.

You can verify the API is running by visiting [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in your browser to see the interactive Swagger UI.

---

## Step 7 — Run the Frontend (Streamlit)

Open a **second terminal**, activate the same virtual environment, and run:

```bash
streamlit run frontend.py
```

Streamlit will automatically open the app in your default browser at [http://localhost:8501](http://localhost:8501).

---

## Step 8 — Using the Application

1. Paste a valid YouTube URL into the input field. The video must have English captions or a transcript available.
2. Click **Create Bot**.
3. The backend will fetch the video transcript, split it into chunks, generate embeddings, and upload them to Pinecone. This can take 15-60 seconds depending on video length.
4. Once the bot is ready, a status badge will confirm it.
5. Type your question in the chat input at the bottom and press Enter.
6. The assistant will answer using only the content from the video, and will mention timestamps where relevant.

---

## API Reference

The backend exposes two endpoints:

### POST /create-bot

Creates a new bot for a given YouTube video. Fetches the transcript and indexes it in Pinecone.

**Request body:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Response:**
```json
{
  "message": "Bot created successfully",
  "bot_id": 1,
  "video_id": "VIDEO_ID"
}
```

### POST /chat

Sends a question to an existing bot and returns an answer grounded in the video content.

**Request body:**
```json
{
  "bot_id": 1,
  "question": "What does the video say about X?"
}
```

**Response:**
```json
{
  "answer": "According to the video at timestamp 120s, ..."
}
```

---

## Project Structure

```
yt_transcription/
├── main.py              # FastAPI application — API routes
├── frontend.py          # Streamlit UI
├── database.py          # SQLite helpers (bots, chat messages)
├── utils/
│   ├── rag.py           # Transcript fetch, Pinecone indexing, RAG chain
│   └── youtube_cookies.txt  # (Optional) cookies for restricted videos
├── requirements.txt     # Python dependencies
├── .env                 # API keys (not committed)
├── .gitignore
└── youtube_rag.db       # SQLite database (auto-created on first run)
```

---

## Troubleshooting

**"Cannot connect to backend"**
- Make sure the FastAPI server is running in a separate terminal on port 8000.
- Check that your virtual environment is activated in both terminals.

**"Invalid YouTube URL"**
- Ensure the URL is in the format `https://www.youtube.com/watch?v=VIDEO_ID` or `https://youtu.be/VIDEO_ID`.
- The video must be publicly accessible.

**"Transcript not available"**
- The video must have English captions (auto-generated or manually added). Videos without captions cannot be processed.

**Pinecone index limit reached**
- The free Pinecone plan supports up to 5 indexes. The application handles this automatically by deleting the oldest index. If you see errors, log into Pinecone and verify your index count.

**Slow first-time setup**
- The first request after starting the server may be slow because the HuggingFace embedding model needs to be loaded. Subsequent requests will be faster.

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | API key for the Groq LLM inference service |
| `PINECONE_API_KEY` | Yes | API key for the Pinecone vector database |
| `HUGGINGFACE_API_KEY` | Yes | HuggingFace token for the embedding model inference API |
| `TAVILY_API_KEY` | No | Tavily search API key (not used in current version) |
