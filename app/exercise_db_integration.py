"""
ExerciseDB integration for exercise schemas/technique instructions.
Provides exercise details: target muscle, secondary muscles, equipment, GIF URL.

API: https://rapidapi.com/justin-WFnsXH_haHLw/api/exercisedb
"""
import os
import requests
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

EXERCISE_DB_API_KEY = os.getenv("EXERCISE_DB_API_KEY", "")
EXERCISE_DB_HOST = "exercisedb.p.rapidapi.com"


@lru_cache(maxsize=200)
def search_exercise(exercise_name: str) -> dict | None:
    """
    Поиск упражнения в ExerciseDB по названию.
    Возвращает первый результат с информацией о технике.
    
    Returns:
        {
            "name": str,
            "target": str,           # целевая мышца
            "secondary": list[str],  # вспомогательные мышцы
            "equipment": str,        # оборудование
            "gif_url": str,          # GIF-анимация
            "description": str       # техника описание
        }
    """
    if not EXERCISE_DB_API_KEY:
        return None
    
    try:
        url = f"https://{EXERCISE_DB_HOST}/exercises/name/{exercise_name.lower()}"
        headers = {
            "X-RapidAPI-Key": EXERCISE_DB_API_KEY,
            "X-RapidAPI-Host": EXERCISE_DB_HOST
        }
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code != 200 or not response.json():
            return None
        
        exercises = response.json()
        if not exercises:
            return None
        
        # Берём первый результат
        ex = exercises[0]
        return {
            "name": ex.get("name", "").title(),
            "target": ex.get("target", "").title(),
            "secondary": [m.title() for m in ex.get("secondaryMuscles", [])],
            "equipment": ex.get("equipment", "").title(),
            "gif_url": ex.get("gifUrl", ""),
            "description": f"🎯 Target: {ex.get('target', '').title()} | "
                          f"Equipment: {ex.get('equipment', 'Bodyweight').title()}"
        }
    except Exception as e:
        print(f"ExerciseDB error: {e}")
        return None


def get_exercise_schema(exercise_name: str) -> str:
    """
    Получить описание схемы выполнения упражнения для Streamlit вывода.
    """
    ex = search_exercise(exercise_name)
    if not ex:
        return ""
    
    schema = f"**🏋️ {ex['name']}**\n\n"
    schema += f"🎯 **Target:** {ex['target']}\n"
    
    if ex['secondary']:
        schema += f"💪 **Secondary:** {', '.join(ex['secondary'][:3])}\n"
    
    schema += f"⚙️ **Equipment:** {ex['equipment'] or 'Bodyweight'}\n"
    
    return schema


def get_exercise_gif(exercise_name: str) -> str | None:
    """Получить GIF-ссылку на анимацию упражнения."""
    ex = search_exercise(exercise_name)
    return ex.get("gif_url") if ex else None
