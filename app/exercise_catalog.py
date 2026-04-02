"""
Multilingual exercise catalog, organized by muscle group index.
Group indices match MUSCLE_GROUPS in translations.py:
  0 Chest/Грудь, 1 Back/Спина, 2 Shoulders/Плечи, 3 Biceps/Бицепс,
  4 Triceps/Трицепс, 5 Abs/Пресс, 6 Quads/Квадрицепс,
  7 Hamstrings/Бицепс бедра, 8 Glutes/Ягодицы,
  9 Calves/Икры, 10 Cardio/Кардио
"""

_EN: list[list[str]] = [
    # 0 Chest
    ["Bench Press", "Incline Bench Press", "Decline Bench Press",
     "Dumbbell Press", "Incline Dumbbell Press", "Dumbbell Fly",
     "Incline Dumbbell Fly", "Cable Crossover", "Push-ups",
     "Diamond Push-ups", "Wide Push-ups", "Dips",
     "Pec Deck Machine", "Smith Machine Press", "Landmine Press",
     "Svend Press"],

    # 1 Back
    ["Deadlift", "Pull-ups", "Chin-ups", "Neutral-grip Pull-ups",
     "Lat Pulldown", "Close-grip Pulldown", "Barbell Row",
     "Dumbbell Row", "Cable Row", "Seated Cable Row",
     "T-bar Row", "Face Pull", "Hyperextension",
     "Rack Pull", "Meadows Row", "Pendlay Row",
     "Straight-arm Pulldown", "Superman"],

    # 2 Shoulders
    ["Overhead Barbell Press", "Dumbbell Shoulder Press",
     "Arnold Press", "Lateral Raise", "Cable Lateral Raise",
     "Front Raise", "Rear Delt Fly", "Cable Rear Delt Fly",
     "Upright Row", "Shrugs", "Machine Shoulder Press",
     "Behind-the-neck Press", "Cuban Press", "Y-Raise",
     "Bent-over Lateral Raise"],

    # 3 Biceps
    ["Barbell Curl", "EZ-bar Curl", "Dumbbell Curl",
     "Hammer Curl", "Preacher Curl", "EZ Preacher Curl",
     "Cable Curl", "Concentration Curl",
     "Incline Dumbbell Curl", "Spider Curl",
     "Zottman Curl", "Drag Curl", "Reverse Curl",
     "Cross-body Hammer Curl"],

    # 4 Triceps
    ["Tricep Pushdown (rope)", "Tricep Pushdown (bar)",
     "Skull Crusher", "Overhead Extension",
     "Overhead Extension (cable)", "Close-grip Bench Press",
     "Dips", "Kickback", "Single-arm Pushdown",
     "JM Press", "Tate Press", "Diamond Push-ups",
     "Tricep Dip Machine"],

    # 5 Abs
    ["Crunch", "Bicycle Crunch", "Reverse Crunch",
     "Plank", "Side Plank", "Plank Reach",
     "Leg Raise", "Hanging Leg Raise", "Hanging Knee Raise",
     "Russian Twist", "Mountain Climber",
     "Ab Rollout", "Cable Crunch", "V-up",
     "Dragon Flag", "Hollow Body Hold", "Dead Bug",
     "Windshield Wiper"],

    # 6 Quads
    ["Squat", "Front Squat", "Overhead Squat",
     "Leg Press", "Leg Extension", "Walking Lunge",
     "Reverse Lunge", "Bulgarian Split Squat",
     "Hack Squat", "Box Squat", "Step-up",
     "Sissy Squat", "Goblet Squat", "Zercher Squat",
     "Pistol Squat", "Wall Sit"],

    # 7 Hamstrings
    ["Romanian Deadlift", "Leg Curl (lying)",
     "Leg Curl (seated)", "Stiff-leg Deadlift",
     "Good Morning", "Nordic Curl",
     "Glute-Ham Raise", "Single-leg Deadlift",
     "Stability Ball Curl", "Single-leg Curl",
     "Snatch-grip Deadlift"],

    # 8 Glutes
    ["Hip Thrust", "Barbell Glute Bridge",
     "Single-leg Hip Thrust", "Cable Kickback",
     "Abductor Machine", "Donkey Kick",
     "Fire Hydrant", "Step-up",
     "Sumo Squat", "Bulgarian Split Squat",
     "Lateral Band Walk", "Clamshell",
     "Frog Pump"],

    # 9 Calves
    ["Standing Calf Raise", "Seated Calf Raise",
     "Donkey Calf Raise", "Leg Press Calf Raise",
     "Single-leg Calf Raise", "Smith Machine Calf Raise",
     "Jump Rope (calves focus)", "Tibialis Raise"],

    # 10 Cardio
    ["Treadmill Run", "Cycling", "Rowing Machine",
     "Elliptical", "Jump Rope", "HIIT",
     "Swimming", "Stair Climber", "Battle Ropes",
     "Box Jumps", "Burpees", "Kettlebell Swing",
     "Sled Push", "Air Bike", "Shadow Boxing",
     "Jump Squat", "Sprint Intervals"],
]

