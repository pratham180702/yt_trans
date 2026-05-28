from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import *
from langchain_core.documents import Document
from dotenv import load_dotenv
load_dotenv()
from langchain_huggingface import HuggingFaceEndpointEmbeddings
# from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from urllib.parse import urlparse, parse_qs
import os
import time
import logging
import yt_dlp

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

INDEX_PREFIX = "youtube-rag-index"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def get_youtube_video_id(url):
    parsed_url = urlparse(url)

    if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed_url.query).get("v", [None])[0]

    if parsed_url.hostname == "youtu.be":
        return parsed_url.path.lstrip("/")

    return None


class _Snippet:
    """Duck-typed snippet compatible with transcript_to_docs."""
    def __init__(self, text, start):
        self.text = text
        self.start = start


class _FetchedTranscript:
    """Duck-typed transcript compatible with transcript_to_docs."""
    def __init__(self, snippets):
        self.snippets = snippets


def fetch_transcript(video_id):
    """Fetch transcript using yt-dlp with tv_embedded client (no PO token needed)."""
    url = f"https://www.youtube.com/watch?v={video_id}"

    cookies_path = os.environ.get(
        "YOUTUBE_COOKIES_PATH",
        os.path.join(os.path.dirname(__file__), "youtube_cookies.txt")
    )

    logger.info(f"[fetch_transcript] video_id={video_id}")
    logger.info(f"[fetch_transcript] cookies file exists: {os.path.exists(cookies_path)}")

    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["all"],
        "subtitlesformat": "json3",
        "quiet": True,
        "no_warnings": False,
        "ignore_no_formats_error": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["tv_embedded"]
            }
        },
    }

    if os.path.exists(cookies_path):
        ydl_opts["cookiefile"] = cookies_path
        logger.info(f"[fetch_transcript] using cookiefile")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    subtitles = info.get("subtitles") or {}
    auto_subs = info.get("automatic_captions") or {}

    logger.info(f"[fetch_transcript] manual subtitle langs: {list(subtitles.keys())[:10]}")
    logger.info(f"[fetch_transcript] auto-caption langs (first 10): {list(auto_subs.keys())[:10]}")

    # Preferred language prefixes in order (handles codes like en-en-IN, hi-en-IN)
    preferred_prefixes = ["en-IN", "en", "hi", "en-in"]

    raw_entries = None
    matched_lang = None

    # Check manual subtitles first, then auto-captions
    for source in [subtitles, auto_subs]:
        for prefix in preferred_prefixes:
            # Exact match first
            if prefix in source:
                raw_entries = source[prefix]
                matched_lang = prefix
                break
            # Prefix match (e.g. "en" matches "en-en-IN")
            for lang_code in source:
                if lang_code.startswith(prefix):
                    raw_entries = source[lang_code]
                    matched_lang = lang_code
                    break
            if raw_entries:
                break
        if raw_entries:
            break

    if not raw_entries:
        available = list(subtitles.keys()) + list(auto_subs.keys())
        raise ValueError(f"No en/hi transcript found for video {video_id}. Available: {available[:20]}")

    logger.info(f"[fetch_transcript] using lang: {matched_lang}")

    # Pick json3 format
    json3_entry = next(
        (e for e in raw_entries if e.get("ext") == "json3"),
        raw_entries[0]
    )

    import urllib.request, json
    with urllib.request.urlopen(json3_entry["url"]) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    snippets = []
    for event in data.get("events", []):
        start_sec = round(event.get("tStartMs", 0) / 1000, 2)
        text = "".join(seg.get("utf8", "") for seg in event.get("segs", [])).strip()
        if text and text != "\n":
            snippets.append(_Snippet(text=text, start=start_sec))

    logger.info(f"[fetch_transcript] extracted {len(snippets)} snippets")
    return _FetchedTranscript(snippets=snippets)



