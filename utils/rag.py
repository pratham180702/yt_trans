from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import *
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_core.documents import Document
from dotenv import load_dotenv
load_dotenv()
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from urllib.parse import urlparse, parse_qs
import os
import time

INDEX_PREFIX = "youtube-rag-index"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def get_youtube_video_id(url):
    parsed_url = urlparse(url)

    # Normal YouTube URL
    if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed_url.query).get("v", [None])[0]

    # Shortened youtu.be URL
    if parsed_url.hostname == "youtu.be":
        return parsed_url.path.lstrip("/")

    return None


def get_youtube_video_id(url):
    parsed_url = urlparse(url)

    if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed_url.query).get("v", [None])[0]

    if parsed_url.hostname == "youtu.be":
        return parsed_url.path.lstrip("/")

    return None


def fetch_transcript(video_id):
    ytt_api = YouTubeTranscriptApi()
    return ytt_api.fetch(video_id, languages=["en-IN", "en", "hi"])


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
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL
    )


def get_pinecone_client():
    return Pinecone(
        api_key=os.getenv("PINECONE_API_KEY")
    )


def get_index_name(video_id):
    return f"{INDEX_PREFIX}-{video_id.lower()}"


def create_index_if_not_exists(pc, index_name):
    existing_indexes = pc.list_indexes().names()

    if index_name not in existing_indexes:
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )

        time.sleep(10)
        return True

    return False


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

    is_new_index = create_index_if_not_exists(pc, index_name)

    vectorstore = get_vectorstore(index_name, embeddings)

    if is_new_index:
        vectorstore.add_documents(docs)

    return {
        "video_id": video_id,
        "index_name": index_name,
        "status": "created" if is_new_index else "already_exists"
    }


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


def get_prompt():
    return PromptTemplate(
        template="""
You are a helpful YouTube video assistant.

Review the provided context, which contains timestamp in seconds and transcript content.

Rules:
1. Keep your tone natural and friendly.
2. Do not show unnecessary technical details.
3. Keep the answer precise and friendly.
4. If the answer is not present in the context, simply say: "I don't know".
5. For each important point, mention which timestamp/content supports your answer.
6. Give short answers unless details are required.

User Query: {user_query}

Context:
{context}
""",
        input_variables=["user_query", "context"]
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
            "context": retriever | format_docs,
            "user_query": RunnablePassthrough()
        }
        | prompt
        | llm
        | parser
    )

    return rag_chain


def make_yt_video_rag(url):
    result = ingest_youtube_video(url)
    return get_rag_chain(result["video_id"])