_RU: list[list[str]] = [
    # 0 Грудь
    ["Жим штанги лёжа", "Жим гантелей лёжа",
     "Жим на наклонной скамье", "Жим гантелей на наклонной",
     "Жим на обратной скамье", "Разводка гантелей лёжа",
     "Разводка гантелей на наклонной", "Кроссовер",
     "Отжимания", "Отжимания узким хватом",
     "Широкие отжимания", "Дипсы",
     "Пек-дек", "Жим в Смите", "Ландминная жим",
     "Жим Свенда"],

    # 1 Спина
    ["Становая тяга", "Подтягивания широким хватом",
     "Подтягивания обратным хватом", "Подтягивания нейтральным хватом",
     "Тяга верхнего блока широким хватом",
     "Тяга верхнего блока узким хватом",
     "Тяга штанги в наклоне", "Тяга гантели одной рукой",
     "Горизонтальная тяга", "Тяга сидя в блоке",
     "Тяга Т-образного грифа", "Тяга к лицу",
     "Гиперэкстензия", "Становая тяга в стойке",
     "Тяга Пендлея", "Тяга прямыми руками",
     "Супермен"],

    # 2 Плечи
    ["Жим штанги стоя", "Жим гантелей сидя",
     "Жим Арнольда", "Махи гантелями в стороны",
     "Тяга блока в стороны", "Махи гантелями вперёд",
     "Разводка гантелей в наклоне",
     "Тяга блока на заднюю дельту", "Тяга штанги к подбородку",
     "Шраги со штангой", "Жим в тренажёре для плеч",
     "Жим за голову", "Кубинский жим",
     "Y-подъём", "Обратные махи в наклоне"],

    # 3 Бицепс
    ["Сгибание рук со штангой", "Сгибание с EZ-грифом",
     "Сгибание рук с гантелями", "Молоток",
     "Сгибание Скотта", "Сгибание на скамье Скотта с EZ-грифом",
     "Сгибание в кроссовере", "Концентрированное сгибание",
     "Сгибание на наклонной скамье", "Паук-сгибание",
     "Сгибание Зоттмана", "Сгибание протяжкой",
     "Обратное сгибание", "Сгибание поперёк тела"],

    # 4 Трицепс
    ["Разгибание в блоке (канат)", "Разгибание в блоке (гриф)",
     "Французский жим лёжа", "Разгибание гантели из-за головы",
     "Разгибание на блоке над головой",
     "Жим узким хватом", "Дипсы",
     "Отдача (кикбэк)", "Разгибание одной рукой в блоке",
     "JM-жим", "Жим Тейт",
     "Отжимания узким хватом", "Разгибание в тренажёре"],

    # 5 Пресс
    ["Скручивания", "Велосипед", "Обратные скручивания",
     "Планка", "Боковая планка", "Планка с касанием",
     "Подъём ног лёжа", "Подъём ног в висе",
     "Подъём коленей в висе", "Русский твист",
     "Скалолаз", "Ролик для пресса",
     "Скручивания в кроссовере", "V-подъём",
     "Флаг дракона", "Мёртвый жук",
     "Стеклоочиститель"],

    # 6 Квадрицепс
    ["Приседания со штангой", "Фронтальные приседания",
     "Приседания над головой", "Жим ногами",
     "Разгибания ног в тренажёре", "Выпады с ходьбой",
     "Обратные выпады", "Болгарский сплит-присед",
     "Гакк-приседания", "Приседания в ящик",
     "Зашагивания на ящик", "Сисси-приседания",
     "Гоблет-приседания", "Приседания Зерчера",
     "Пистолет", "Статические приседания у стены"],

    # 7 Бицепс бедра
    ["Румынская тяга", "Сгибания ног лёжа",
     "Сгибания ног сидя", "Становая тяга на прямых ногах",
     "Гудморнинг", "Нордические сгибания",
     "Разгибание на скамье GHD", "Тяга одной ногой",
     "Сгибания ног на фитболе", "Тяга сумо"],

    # 8 Ягодицы
    ["Ягодичный мостик со штангой",
     "Ягодичный мостик с весом", "Мостик на одной ноге",
     "Тяга ногой в кроссовере", "Разводка ног в тренажёре",
     "Мах ногой назад", "Пожарный гидрант",
     "Зашагивания на ящик", "Сумо-приседания",
     "Болгарский сплит-присед",
     "Ходьба с резинкой в стороны", "Раскладушка",
     "Лягушачий насос"],

    # 9 Икры
    ["Подъём на носки стоя", "Подъём на носки сидя",
     "Ослиные подъёмы", "Подъём на носки в жиме ногами",
     "Подъём на носки на одной ноге",
     "Подъём на носки в тренажёре Смита",
     "Прыжки со скакалкой (акцент на икры)",
     "Подъём носка (тибиалис)"],

    # 10 Кардио
    ["Бег на беговой дорожке", "Велотренажёр",
     "Гребной тренажёр", "Эллиптический тренажёр",
     "Прыжки со скакалкой", "ВИИТ-тренировка",
     "Плавание", "Степпер", "Боевые канаты",
     "Запрыгивания на ящик", "Берпи",
     "Свинг с гирей", "Толкание саней",
     "Велосипед (Air Bike)", "Бой с тенью",
     "Прыжки на месте", "Спринтерские интервалы"],
]

# Spanish exercises (gym terms are mostly same as English)
_ES = _EN  # Spanish gyms use English names predominantly

# German
_DE = _EN

# French
_FR = _EN

# Hebrew
_HE = _EN


def get_catalog(lang: str) -> list[list[str]]:
    """Return exercise list for given language code. Falls back to English."""
    return {
        "ru": _RU,
        "en": _EN,
        "es": _ES,
        "de": _DE,
        "fr": _FR,
        "he": _HE,
    }.get(lang, _EN)