def transcript_to_docs(transcription, video_id, chunk_size=500):
    docs = []

    current_chunk = ""
    current_start_time = None

    for snippet in transcription.snippets:
        text = snippet.text.strip()

        if not text:
            continue

        if current_start_time is None:
            current_start_time = snippet.start

        line = f"TimeStamp(sec): {snippet.start}, Content: {text}\n"

        if len(current_chunk) + len(line) <= chunk_size:
            current_chunk += line
        else:
            docs.append(
                Document(
                    page_content=current_chunk.strip(),
                    metadata={
                        "source": "youtube",
                        "video_id": video_id,
                        "start_time": current_start_time
                    }
                )
            )

            current_chunk = line
            current_start_time = snippet.start

    if current_chunk:
        docs.append(
            Document(
                page_content=current_chunk.strip(),
                metadata={
                    "source": "youtube",
                    "video_id": video_id,
                    "start_time": current_start_time
                }
            )
        )

    return docs


def get_embeddings():
    return HuggingFaceEndpointEmbeddings(
        model="sentence-transformers/all-MiniLM-L6-v2",
        huggingfacehub_api_token=os.getenv("HUGGINGFACE_API_KEY")
    )


def get_pinecone_client():
    return Pinecone(
        api_key=os.getenv("PINECONE_API_KEY")
    )


def get_index_name(video_id):
    return f"{INDEX_PREFIX}-{video_id.lower()}"


def create_index_if_not_exists(pc, index_name):
    # Get the current list of indexes
    indexes_info = pc.list_indexes()
    existing_indexes = [idx.name for idx in indexes_info]

    # If the index we want already exists, we are done
    if index_name in existing_indexes:
        logger.info(f"Index {index_name} already exists.")
        return False

    # Check if we have reached the limit (5 for Starter/Default projects)
    if len(existing_indexes) >= 5:
        # Sort or just pick the first one to delete. 
        # Pinecone list usually returns them in a stable order.
        oldest_index_name = existing_indexes[0]
        
        logger.warning(f"Index limit (5) reached. Deleting oldest index: {oldest_index_name}")
        pc.delete_index(oldest_index_name)
        
        # Wait a few seconds for Pinecone to register the deletion
        time.sleep(5)

    # Create the new index
    logger.info(f"Creating new index: {index_name}")
    pc.create_index(
        name=index_name,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

    # Give Pinecone time to initialize the DNS/DNS for the new index
    time.sleep(10)
    return True


def get_vectorstore(index_name, embeddings):
    return PineconeVectorStore(
        index_name=index_name,
        embedding=embeddings
    )


def ingest_youtube_video(url):
    if not url:
        raise ValueError("YouTube URL is required")

    video_id = get_youtube_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")

    transcription = fetch_transcript(video_id)
    docs = transcript_to_docs(transcription, video_id)

    embeddings = get_embeddings()
    pc = get_pinecone_client()
    index_name = get_index_name(video_id)

    # Ensure index exists
    create_index_if_not_exists(pc, index_name)

    vectorstore = get_vectorstore(index_name, embeddings)

    # CHECK: Does the index actually have data?
    index_stats = pc.Index(index_name).describe_index_stats()
    if index_stats['total_vector_count'] == 0:
        logger.info(f"Index {index_name} is empty. Ingesting {len(docs)} documents...")
        vectorstore.add_documents(docs)
    else:
        logger.info(f"Index {index_name} already contains data. Skipping ingestion.")

    return {
        "video_id": video_id,
        "index_name": index_name,
        "status": "processed"
    }

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def get_prompt():
    return PromptTemplate(
        template="""
You are a helpful YouTube video assistant.

Previous conversation:
{chat_history}

Video context:
{context}

User Query: {user_query}

Rules:
1. Answer using video context.
2. Use previous conversation only to understand follow-up questions.
3. If answer is not in video context, say "I don't know".
4. Mention timestamps when useful.
""",
        input_variables=["user_query", "context", "chat_history"]
    )


def get_rag_chain(video_id):
    index_name = get_index_name(video_id)

    embeddings = get_embeddings()
    vectorstore = get_vectorstore(index_name, embeddings)

    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 10}
    )

    prompt = get_prompt()

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0
    )

    parser = StrOutputParser()

    rag_chain = (
        {
            "context": lambda x: format_docs(
                retriever.invoke(x["user_query"])
            ),
            "user_query": lambda x: x["user_query"],
            "chat_history": lambda x: x["chat_history"]
        }
        | prompt
        | llm
        | parser
    )

    return rag_chain


def make_yt_video_rag(url):
    result = ingest_youtube_video(url)
    return get_rag_chain(result["video_id"])