import sqlite3
import os
from datetime import date

DB_PATH = os.path.join(os.path.dirname(__file__), "chat_history.db")


def init_workout_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                workout_date TEXT NOT NULL,
                exercise TEXT NOT NULL,
                muscle_group TEXT NOT NULL,
                sets INTEGER,
                reps INTEGER,
                weight_kg REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def add_exercise(user_name: str, workout_date: str, exercise: str,
                 muscle_group: str, sets: int, reps: int, weight_kg: float, notes: str = ""):
    init_workout_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO workouts (user_name, workout_date, exercise, muscle_group, sets, reps, weight_kg, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_name, workout_date, exercise, muscle_group, sets, reps, weight_kg, notes))


def get_workouts(user_name: str, limit: int = 100) -> list:
    init_workout_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT workout_date, exercise, muscle_group, sets, reps, weight_kg, notes
            FROM workouts WHERE user_name = ?
            ORDER BY workout_date DESC, id DESC
            LIMIT ?
        """, (user_name, limit)).fetchall()
    return [
        {"date": r[0], "exercise": r[1], "muscle_group": r[2],
         "sets": r[3], "reps": r[4], "weight": r[5], "notes": r[6]}
        for r in rows
    ]


def get_exercise_history(user_name: str, exercise: str) -> list:
    """История конкретного упражнения для анализа прогресса."""
    init_workout_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT workout_date, sets, reps, weight_kg
            FROM workouts WHERE user_name = ? AND exercise = ?
            ORDER BY workout_date ASC
        """, (user_name, exercise)).fetchall()
    return [{"date": r[0], "sets": r[1], "reps": r[2], "weight": r[3]} for r in rows]


def get_muscle_summary(user_name: str) -> str:
    """Сводка по группам мышц для анализа."""
    init_workout_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT muscle_group, COUNT(*) as sessions,
                   MAX(weight_kg) as max_weight,
                   MAX(workout_date) as last_trained
            FROM workouts WHERE user_name = ?
            GROUP BY muscle_group
            ORDER BY last_trained DESC
        """, (user_name,)).fetchall()
    if not rows:
        return "Тренировок ещё нет."
    lines = ["Группа мышц | Сессий | Макс. вес | Последняя тренировка"]
    for r in rows:
        lines.append(f"{r[0]} | {r[1]} | {r[2]} кг | {r[3]}")
    return "\n".join(lines)


def get_workouts_as_text(user_name: str, limit: int = 50) -> str:
    """Форматированный текст тренировок для отправки в LLM."""
    workouts = get_workouts(user_name, limit)
    if not workouts:
        return "Дневник тренировок пуст."
    lines = []
    for w in workouts:
        lines.append(
            f"{w['date']} | {w['exercise']} ({w['muscle_group']}) | "
            f"{w['sets']}x{w['reps']} @ {w['weight']} кг"
            + (f" | {w['notes']}" if w['notes'] else "")
        )
    return "\n".join(lines)


def get_workouts_by_date(user_name: str, workout_date: str) -> list:
    """Все упражнения за конкретную дату."""
    init_workout_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT exercise, muscle_group, sets, reps, weight_kg, notes
            FROM workouts WHERE user_name = ? AND workout_date = ?
            ORDER BY id ASC
        """, (user_name, workout_date)).fetchall()
    return [{"exercise": r[0], "muscle_group": r[1],
             "sets": r[2], "reps": r[3], "weight": r[4], "notes": r[5]}
            for r in rows]


def delete_last_exercise(user_name: str):
    init_workout_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            DELETE FROM workouts WHERE id = (
                SELECT id FROM workouts WHERE user_name = ? ORDER BY id DESC LIMIT 1
            )
        """, (user_name,))
