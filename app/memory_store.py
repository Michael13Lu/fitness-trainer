import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "chat_history.db")


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def load_messages(user_name: str) -> list:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE user_name = ? ORDER BY id",
            (user_name,)
        ).fetchall()
    return [{"role": r[0], "content": r[1]} for r in rows]


def save_message(user_name: str, role: str, content: str):
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO messages (user_name, role, content) VALUES (?, ?, ?)",
            (user_name, role, content)
        )


def clear_history(user_name: str):
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM messages WHERE user_name = ?", (user_name,))
