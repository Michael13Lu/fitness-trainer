import sqlite3
from config import DB_PATH

MEAL_TYPES = ["Завтрак", "Обед", "Ужин", "Перекус"]


def _init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS food_diary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                food_date TEXT NOT NULL,
                meal_type TEXT NOT NULL,
                food_name TEXT NOT NULL,
                calories REAL DEFAULT 0,
                protein REAL DEFAULT 0,
                fat REAL DEFAULT 0,
                carbs REAL DEFAULT 0,
                weight_g REAL DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


# Инициализируем БД один раз при импорте модуля
_init_db()


def add_food(user_name: str, food_date: str, meal_type: str, food_name: str,
             calories: float = 0, protein: float = 0, fat: float = 0,
             carbs: float = 0, weight_g: float = 0, notes: str = ""):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO food_diary
              (user_name, food_date, meal_type, food_name, calories, protein, fat, carbs, weight_g, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_name, food_date, meal_type, food_name,
              calories, protein, fat, carbs, weight_g, notes))


def get_food_by_date(user_name: str, food_date: str) -> list:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT id, meal_type, food_name, calories, protein, fat, carbs, weight_g, notes
            FROM food_diary
            WHERE user_name = ? AND food_date = ?
            ORDER BY id ASC
        """, (user_name, food_date)).fetchall()
    return [
        {"id": r[0], "meal_type": r[1], "food_name": r[2],
         "calories": r[3], "protein": r[4], "fat": r[5],
         "carbs": r[6], "weight_g": r[7], "notes": r[8]}
        for r in rows
    ]


def get_food_history(user_name: str, limit: int = 50) -> list:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT food_date, meal_type, food_name, calories, protein, fat, carbs, weight_g, notes
            FROM food_diary
            WHERE user_name = ?
            ORDER BY food_date DESC, id DESC LIMIT ?
        """, (user_name, limit)).fetchall()
    return [
        {"date": r[0], "meal_type": r[1], "food_name": r[2],
         "calories": r[3], "protein": r[4], "fat": r[5],
         "carbs": r[6], "weight_g": r[7], "notes": r[8]}
        for r in rows
    ]


def delete_last_food(user_name: str):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT id FROM food_diary WHERE user_name = ? ORDER BY id DESC LIMIT 1",
            (user_name,)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM food_diary WHERE id = ?", (row[0],))


def get_daily_totals(user_name: str, food_date: str) -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("""
            SELECT COALESCE(SUM(calories),0), COALESCE(SUM(protein),0),
                   COALESCE(SUM(fat),0), COALESCE(SUM(carbs),0)
            FROM food_diary WHERE user_name = ? AND food_date = ?
        """, (user_name, food_date)).fetchone()
    return {"calories": row[0], "protein": row[1], "fat": row[2], "carbs": row[3]}


def get_food_as_text(user_name: str, limit: int = 30) -> str:
    rows = get_food_history(user_name, limit)
    if not rows:
        return "Дневник питания пуст."
    lines = []
    for r in rows:
        line = f"{r['date']} | {r['meal_type']} | {r['food_name']}"
        if r["weight_g"]:
            line += f" {r['weight_g']}г"
        if r["calories"]:
            line += f" | {r['calories']:.0f} ккал"
        if r["protein"] or r["fat"] or r["carbs"]:
            line += f" | Б{r['protein']:.0f} Ж{r['fat']:.0f} У{r['carbs']:.0f}"
        lines.append(line)
    return "\n".join(lines)



def get_food_as_text(user_name: str, limit: int = 30) -> str:
    rows = get_food_history(user_name, limit)
    if not rows:
        return "Дневник питания пуст."
    lines = []
    for r in rows:
        line = f"{r['date']} | {r['meal_type']} | {r['food_name']}"
        if r["weight_g"]:
            line += f" {r['weight_g']}г"
        if r["calories"]:
            line += f" | {r['calories']:.0f} ккал"
        if r["protein"] or r["fat"] or r["carbs"]:
            line += f" | Б{r['protein']:.0f} Ж{r['fat']:.0f} У{r['carbs']:.0f}"
        lines.append(line)
    return "\n".join(lines)
