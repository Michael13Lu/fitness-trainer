import sqlite3
from config import DB_PATH


def _init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS training_programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                title TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS program_days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_id INTEGER NOT NULL,
                day_label TEXT NOT NULL,
                exercises TEXT NOT NULL,
                notes TEXT DEFAULT '',
                FOREIGN KEY (program_id) REFERENCES training_programs(id)
            )
        """)


# Инициализируем БД один раз при импорте модуля
_init_db()


def save_program(user_name: str, title: str, raw_text: str) -> int:
    """Save new program, deactivate previous ones. Returns new program id."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE training_programs SET is_active=0 WHERE user_name=?",
            (user_name,)
        )
        cur = conn.execute(
            "INSERT INTO training_programs (user_name, title, raw_text) VALUES (?,?,?)",
            (user_name, title, raw_text)
        )
        return cur.lastrowid


def update_program_text(program_id: int, raw_text: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE training_programs SET raw_text=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (raw_text, program_id)
        )


def get_active_program(user_name: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("""
            SELECT id, title, raw_text, created_at, updated_at
            FROM training_programs
            WHERE user_name=? AND is_active=1
            ORDER BY id DESC LIMIT 1
        """, (user_name,)).fetchone()
    if not row:
        return None
    return {"id": row[0], "title": row[1], "raw_text": row[2],
            "created_at": row[3], "updated_at": row[4]}


def get_all_programs(user_name: str) -> list:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT id, title, created_at, is_active
            FROM training_programs WHERE user_name=?
            ORDER BY id DESC LIMIT 10
        """, (user_name,)).fetchall()
    return [{"id": r[0], "title": r[1], "created_at": r[2], "is_active": r[3]}
            for r in rows]


def activate_program(user_name: str, program_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE training_programs SET is_active=0 WHERE user_name=?",
            (user_name,)
        )
        conn.execute(
            "UPDATE training_programs SET is_active=1 WHERE id=? AND user_name=?",
            (program_id, user_name)
        )
