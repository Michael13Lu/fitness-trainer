import sqlite3
import json
from config import DB_PATH


def init_db():
    """Создаёт все таблицы при первом запуске (идемпотентно)."""
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_prefs (
                user_name TEXT PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'Русский',
                profile TEXT
            )
        """)


# Инициализируем БД один раз при импорте модуля
init_db()


def load_messages(user_name: str) -> list:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE user_name = ? ORDER BY id",
            (user_name,)
        ).fetchall()
    return [{"role": r[0], "content": r[1]} for r in rows]


def save_message(user_name: str, role: str, content: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO messages (user_name, role, content) VALUES (?, ?, ?)",
            (user_name, role, content)
        )


def clear_history(user_name: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM messages WHERE user_name = ?", (user_name,))


def save_profile(user_name: str, profile: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO user_prefs (user_name, language, profile) VALUES (?, '', ?)
            ON CONFLICT(user_name) DO UPDATE SET profile = excluded.profile
        """, (user_name, json.dumps(profile, ensure_ascii=False)))


def load_profile(user_name: str) -> dict | None:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT profile FROM user_prefs WHERE user_name = ?", (user_name,)
            ).fetchone()
        if row and row[0]:
            return json.loads(row[0])
    except Exception:
        pass
    return None


def save_language(user_name: str, lang_name: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO user_prefs (user_name, language) VALUES (?, ?)
            ON CONFLICT(user_name) DO UPDATE SET language = excluded.language
        """, (user_name, lang_name))


def load_language(user_name: str, default: str = "Русский") -> str:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT language FROM user_prefs WHERE user_name = ?", (user_name,)
            ).fetchone()
        return row[0] if row else default
    except Exception:
        return default
