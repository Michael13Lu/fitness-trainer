import os
import base64
import json
import io
from datetime import date
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from pypdf import PdfReader
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from audio_recorder_streamlit import audio_recorder
from groq import Groq
from memory_store import load_messages, save_message, clear_history, save_language, load_language, save_profile, load_profile
from workout_store import (add_exercise, get_workouts, get_muscle_summary,
                           get_workouts_as_text, delete_last_exercise,
                           get_workouts_by_date)
from translations import LANGUAGES, t
from google_calendar import (is_configured, get_auth_url, exchange_code,
                              creds_to_dict, creds_from_dict)
from googleapiclient.discovery import build as gcal_build

load_dotenv()

st.set_page_config(page_title="Fitness Trainer", page_icon="💪", layout="wide")

# ============================================================
# GOOGLE CALENDAR — OAuth callback
# ============================================================
if "gcal_creds" not in st.session_state:
    st.session_state.gcal_creds = None

_params = st.query_params
if "code" in _params and st.session_state.gcal_creds is None:
    try:
        creds = exchange_code(_params["code"], _params.get("state", ""))
        st.session_state.gcal_creds = creds_to_dict(creds)
        st.query_params.clear()
        st.success("✅ Google Calendar connected!")
        st.rerun()
    except Exception as e:
        st.error(f"Google Calendar auth error: {e}")
        st.query_params.clear()

# ============================================================
# ЯЗЫК — выбирается первым, до всего остального
# ============================================================
# Загружаем сохранённый язык из session_state (сохраняется в БД после выбора имени)
if "lang_name" not in st.session_state:
    st.session_state.lang_name = "Русский"

with st.sidebar:
    lang_list = list(LANGUAGES.keys())
    saved_idx = lang_list.index(st.session_state.lang_name) if st.session_state.lang_name in lang_list else 0
    lang_name = st.selectbox("🌐 Language / Язык", lang_list, index=saved_idx)
    lang = LANGUAGES[lang_name]
    # Сохраняем выбор в session_state сразу
    if lang_name != st.session_state.lang_name:
        st.session_state.lang_name = lang_name
        st.rerun()

st.title(t(lang, "app_title"))

# ============================================================
# САЙДБАР — АККОРДЕОН
# ============================================================
if "sidebar_section" not in st.session_state:
    st.session_state.sidebar_section = "profile"

_PROFILE_DEFAULTS = {
    "name": "Михаил", "age": 25, "weight": 75, "height": 175,
    "goal_idx": 0, "level_idx": 0, "style_idx": 0,
    "target_weight": 0.0, "target_date": "",
}

if "profile" not in st.session_state:
    # Попытка загрузить из БД по имени по умолчанию
    _saved = load_profile(_PROFILE_DEFAULTS["name"])
    st.session_state["profile"] = _saved if _saved else dict(_PROFILE_DEFAULTS)

_prof = st.session_state["profile"]
# Заполняем недостающие ключи (обратная совместимость)
for _k, _v in _PROFILE_DEFAULTS.items():
    _prof.setdefault(_k, _v)

