"""Local exercise integration from GitHub JSON dump (no API key required)."""

from __future__ import annotations

import json
import urllib.request
from functools import lru_cache
from pathlib import Path

EXERCISE_JSON_PATH = Path(__file__).parent / "data" / "exercises_github.json"
EXERCISE_JSON_URL = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"
EXERCISE_IMAGE_BASE = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/"


@lru_cache(maxsize=1)
def _load_catalog() -> list[dict]:
    if not EXERCISE_JSON_PATH.exists():
        refresh_exercises_from_github()
    if not EXERCISE_JSON_PATH.exists():
        return []
    try:
        return json.loads(EXERCISE_JSON_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def refresh_exercises_from_github() -> bool:
    """Скачать актуальный JSON-дамп упражнений из GitHub в локальный файл."""
    try:
        EXERCISE_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        raw = urllib.request.urlopen(EXERCISE_JSON_URL, timeout=30).read().decode("utf-8")
        data = json.loads(raw)
        EXERCISE_JSON_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        _load_catalog.cache_clear()
        search_exercise.cache_clear()
        return True
    except Exception:
        return False


def _norm(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


@lru_cache(maxsize=300)
def search_exercise(exercise_name: str) -> dict | None:
    """Ищет упражнение в локальном JSON и возвращает структурированные данные."""
    query = _norm(exercise_name)
    if not query:
        return None

    catalog = _load_catalog()
    if not catalog:
        return None

    match = None
    for ex in catalog:
        if _norm(ex.get("name", "")) == query:
            match = ex
            break
    if match is None:
        for ex in catalog:
            if query in _norm(ex.get("name", "")):
                match = ex
                break
    if match is None:
        return None

    images = match.get("images") or []
    image_urls = [f"{EXERCISE_IMAGE_BASE}{img}" for img in images if isinstance(img, str)]
    primary = [m.title() for m in (match.get("primaryMuscles") or [])]
    secondary = [m.title() for m in (match.get("secondaryMuscles") or [])]
    instructions = [step for step in (match.get("instructions") or []) if isinstance(step, str)]

    return {
        "name": (match.get("name") or "").title(),
        "target": primary[0] if primary else "",
        "secondary": secondary,
        "equipment": (match.get("equipment") or "Bodyweight").title(),
        "image_urls": image_urls,
        "instructions": instructions,
    }


def get_exercise_schema(exercise_name: str) -> str:
    """Возвращает краткую схему выполнения упражнения."""
    ex = search_exercise(exercise_name)
    if not ex:
        return ""

    schema = f"**🏋️ {ex['name']}**\n\n"
    if ex["target"]:
        schema += f"🎯 **Target:** {ex['target']}\n"
    if ex["secondary"]:
        schema += f"💪 **Secondary:** {', '.join(ex['secondary'][:3])}\n"
    schema += f"⚙️ **Equipment:** {ex['equipment'] or 'Bodyweight'}\n"
    if ex["instructions"]:
        schema += "\n**📋 Steps:**\n"
        for idx, step in enumerate(ex["instructions"][:3], start=1):
            schema += f"{idx}. {step}\n"
    return schema


def get_exercise_gif(exercise_name: str) -> str | None:
    """Совместимость со старым интерфейсом: возвращает первую картинку упражнения."""
    ex = search_exercise(exercise_name)
    if not ex:
        return None
    return ex["image_urls"][0] if ex["image_urls"] else None


def get_exercise_images(exercise_name: str) -> list[str]:
    """Возвращает все кадры упражнения (обычно 2: начало и конец движения)."""
    ex = search_exercise(exercise_name)
    if not ex:
        return []
    return ex["image_urls"]
