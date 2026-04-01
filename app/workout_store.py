import sqlite3
import os
from datetime import date  # noqa

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
        # Доп. поля — добавляем если ещё нет
        for col, typedef in [
            ("cardio_type", "TEXT"),
            ("duration_min", "INTEGER"),
            ("distance_km", "REAL"),
            ("avg_hr", "INTEGER"),
            ("workout_start", "TEXT"),
            ("workout_end", "TEXT"),
            ("rest_sec", "INTEGER"),
        ]:
            try:
                conn.execute(f"ALTER TABLE workouts ADD COLUMN {col} {typedef}")
            except sqlite3.OperationalError:
                pass  # уже существует


def add_exercise(user_name: str, workout_date: str, exercise: str,
                 muscle_group: str, sets: int = 0, reps: int = 0, weight_kg: float = 0.0,
                 notes: str = "", cardio_type: str = "", duration_min: int = 0,
                 distance_km: float = 0.0, avg_hr: int = 0,
                 workout_start: str = "", workout_end: str = "", rest_sec: int = 0):
    init_workout_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO workouts
              (user_name, workout_date, exercise, muscle_group, sets, reps, weight_kg,
               notes, cardio_type, duration_min, distance_km, avg_hr,
               workout_start, workout_end, rest_sec)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_name, workout_date, exercise, muscle_group, sets, reps, weight_kg,
              notes, cardio_type, duration_min, distance_km, avg_hr,
              workout_start, workout_end, rest_sec))


def get_workouts(user_name: str, limit: int = 100) -> list:
    init_workout_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT id, workout_date, exercise, muscle_group, sets, reps, weight_kg, notes,
                   cardio_type, duration_min, distance_km, avg_hr
            FROM workouts WHERE user_name = ?
            ORDER BY workout_date DESC, id DESC
            LIMIT ?
        """, (user_name, limit)).fetchall()
    return [
        {"id": r[0], "date": r[1], "exercise": r[2], "muscle_group": r[3],
         "sets": r[4], "reps": r[5], "weight": r[6], "notes": r[7],
         "cardio_type": r[8] or "", "duration_min": r[9] or 0,
         "distance_km": r[10] or 0.0, "avg_hr": r[11] or 0}
        for r in rows
    ]


def update_exercise(row_id: int, exercise: str, muscle_group: str,
                    sets: int, reps: int, weight_kg: float, notes: str):
    init_workout_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            UPDATE workouts
            SET exercise=?, muscle_group=?, sets=?, reps=?, weight_kg=?, notes=?
            WHERE id=?
        """, (exercise, muscle_group, sets, reps, weight_kg, notes, row_id))


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
    init_workout_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT workout_date, exercise, muscle_group, sets, reps, weight_kg,
                   notes, cardio_type, duration_min, distance_km, avg_hr,
                   workout_start, workout_end
            FROM workouts WHERE user_name = ?
            ORDER BY workout_date DESC, id DESC LIMIT ?
        """, (user_name, limit)).fetchall()
    if not rows:
        return "Дневник тренировок пуст."
    lines = []
    for r in rows:
        date, exercise, mg, sets, reps, weight, notes, ctype, dur, dist, hr, wstart, wend = r
        time_str = f" [{wstart}–{wend}]" if wstart and wend else ""
        if mg in ("Кардио", "Cardio", "קרדיו") or ctype or dur:
            parts = [f"{date}{time_str} | {exercise} ({mg})"]
            if ctype:
                parts.append(ctype)
            if dur:
                parts.append(f"{dur} мин")
            if dist:
                parts.append(f"{dist} км")
            if hr:
                parts.append(f"пульс {hr} уд/мин")
            if notes:
                parts.append(notes)
            lines.append(" | ".join(parts))
        else:
            lines.append(
                f"{date}{time_str} | {exercise} ({mg}) | {sets}x{reps} @ {weight} кг"
                + (f" | {notes}" if notes else "")
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
