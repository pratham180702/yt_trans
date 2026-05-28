# database.py

import sqlite3

DB_NAME = "youtube_rag.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        youtube_url TEXT NOT NULL,
        video_id TEXT NOT NULL UNIQUE,
        pinecone_namespace TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def insert_bot(youtube_url, video_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO bots (youtube_url, video_id, pinecone_namespace)
    VALUES (?, ?, ?)
    """, (youtube_url, video_id, video_id))

    conn.commit()

    cursor.execute("SELECT id, youtube_url, video_id, pinecone_namespace FROM bots WHERE video_id = ?", (video_id,))
    bot = cursor.fetchone()

    conn.close()
    return bot


def get_chat_messages(bot_id, limit=10):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT role, content
    FROM chat_messages
    WHERE bot_id = ?
    ORDER BY created_at DESC
    LIMIT ?
    """, (bot_id, limit))

    messages = cursor.fetchall()
    conn.close()

    return list(reversed(messages))

def get_bot_by_id(bot_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, youtube_url, video_id, pinecone_namespace FROM bots WHERE id = ?", (bot_id,))
    bot = cursor.fetchone()

    conn.close()
    return bot


def save_chat_message(bot_id, role, content):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO chat_messages (bot_id, role, content)
    VALUES (?, ?, ?)
    """, (bot_id, role, content))

    conn.commit()
    conn.close()