with st.sidebar:
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🙂 " + t(lang, "profile"), use_container_width=True):
            st.session_state.sidebar_section = "profile"
    with c2:
        if st.button("🔊", use_container_width=True):
            st.session_state.sidebar_section = "voice"
    with c3:
        cal_label = "📅 ✓" if st.session_state.gcal_creds else "📅"
        if st.button(cal_label, use_container_width=True):
            st.session_state.sidebar_section = "calendar"

    st.divider()

    # ── Профиль ──────────────────────────────────────────────
    if st.session_state.sidebar_section == "profile":
        _prof["name"] = st.text_input(t(lang, "name"), value=_prof["name"])
        _prof["age"] = st.number_input(t(lang, "age"), min_value=10, max_value=100, value=_prof["age"])
        _prof["weight"] = st.number_input(t(lang, "weight"), min_value=30, max_value=200, value=_prof["weight"])
        _prof["height"] = st.number_input(t(lang, "height"), min_value=100, max_value=250, value=_prof["height"])
        goals_list = t(lang, "goals")
        _prof["goal_idx"] = min(_prof["goal_idx"], len(goals_list) - 1)
        _prof["goal_idx"] = goals_list.index(st.selectbox(t(lang, "goal"), goals_list, index=_prof["goal_idx"]))
        levels_list = t(lang, "levels")
        _prof["level_idx"] = min(_prof["level_idx"], len(levels_list) - 1)
        _prof["level_idx"] = levels_list.index(st.selectbox(t(lang, "level"), levels_list, index=_prof["level_idx"]))
        styles_list = t(lang, "styles")
        _prof["style_idx"] = min(_prof["style_idx"], len(styles_list) - 1)
        _prof["style_idx"] = styles_list.index(st.selectbox(t(lang, "trainer_style"), styles_list, index=_prof["style_idx"]))

        st.divider()
        _prof["target_weight"] = st.number_input(
            t(lang, "target_weight"), min_value=0.0, max_value=300.0,
            value=float(_prof["target_weight"]), step=0.5,
            help="0 = не задано"
        )
        import datetime as _dt
        _default_date = (
            _dt.date.fromisoformat(_prof["target_date"])
            if _prof.get("target_date") else _dt.date.today() + _dt.timedelta(weeks=12)
        )
        _target_date = st.date_input(t(lang, "target_date"), value=_default_date)
        _prof["target_date"] = str(_target_date)

        save_profile(_prof["name"], _prof)

    # ── Голос и чат ──────────────────────────────────────────
    elif st.session_state.sidebar_section == "voice":
        voice_response = st.toggle(t(lang, "speak_toggle"), value=False)
        st.write("")
        if st.button(t(lang, "clear_chat"), use_container_width=True):
            clear_history(_prof["name"])
            st.session_state.history = ChatMessageHistory()
            st.session_state.messages = []
            st.rerun()

    # ── Google Calendar ───────────────────────────────────────
    elif st.session_state.sidebar_section == "calendar":
        st.markdown("**📅 Google Calendar**")
        if st.session_state.gcal_creds:
            st.success("Connected ✓")
            if st.button("🔌 Disconnect", use_container_width=True):
                st.session_state.gcal_creds = None
                st.rerun()
        elif is_configured():
            auth_url = get_auth_url()
            st.link_button("🔗 Connect Google Calendar", auth_url, use_container_width=True)
        else:
            st.caption("Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env to enable")

# Читаем профиль из session_state (всегда доступны)
name = _prof["name"]
age = _prof["age"]
weight = _prof["weight"]
height = _prof["height"]
goal = t(lang, "goals")[_prof["goal_idx"]]
level = t(lang, "levels")[_prof["level_idx"]]
trainer_style = t(lang, "styles")[_prof["style_idx"]]
target_weight = _prof.get("target_weight", 0.0)
target_date = _prof.get("target_date", "")

# Вычисляем реалистичный темп похудения
import datetime as _dt
_weight_goal_info = ""
if target_weight and target_weight > 0 and target_date:
    _kg_diff = weight - target_weight
    try:
        _days = (_dt.date.fromisoformat(target_date) - _dt.date.today()).days
        _weeks = max(_days / 7, 1)
        _kg_per_week = _kg_diff / _weeks
        _realistic = 0.5 if _kg_diff > 0 else 0.3  # норма похудения/набора в кг/нед
        _realistic_weeks = abs(_kg_diff) / _realistic
        _realistic_date = _dt.date.today() + _dt.timedelta(weeks=_realistic_weeks)
        if _kg_diff > 0:
            _weight_goal_info = (
                f"- Target weight: {target_weight} kg by {target_date} "
                f"({_kg_diff:+.1f} kg, {_kg_per_week:.2f} kg/week planned). "
                f"Safe rate is ~0.5 kg/week → realistic date: {_realistic_date}. "
                f"{'WARN: plan is too aggressive, adjust expectations.' if abs(_kg_per_week) > 1.0 else 'Plan is realistic.'}"
            )
        elif _kg_diff < 0:
            _weight_goal_info = (
                f"- Target weight: {target_weight} kg by {target_date} "
                f"(+{abs(_kg_diff):.1f} kg muscle gain). "
                f"Safe rate ~0.3 kg/week → realistic date: {_realistic_date}."
            )
    except Exception:
        _weight_goal_info = f"- Target weight: {target_weight} kg by {target_date}"
if st.session_state.sidebar_section != "voice":
    voice_response = False

# ============================================================
# ИСТОРИЯ ИЗ БД
# ============================================================
if "history" not in st.session_state:
    st.session_state.history = ChatMessageHistory()
    for msg in load_messages(name):
        if msg["role"] == "user":
            st.session_state.history.add_user_message(msg["content"])
        else:
            st.session_state.history.add_ai_message(msg["content"])

if "messages" not in st.session_state:
    st.session_state.messages = load_messages(name)

if "loaded_for" not in st.session_state:
    st.session_state.loaded_for = name
    saved_lang = load_language(name)
    if saved_lang != st.session_state.lang_name:
        st.session_state.lang_name = saved_lang
        st.rerun()
elif st.session_state.loaded_for != name:
    # Смена пользователя — загружаем его профиль и историю
    _saved_prof = load_profile(name)
    if _saved_prof:
        st.session_state["profile"] = _saved_prof
    st.session_state.history = ChatMessageHistory()
    for msg in load_messages(name):
        if msg["role"] == "user":
            st.session_state.history.add_user_message(msg["content"])
        else:
            st.session_state.history.add_ai_message(msg["content"])
    st.session_state.messages = load_messages(name)
    st.session_state.loaded_for = name
    saved_lang = load_language(name)
    if saved_lang != st.session_state.lang_name:
        st.session_state.lang_name = saved_lang
        st.rerun()

# Сохраняем текущий выбор языка в БД
save_language(name, lang_name)

# ============================================================
# МОДЕЛИ И ЦЕПОЧКА
# ============================================================
llm_text = ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)
llm_vision = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0.7)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

system_prompt = """You are a personal fitness trainer and nutritionist.

Client info:
- Name: {name}
- Age: {age}
- Weight: {weight} kg, Height: {height} cm
- Goal: {goal}
- Fitness level: {level}
- Your communication style: {trainer_style}
{weight_goal_info}
Give specific advice on training and nutrition based on the client's profile.
When building a program, respect the realistic weight loss/gain rate (~0.5 kg/week for fat loss).
If the client's target is too aggressive, gently explain realistic expectations.
Motivate and support. Be concrete and practical.
{lang_instruction}"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])
chain = prompt | llm_text | StrOutputParser()

MUSCLE_GROUPS = t(lang, "muscle_groups")


def get_chain_input(user_input: str) -> dict:
    return {
        "name": name, "age": age, "weight": weight, "height": height,
        "goal": goal, "level": level, "trainer_style": trainer_style,
        "weight_goal_info": _weight_goal_info,
        "lang_instruction": t(lang, "system_prompt_lang"),
        "history": st.session_state.history.messages,
        "input": user_input,
    }


def transcribe_audio(audio_bytes: bytes) -> str:
    result = groq_client.audio.transcriptions.create(
        file=("voice.wav", audio_bytes),
        model="whisper-large-v3",
    )
    return result.text


def get_system_text():
    return system_prompt.format(
        name=name, age=age, weight=weight, height=height,
        goal=goal, level=level, trainer_style=trainer_style,
        weight_goal_info=_weight_goal_info,
        lang_instruction=t(lang, "system_prompt_lang")
    )


def extract_text_from_file(file) -> str:
    if file.name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file.read()))
        return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    elif file.name.endswith(".csv"):
        df = pd.read_csv(file)
        return df.to_string(index=False)
    return ""


def speak(text: str):
    lang_map = {"ru": "ru-RU", "en": "en-US", "es": "es-ES",
                "de": "de-DE", "fr": "fr-FR", "he": "he-IL"}
    clean = text.replace("`", "").replace("*", "").replace("#", "")
    js = f"""
    <script>
    window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance({json.dumps(clean)});
    u.lang = '{lang_map.get(lang, "en-US")}';
    u.rate = 1.0;
    window.speechSynthesis.speak(u);
    </script>
    """
    components.html(js, height=0)


def analyze_with_image(image_bytes: bytes, mime_type: str, user_text: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    messages = [
        SystemMessage(content=get_system_text()),
        HumanMessage(content=[
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
            {"type": "text", "text": user_text or "Analyze this photo and give advice based on my profile."},
        ]),
    ]
    return llm_vision.invoke(messages).content


def extract_exercise_from_image(image_bytes: bytes, mime_type: str) -> dict:
    muscle_list = "/".join(MUSCLE_GROUPS)
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    messages = [
        HumanMessage(content=[
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
            {"type": "text", "text": f"""Look at the photo of the exercise machine or exercise.
Reply ONLY in JSON format, no extra text:
{{"exercise": "exercise name", "muscle_group": "one of: {muscle_list}"}}
If no exercise machine in photo — return {{"exercise": "", "muscle_group": ""}}"""},
        ]),
    ]
    try:
        result = llm_vision.invoke(messages).content
        start = result.find("{")
        end = result.rfind("}") + 1
        return json.loads(result[start:end])
    except Exception:
        return {"exercise": "", "muscle_group": ""}


# ============================================================
# ВКЛАДКИ
# ============================================================
tab_chat, tab_diary, tab_analysis = st.tabs([
    t(lang, "tab_chat"), t(lang, "tab_diary"), t(lang, "tab_analysis")
])

# ============================================================
# ВКЛАДКА 1: ЧАТ
# ============================================================
with tab_chat:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("image"):
                st.image(msg["image"], width=200)
            st.markdown(msg["content"])

# Микрофон
_, col_mic, _ = st.columns([0.48, 0.04, 0.48])
with col_mic:
    audio_bytes = audio_recorder(
        text="", recording_color="#e74c3c",
        neutral_color="#888888", icon_size="sm",
    )

# Голосовой ввод
if audio_bytes and len(audio_bytes) > 1000 and audio_bytes != st.session_state.get("last_audio"):
    st.session_state.last_audio = audio_bytes
    with st.spinner(t(lang, "recognizing")):
        voice_text = transcribe_audio(audio_bytes)
    if voice_text:
        with st.chat_message("user"):
            st.markdown(f"🎙️ {voice_text}")
        st.session_state.messages.append({"role": "user", "content": f"🎙️ {voice_text}"})
        with st.chat_message("assistant"):
            with st.spinner(t(lang, "thinking")):
                response = chain.invoke(get_chain_input(voice_text))
            st.markdown(response)
        if voice_response:
            speak(response)
        st.session_state.history.add_user_message(voice_text)
        st.session_state.history.add_ai_message(response)
        save_message(name, "user", voice_text)
        save_message(name, "assistant", response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# Текстовый ввод + файл
msg = st.chat_input(
    t(lang, "chat_placeholder"),
    accept_file=True,
    file_type=["jpg", "jpeg", "png", "webp", "pdf", "csv"],
)

if msg:
    user_input = msg.text or ""
    attached = msg["files"][0] if msg["files"] else None
    is_image = attached and attached.type in ("image/jpeg", "image/png", "image/webp", "image/jpg")
    is_doc = attached and not is_image

    with st.chat_message("user"):
        if is_image:
            st.image(attached.read(), width=200)
            attached.seek(0)
        elif is_doc:
            st.markdown(f"📄 **{attached.name}**")
        if user_input:
            st.markdown(user_input)

    st.session_state.messages.append({
        "role": "user",
        "content": user_input or (f"📄 {attached.name}" if attached else "_(msg)_"),
    })

    with st.chat_message("assistant"):
        with st.spinner(t(lang, "thinking")):
            if is_image:
                image_data = attached.read()
                exercise_info = extract_exercise_from_image(image_data, attached.type)
                response = analyze_with_image(image_data, attached.type, user_input)
                if exercise_info.get("exercise"):
                    st.session_state.detected_exercise = exercise_info
            elif is_doc:
                file_text = extract_text_from_file(attached)
                doc_prompt = f"Here is my document ({attached.name}). Analyze it and give recommendations:\n\n{file_text[:4000]}"
                response = chain.invoke(get_chain_input(doc_prompt))
            else:
                response = chain.invoke(get_chain_input(user_input))
        st.markdown(response)

    if voice_response:
        speak(response)
    st.session_state.history.add_user_message(user_input or "[file]")
    st.session_state.history.add_ai_message(response)
    save_message(name, "user", user_input or "[file]")
    save_message(name, "assistant", response)
    st.session_state.messages.append({"role": "assistant", "content": response})

# Форма сохранения упражнения из фото
if st.session_state.get("detected_exercise", {}).get("exercise"):
    info = st.session_state.detected_exercise
    with st.expander(t(lang, "save_to_diary"), expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            q_exercise = st.text_input(t(lang, "exercise"), value=info["exercise"], key="q_ex")
        with col2:
            mg = info["muscle_group"] if info["muscle_group"] in MUSCLE_GROUPS else MUSCLE_GROUPS[0]
            q_muscle = st.selectbox(t(lang, "muscle_group"), MUSCLE_GROUPS,
                                    index=MUSCLE_GROUPS.index(mg), key="q_mg")
        with col3:
            q_sets = st.number_input(t(lang, "sets"), min_value=1, max_value=20, value=3, key="q_sets")
            q_reps = st.number_input(t(lang, "reps"), min_value=1, max_value=100, value=10, key="q_reps")
        with col4:
            q_weight = st.number_input(t(lang, "weight_kg"), min_value=0.0, value=0.0, step=2.5, key="q_weight")
        col_save, col_skip = st.columns(2)
        with col_save:
            if st.button(t(lang, "btn_save"), use_container_width=True):
                add_exercise(name, str(date.today()), q_exercise, q_muscle, q_sets, q_reps, q_weight)
                st.success(f"{t(lang, 'recorded')}: {q_exercise}")
                st.session_state.detected_exercise = {}
                st.rerun()
        with col_skip:
            if st.button(t(lang, "btn_skip"), use_container_width=True):
                st.session_state.detected_exercise = {}
                st.rerun()

# ============================================================
# ВКЛАДКА 2: ДНЕВНИК
# ============================================================
with tab_diary:
    st.subheader(t(lang, "record_workout"))

    # Название тренировки (хранится в session_state)
    if "workout_name" not in st.session_state:
        st.session_state.workout_name = ""
    w_name = st.text_input(
        "🏷️ Название тренировки",
        value=st.session_state.workout_name,
        placeholder="День груди, Ног, Спина и бицепс...",
        key="w_name_input",
    )
    st.session_state.workout_name = w_name

    col1, col2 = st.columns(2)
    with col1:
        w_date = st.date_input(t(lang, "date"), value=date.today())
        w_exercise = st.text_input(t(lang, "exercise"), placeholder=t(lang, "exercise_placeholder"))
        w_muscle = st.selectbox(t(lang, "muscle_group"), MUSCLE_GROUPS)
    with col2:
        is_cardio = (w_muscle == MUSCLE_GROUPS[-1])  # последний элемент — Кардио

        if is_cardio:
            CARDIO_TYPES = ["🏃 Бег", "🚴 Велосипед", "🏊 Плавание", "⛷️ Эллипсоид",
                            "🚶 Ходьба", "🪜 Степпер", "🥊 Бокс/HIIT", "🛶 Гребля", "Другое"]
            w_cardio_type = st.selectbox("Вид кардио", CARDIO_TYPES)
            w_duration = st.number_input("⏱️ Длительность (мин)", min_value=1, max_value=300, value=30)
            w_distance = st.number_input("📏 Дистанция (км)", min_value=0.0, max_value=200.0, value=0.0, step=0.1)
            w_avg_hr = st.number_input("❤️ Средний пульс (уд/мин)", min_value=0, max_value=250, value=0)
        else:
            w_sets = st.number_input(t(lang, "sets"), min_value=1, max_value=20, value=3)
            w_reps = st.number_input(t(lang, "reps"), min_value=1, max_value=100, value=10)
            w_weight = st.number_input(t(lang, "weight_kg"), min_value=0.0, max_value=500.0, value=0.0, step=2.5)

    # Пульсовая зона (если кардио и пульс введён)
    if is_cardio and w_avg_hr > 0:
        max_hr = 220 - age
        pct = w_avg_hr / max_hr * 100
        if pct < 60:
            zone, zone_name = 1, "Восстановление"
        elif pct < 70:
            zone, zone_name = 2, "Жиросжигание"
        elif pct < 80:
            zone, zone_name = 3, "Аэробная"
        elif pct < 90:
            zone, zone_name = 4, "Анаэробная"
        else:
            zone, zone_name = 5, "Максимальная"
        colors = {1: "🟦", 2: "🟩", 3: "🟨", 4: "🟧", 5: "🟥"}
        st.info(f"{colors[zone]} **Зона {zone} — {zone_name}** ({pct:.0f}% от макс. пульса {max_hr})")

    w_notes = st.text_input(t(lang, "notes"), placeholder=t(lang, "notes_placeholder"))

    col_add, col_del = st.columns([0.3, 0.7])
    with col_add:
        if st.button(t(lang, "add_exercise"), use_container_width=True):
            if w_exercise:
                if is_cardio:
                    add_exercise(name, str(w_date), w_exercise, w_muscle,
                                 notes=w_notes, cardio_type=w_cardio_type,
                                 duration_min=w_duration, distance_km=w_distance,
                                 avg_hr=w_avg_hr)
                else:
                    add_exercise(name, str(w_date), w_exercise, w_muscle,
                                 w_sets, w_reps, w_weight, w_notes)
                st.success(f"{t(lang, 'recorded')}: {w_exercise}")
                st.rerun()
            else:
                st.warning(t(lang, "enter_exercise"))
    with col_del:
        if st.button(t(lang, "delete_last"), use_container_width=True):
            delete_last_exercise(name)
            st.rerun()

    # Сохранить тренировку в Google Calendar
    if st.session_state.gcal_creds:
        today_exercises = get_workouts_by_date(name, str(w_date))
        if today_exercises:
            st.divider()
            cal_title = st.session_state.workout_name or f"Тренировка {w_date}"
            st.markdown(f"**📅 Сохранить в Google Calendar:** *{cal_title}*")
            st.caption(" · ".join(e["exercise"] for e in today_exercises))
            if st.button("📅 Сохранить тренировку в календарь", use_container_width=True):
                try:
                    # Формируем описание из всех упражнений
                    lines = []
                    for e in today_exercises:
                        if e["cardio_type"] or e["duration_min"]:
                            parts = [f"• {e['exercise']} ({e['muscle_group']})"]
                            if e["cardio_type"]:
                                parts.append(e["cardio_type"])
                            if e["duration_min"]:
                                parts.append(f"{e['duration_min']} мин")
                            if e["distance_km"]:
                                parts.append(f"{e['distance_km']} км")
                            if e["avg_hr"]:
                                parts.append(f"пульс {e['avg_hr']} уд/мин")
                            line = " — ".join(parts)
                        else:
                            line = f"• {e['exercise']} ({e['muscle_group']}) — {e['sets']}×{e['reps']} @ {e['weight']} кг"
                        if e["notes"]:
                            line += f"  [{e['notes']}]"
                        lines.append(line)
                    description = "\n".join(lines)

                    creds = creds_from_dict(st.session_state.gcal_creds)
                    service = gcal_build("calendar", "v3", credentials=creds)
                    event = {
                        "summary": f"🏋️ {cal_title}",
                        "description": description,
                        "start": {"date": str(w_date)},
                        "end": {"date": str(w_date)},
                        "colorId": "2",
                    }
                    created = service.events().insert(calendarId="primary", body=event).execute()
                    event_url = created.get("htmlLink", "")
                    st.session_state.gcal_creds = creds_to_dict(creds)
                    st.success(f"Тренировка сохранена в календарь! [Открыть событие]({event_url})")
                except Exception as e:
                    st.error(f"Ошибка календаря: {e}")

    st.divider()
    st.subheader(t(lang, "workout_history"))
    workouts = get_workouts(name, limit=50)
    if workouts:
        rows = []
        for w in workouts:
            if w["cardio_type"] or w["duration_min"]:
                parts = []
                if w["cardio_type"]:
                    parts.append(w["cardio_type"])
                if w["duration_min"]:
                    parts.append(f"{w['duration_min']} мин")
                if w["distance_km"]:
                    parts.append(f"{w['distance_km']} км")
                if w["avg_hr"]:
                    parts.append(f"♥ {w['avg_hr']}")
                details = " · ".join(parts)
            else:
                details = f"{w['sets']}×{w['reps']} @ {w['weight']} кг"
            rows.append({
                t(lang, "table_cols")[0]: w["date"],
                t(lang, "table_cols")[1]: w["exercise"],
                t(lang, "table_cols")[2]: w["muscle_group"],
                t(lang, "table_cols")[3]: details,
                t(lang, "table_cols")[4]: w["notes"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info(t(lang, "no_workouts"))

# ============================================================
# ВКЛАДКА 3: АНАЛИЗ
# ============================================================
with tab_analysis:
    st.subheader(t(lang, "analysis_title"))
    workouts_text = get_workouts_as_text(name, limit=50)
    muscle_summary = get_muscle_summary(name)

    st.markdown(f"**{t(lang, 'muscle_summary')}**")
    st.code(muscle_summary)
    st.divider()

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        analyze_all = st.button(t(lang, "btn_full_analysis"), use_container_width=True)
    with col_b:
        analyze_weak = st.button(t(lang, "btn_weak"), use_container_width=True)
    with col_c:
        analyze_plan = st.button(t(lang, "btn_plan"), use_container_width=True)

    st.divider()
    selected_muscle = st.selectbox(t(lang, "select_muscle"),
                                   [t(lang, "select_placeholder")] + MUSCLE_GROUPS)
    analyze_muscle = st.button(t(lang, "btn_analyze_muscle"))

    analysis_prompt = None
    if analyze_all:
        analysis_prompt = f"Here is my workout diary:\n\n{workouts_text}\n\nDo a full analysis: progress, muscle balance, injury risks, recommendations."
    elif analyze_weak:
        analysis_prompt = f"Here is my workout diary:\n\n{workouts_text}\n\nIdentify my weak spots. My goal: {goal}."
    elif analyze_plan:
        analysis_prompt = f"Here is my workout diary:\n\n{workouts_text}\n\nBased on this, create a new 2-week training plan. Goal: {goal}, level: {level}."
    elif analyze_muscle and selected_muscle != t(lang, "select_placeholder"):
        analysis_prompt = f"Here is my workout diary:\n\n{workouts_text}\n\nDo a detailed analysis of muscle group: {selected_muscle}. Goal: {goal}."

    if analysis_prompt:
        with st.chat_message("assistant"):
            with st.spinner(t(lang, "analyzing")):
                response = chain.invoke(get_chain_input(analysis_prompt))
            st.markdown(response)
        if voice_response:
            speak(response)
