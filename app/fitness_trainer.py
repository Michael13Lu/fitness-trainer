import os
import re
import base64
import json
import io
import datetime as _dt
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
from muscle_diagram import get_muscle_html
from program_store import (save_program, get_active_program, get_all_programs,
                           activate_program, update_program_text)
from workout_store import (add_exercise, get_workouts, get_muscle_summary,
                           get_workouts_as_text, delete_last_exercise,
                           get_workouts_by_date, update_exercise)
from food_store import (add_food, get_food_by_date, get_food_history,
                        delete_last_food, get_daily_totals, get_food_as_text)
from translations import LANGUAGES, t
from exercise_catalog import get_catalog
from google_calendar import (is_configured, get_auth_url, exchange_code,
                              creds_to_dict, creds_from_dict)
from googleapiclient.discovery import build as gcal_build
from exercise_db_integration import get_exercise_schema, get_exercise_gif

from utils import calc_tdee, calc_realistic_date

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

if "sidebar_video_id" not in st.session_state:
    st.session_state.sidebar_video_id = None

with st.sidebar:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button(t(lang, "profile"), use_container_width=True):
            st.session_state.sidebar_section = "profile"
    with c2:
        if st.button("🔊", use_container_width=True):
            st.session_state.sidebar_section = "voice"
    with c3:
        cal_label = "📅 ✓" if st.session_state.gcal_creds else "📅"
        if st.button(cal_label, use_container_width=True):
            st.session_state.sidebar_section = "calendar"
    with c4:
        if st.button("🎬", use_container_width=True):
            st.session_state.sidebar_section = "video"

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
        _default_date = (
            _dt.date.fromisoformat(_prof["target_date"])
            if _prof.get("target_date") else _dt.date.today() + _dt.timedelta(weeks=12)
        )
        _target_date = st.date_input(t(lang, "target_date"), value=_default_date)
        _prof["target_date"] = str(_target_date)

        # Кнопка "принять реалистичную дату"
        _real_date = calc_realistic_date(float(_prof["weight"]), float(_prof["target_weight"]))
        if _real_date and _real_date != _target_date:
            if st.button(f"✅ {_real_date}", use_container_width=True, help=t(lang, "accept_realistic_date")):
                _prof["target_date"] = str(_real_date)
                save_profile(_prof["name"], _prof)
                st.rerun()

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

    # ── Видео по технике ─────────────────────────────────────
    elif st.session_state.sidebar_section == "video":
        st.markdown(f"**{t(lang, 'video_tutorials')}**")
        _exercises_list = st.session_state.get("sidebar_exercises", [])
        if _exercises_list:
            _suffix = t(lang, "video_search_suffix")
            # Если пришли с клика на упражнение — сразу выбираем его
            _default_ex = st.session_state.pop("sidebar_video_exercise", None)
            _default_idx = (_exercises_list.index(_default_ex)
                            if _default_ex and _default_ex in _exercises_list else 0)
            _selected_ex = st.selectbox(
                "📋", _exercises_list, index=_default_idx,
                label_visibility="collapsed"
            )
            # Название упражнения без весов/подходов для поиска
            _ex_name = " ".join(_selected_ex.split()[:3])
            _query = f"{_ex_name} {_suffix}".replace(" ", "+")
            _search_url = f"https://www.youtube.com/results?search_query={_query}"
            st.caption(f"🔍 {_ex_name}")
            # Показываем GIF из локальной базы
            _gif = get_exercise_gif(_selected_ex)
            if _gif:
                st.image(_gif, use_container_width=True, caption=_selected_ex)
            # Схема выполнения
            _schema = get_exercise_schema(_selected_ex)
            if _schema:
                st.info(_schema)
            # Ссылка на YouTube (embed listType=search отключён в 2023)
            st.link_button("▶ " + t(lang, "video_tutorials") + " на YouTube", _search_url, use_container_width=True)
        else:
            st.caption("Нажми ▶ на упражнении в программе — здесь появится видео.")

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

# Дневная норма калорий (Mifflin-St Jeor + коэффициент активности)
DAILY_KCAL = calc_tdee(weight, height, age, _prof["goal_idx"], _prof["level_idx"])

# Вычисляем реалистичный темп похудения
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
{active_program_info}
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

# Exercise catalog — language-aware, loaded once per session
_EXERCISE_CATALOG = get_catalog(lang)
_EN_CATALOG = get_catalog("en")   # всегда английский — для поиска в JSON базе


def _en_name_for(ex_pick: str, mg_idx: int) -> str:
    """Возвращает английское название упражнения для поиска в базе."""
    if lang == "en":
        return ex_pick
    try:
        ru_list = _EXERCISE_CATALOG[mg_idx]
        idx = ru_list.index(ex_pick)
        en_list = _EN_CATALOG[mg_idx]
        if idx < len(en_list):
            return en_list[idx]
    except (ValueError, IndexError):
        pass
    return ex_pick

# Keywords → muscle group index (sorted longest-first to avoid false prefix matches)
_EXERCISE_MUSCLE_MAP = sorted({
    # Грудь (0)
    "жим лёжа": 0, "жим на груд": 0, "отжимани": 0, "разводка": 0,
    "кроссовер": 0, "бабочка": 0, "грудн": 0, "пек дек": 0,
    "bench press": 0, "chest press": 0, "chest fly": 0, "dips": 0,
    # Спина (1)
    "тяга верхнего": 1, "тяга нижнего": 1, "тяга в наклоне": 1, "становая тяга": 1,
    "горизонтальная тяга": 1, "подтягивани": 1, "широчайш": 1, "гиперэкстензи": 1,
    "deadlift": 1, "pulldown": 1, "pullup": 1, "pull-up": 1,
    # Плечи (2)
    "жим стоя": 2, "жим сидя": 2, "армейский жим": 2,
    "махи": 2, "дельт": 2, "шраги": 2,
    "overhead press": 2, "lateral raise": 2, "shoulder press": 2,
    # Бицепс (3)
    "сгибани рук": 3, "молоток": 3, "бицепс": 3,
    "bicep curl": 3, "hammer curl": 3,
    # Трицепс (4)
    "разгибани рук": 4, "французский жим": 4, "трицепс": 4,
    "tricep": 4, "pushdown": 4, "skull crusher": 4,
    # Пресс (5)
    "скручивани": 5, "планк": 5, "подъём ног": 5, "подъем ног": 5,
    "crunch": 5, "plank": 5, "sit-up": 5,
    # Квадрицепс (6)
    "приседани": 6, "жим ногами": 6, "выпад": 6, "разгибани ног": 6, "квадрицепс": 6,
    "squat": 6, "leg press": 6, "lunge": 6, "leg extension": 6,
    # Бицепс бедра (7)
    "сгибани ног": 7, "бицепс бедра": 7, "румынская тяга": 7,
    "hamstring": 7, "leg curl": 7, "romanian": 7,
    # Ягодицы (8)
    "ягодичный мостик": 8, "ягодиц": 8, "ягодич": 8, "отведени": 8,
    "hip thrust": 8, "glute": 8,
    # Икры (9)
    "подъём на носк": 9, "подъем на носк": 9, "икр": 9,
    "calf raise": 9, "calf": 9,
    # Кардио (10)
    "кардио": 10, "cardio": 10,
    # Общие (fallback — короткие, проверяются последними)
    "тяга": 1, "row": 1,
    "жим": 0,
    "сгибани": 3,
    "разгибани": 4,
    "пресс": 5,
}.items(), key=lambda x: -len(x[0]))


def _detect_muscle_index(name: str):
    name_lower = name.lower()
    for kw, idx in _EXERCISE_MUSCLE_MAP:
        if kw in name_lower:
            return idx
    return None


def _on_exercise_change():
    if not st.session_state.get("_w_exercise_input", ""):
        st.session_state.pop("_auto_mg_index", None)
    else:
        st.session_state["_need_muscle_detect"] = True


def get_chain_input(user_input: str) -> dict:
    _prog = get_active_program(name)
    if _prog:
        _prog_info = (f"Current training program «{_prog['title']}» "
                      f"(saved {_prog['updated_at'][:10]}):\n{_prog['raw_text'][:1500]}\n"
                      f"Take this program into account when giving advice and corrections.")
        if _active_tab == "program":
            _prog_info += ("\nIMPORTANT: The user is currently viewing the training program tab. "
                           "They want to discuss or modify this specific program. "
                           "Focus your response on the program structure, exercises, and scheduling.")
    else:
        _prog_info = ""
    return {
        "name": name, "age": age, "weight": weight, "height": height,
        "goal": goal, "level": level, "trainer_style": trainer_style,
        "weight_goal_info": _weight_goal_info,
        "active_program_info": _prog_info,
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
    _prog = get_active_program(name)
    _prog_info = (f"Current training program «{_prog['title']}» "
                  f"(saved {_prog['updated_at'][:10]}):\n{_prog['raw_text'][:1500]}\n"
                  f"Take this program into account when giving advice and corrections."
                  if _prog else "")
    return system_prompt.format(
        name=name, age=age, weight=weight, height=height,
        goal=goal, level=level, trainer_style=trainer_style,
        weight_goal_info=_weight_goal_info,
        active_program_info=_prog_info,
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
# ОПРЕДЕЛЕНИЕ АКТИВНОЙ ВКЛАДКИ через JS → query param
# ============================================================
components.html("""<script>
(function() {
    function syncTab() {
        try {
            var tabs = window.parent.document.querySelectorAll('[role="tab"]');
            var idx = 0;
            tabs.forEach(function(tab, i) {
                if (tab.getAttribute('aria-selected') === 'true') idx = i;
            });
            var url = new URL(window.parent.location.href);
            if (url.searchParams.get('_t') !== String(idx)) {
                url.searchParams.set('_t', String(idx));
                window.parent.history.replaceState(null, '', url.toString());
            }
        } catch(e) {}
    }
    window.parent.document.addEventListener('click', function(e) {
        if (e.target.closest('[role="tab"]')) { syncTab(); }
    }, true);
    syncTab();
})();
</script>""", height=0)

_TAB_NAMES = ["chat", "diary", "food", "analysis", "program"]
_t_raw = st.query_params.get("_t", "0")
_active_tab = _TAB_NAMES[int(_t_raw)] if _t_raw.isdigit() and int(_t_raw) < len(_TAB_NAMES) else "chat"

# ============================================================
# ВКЛАДКИ
# ============================================================
tab_chat, tab_diary, tab_food, tab_analysis, tab_program = st.tabs([
    t(lang, "tab_chat"), t(lang, "tab_diary"), t(lang, "tab_food"),
    t(lang, "tab_analysis"), t(lang, "tab_program")
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
    col_mic, _ = st.columns([0.12, 0.88])
    with col_mic:
        audio_bytes = audio_recorder(
            text="", recording_color="#e74c3c",
            neutral_color="#888888", icon_size="2x",
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

# Текстовый ввод + прикрепить файл
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

        # Извлекаем упражнения из ответа и показываем ссылки на YouTube
        _ex_extract_prompt = (
            f"Из следующего текста выпиши все названия упражнений в виде JSON-массива строк. "
            f"Если упражнений нет — верни пустой массив []. Только JSON, без объяснений.\n\n{response[:2000]}"
        )
        try:
            _ex_raw = llm_text.invoke(_ex_extract_prompt).content.strip()
            _ex_match = re.search(r'\[.*?\]', _ex_raw, re.DOTALL)
            _exercises_found = json.loads(_ex_match.group()) if _ex_match else []
        except Exception:
            _exercises_found = []

        if _exercises_found:
            st.session_state.sidebar_exercises = _exercises_found[:8]
            st.info(f"{t(lang, 'video_tutorials')}: нажми 🎬 в боковой панели", icon="🎬")

        # Автосохранение программы если тренер её составил
        _prog_keywords = ["день 1", "день 2", "day 1", "day 2", "week 1", "неделя",
                          "программа", "program", "план тренировок", "training plan",
                          "пн:", "вт:", "ср:", "чт:", "пт:", "mon:", "tue:", "wed:", "thu:", "fri:"]
        if any(kw in response.lower() for kw in _prog_keywords) and len(response) > 300:
            _prog_title_prompt = (
                f"Придумай короткое название (3-5 слов) для этой программы тренировок. "
                f"Только название, без кавычек и объяснений:\n\n{response[:500]}"
            )
            try:
                _prog_title = llm_text.invoke(_prog_title_prompt).content.strip()[:60]
            except Exception:
                _prog_title = "Программа тренировок"
            save_program(name, _prog_title, response)
            st.success(f"💾 {t(lang, 'program_saved')}: **{_prog_title}**")

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
            q_rest = st.number_input(t(lang, "rest_sec"), min_value=0, max_value=600, value=60, step=15, key="q_rest")
        col_save, col_skip = st.columns(2)
        with col_save:
            if st.button(t(lang, "btn_save"), use_container_width=True):
                add_exercise(name, str(date.today()), q_exercise, q_muscle, q_sets, q_reps, q_weight,
                             rest_sec=q_rest)
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

    # Предзаполнение из голоса
    _vp = st.session_state.pop("diary_voice_prefill", {})
    if _vp:
        st.info(f"🎙️ Распознано голосом: **{_vp.get('exercise', '')}** — проверь и нажми «Добавить»")

    # Название тренировки (хранится в session_state)
    if "workout_name" not in st.session_state:
        st.session_state.workout_name = ""
    w_name = st.text_input(
        t(lang, "workout_name"),
        value=st.session_state.workout_name,
        placeholder=t(lang, "workout_name_placeholder"),
        key="w_name_input",
    )
    st.session_state.workout_name = w_name

    _mg_voice = _vp.get("muscle_group")
    if _vp.get("exercise"):
        st.session_state["_w_exercise_input"] = _vp["exercise"]
        if _mg_voice and _mg_voice in MUSCLE_GROUPS:
            st.session_state["_auto_mg_index"] = MUSCLE_GROUPS.index(_mg_voice)
        else:
            st.session_state["_need_muscle_detect"] = True
    elif _mg_voice and _mg_voice in MUSCLE_GROUPS:
        st.session_state["_auto_mg_index"] = MUSCLE_GROUPS.index(_mg_voice)

    # LLM auto-detect muscle group when exercise name is typed or voice-filled without group
    _ex_for_detect = st.session_state.get("_w_exercise_input", "")
    if st.session_state.pop("_need_muscle_detect", False) and _ex_for_detect:
        with st.spinner(t(lang, "thinking")):
            _detect_prompt = (
                f"Определи группу мышц для упражнения: '{_ex_for_detect}'. "
                f"Ответь только одним значением из списка: {MUSCLE_GROUPS}. "
                f"Без объяснений."
            )
            _detected_mg = llm_text.invoke(_detect_prompt).content.strip()
        for _i, _mg in enumerate(MUSCLE_GROUPS):
            if _mg.lower() in _detected_mg.lower() or _detected_mg.lower() in _mg.lower():
                st.session_state["_auto_mg_index"] = _i
                break

    _mg_index = st.session_state.get("_auto_mg_index", 0)

    col1, col2 = st.columns(2)
    with col1:
        w_date = st.date_input(t(lang, "date"), value=date.today())
        _tc1, _tc2 = st.columns(2)
        with _tc1:
            w_start = st.time_input(t(lang, "workout_start"), value=_dt.time(9, 0), key="workout_start_time")
        with _tc2:
            w_end = st.time_input(t(lang, "workout_end"), value=_dt.time(10, 0), key="workout_end_time")
        if w_end > w_start:
            _dur_min = int((_dt.datetime.combine(_dt.date.today(), w_end) -
                            _dt.datetime.combine(_dt.date.today(), w_start)).total_seconds() // 60)
            _h, _m = _dur_min // 60, _dur_min % 60
            _dur_str = (f"**{_h} {t(lang,'hours_short')} {_m} {t(lang,'min_short')}**" if _dur_min >= 60
                        else f"**{_m} {t(lang,'min_short')}**")
            st.caption(f"{t(lang, 'duration')} {_dur_str}")
        w_exercise = st.text_input(t(lang, "exercise"),
                                   placeholder=t(lang, "exercise_placeholder"),
                                   key="_w_exercise_input",
                                   on_change=_on_exercise_change)
        
        # Показываем схему выполнения из ExerciseDB
        if w_exercise:
            _schema = get_exercise_schema(w_exercise)
            if _schema:
                st.info(_schema)
        
        w_muscle = st.selectbox(t(lang, "muscle_group"), MUSCLE_GROUPS, index=_mg_index)
        if w_muscle != MUSCLE_GROUPS[-1]:  # не показываем для кардио
            components.html(get_muscle_html(w_muscle, lang=lang), height=380)
    with col2:
        is_cardio = (w_muscle == MUSCLE_GROUPS[-1])  # последний элемент — Кардио
        
        # Показываем схему/кадр выполнения упражнения из локального каталога
        if w_exercise and w_muscle != MUSCLE_GROUPS[-1]:
            _gif_url = get_exercise_gif(w_exercise)
            if _gif_url:
                st.markdown(f"**📹 Техника выполнения:**")
                st.image(_gif_url, use_container_width=True, caption=w_exercise)

        if is_cardio:
            w_cardio_type = st.selectbox("Вид кардио", t(lang, "cardio_types"))
            w_duration = st.number_input("⏱️ Длительность (мин)", min_value=1, max_value=300, value=30)
            w_distance = st.number_input("📏 Дистанция (км)", min_value=0.0, max_value=200.0, value=0.0, step=0.1)
            w_avg_hr = st.number_input("❤️ Средний пульс (уд/мин)", min_value=0, max_value=250, value=0)
        else:
            w_sets = st.number_input(t(lang, "sets"), min_value=1, max_value=20,
                                     value=max(1, int(_vp.get("sets", 3))))
            w_reps = st.number_input(t(lang, "reps"), min_value=1, max_value=100,
                                     value=max(1, int(_vp.get("reps", 10))))
            w_weight = st.number_input(t(lang, "weight_kg"), min_value=0.0, max_value=500.0,
                                       value=float(_vp.get("weight", 0.0)), step=2.5)
            w_rest = st.number_input(t(lang, "rest_sec"), min_value=0, max_value=600,
                                     value=60, step=15)

    # Пульсовая зона (если кардио и пульс введён)
    if is_cardio and w_avg_hr > 0:
        max_hr = 220 - age
        pct = w_avg_hr / max_hr * 100
        _hr_zones = t(lang, "hr_zones")
        if pct < 60:
            zone, zone_name = 1, _hr_zones[0]
        elif pct < 70:
            zone, zone_name = 2, _hr_zones[1]
        elif pct < 80:
            zone, zone_name = 3, _hr_zones[2]
        elif pct < 90:
            zone, zone_name = 4, _hr_zones[3]
        else:
            zone, zone_name = 5, _hr_zones[4]
        colors = {1: "🟦", 2: "🟩", 3: "🟨", 4: "🟧", 5: "🟥"}
        st.info(f"{colors[zone]} **Зона {zone} — {zone_name}** ({pct:.0f}% от макс. пульса {max_hr})")

    w_notes = st.text_input(t(lang, "notes"), value=_vp.get("notes", ""),
                            placeholder=t(lang, "notes_placeholder"))

    col_add, col_del = st.columns([0.3, 0.7])
    with col_add:
        if st.button(t(lang, "add_exercise"), use_container_width=True):
            if w_exercise:
                _wstart = w_start.strftime("%H:%M")
                _wend = w_end.strftime("%H:%M")
                if is_cardio:
                    add_exercise(name, str(w_date), w_exercise, w_muscle,
                                 notes=w_notes, cardio_type=w_cardio_type,
                                 duration_min=w_duration, distance_km=w_distance,
                                 avg_hr=w_avg_hr,
                                 workout_start=_wstart, workout_end=_wend)
                else:
                    add_exercise(name, str(w_date), w_exercise, w_muscle,
                                 w_sets, w_reps, w_weight, w_notes,
                                 workout_start=_wstart, workout_end=_wend,
                                 rest_sec=w_rest)
                st.success(f"{t(lang, 'recorded')}: {w_exercise}")
                st.rerun()
            else:
                st.warning(t(lang, "enter_exercise"))
    with col_del:
        if st.button(t(lang, "delete_last"), use_container_width=True):
            delete_last_exercise(name)
            st.rerun()

    # Голосовой ввод упражнения
    st.caption(t(lang, "voice_add_exercise"))
    _mic_col, _ = st.columns([0.12, 0.88])
    with _mic_col:
        _diary_audio = audio_recorder(
            text="", recording_color="#e74c3c", neutral_color="#888888",
            icon_size="2x", key="diary_mic",
        )
    if _diary_audio and len(_diary_audio) > 1000 and _diary_audio != st.session_state.get("last_diary_audio"):
        st.session_state.last_diary_audio = _diary_audio
        with st.spinner(t(lang, "recognizing")):
            _diary_voice = transcribe_audio(_diary_audio)
        if _diary_voice:
            st.info(f"🎙️ {_diary_voice}")
            with st.spinner(t(lang, "thinking")):
                _parse_prompt = (
                    f"Распознай упражнение из текста: '{_diary_voice}'. "
                    f"Верни JSON: {{\"exercise\": \"\", \"muscle_group\": \"\", "
                    f"\"sets\": 0, \"reps\": 0, \"weight\": 0, \"notes\": \"\"}}. "
                    f"muscle_group должна быть из списка: {MUSCLE_GROUPS}. "
                    f"Верни только JSON, без объяснений."
                )
                _parsed_raw = llm_text.invoke(_parse_prompt).content.strip()
            try:
                _json_match = re.search(r'\{.*\}', _parsed_raw, re.DOTALL)
                if _json_match:
                    _p = json.loads(_json_match.group())
                    if _p.get("exercise"):
                        st.session_state.diary_voice_prefill = {
                            "exercise": _p["exercise"],
                            "muscle_group": _p.get("muscle_group", MUSCLE_GROUPS[0]),
                            "sets": int(_p.get("sets", 3)),
                            "reps": int(_p.get("reps", 10)),
                            "weight": float(_p.get("weight", 0)),
                            "notes": _p.get("notes", ""),
                        }
                        st.rerun()
            except Exception:
                st.warning(f"Не смог распознать: {_diary_voice}")

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
                    _ev_start = f"{w_date}T{w_start.strftime('%H:%M:%S')}"
                    _ev_end = f"{w_date}T{w_end.strftime('%H:%M:%S')}"
                    event = {
                        "summary": f"🏋️ {cal_title}",
                        "description": description,
                        "start": {"dateTime": _ev_start},
                        "end": {"dateTime": _ev_end},
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
        cols = t(lang, "table_cols")  # [Дата, Упражнение, Группа мышц, Подходы, Повторения, Вес, Заметки]
        _id_col = "__id__"
        rows = []
        for w in workouts:
            rows.append({
                _id_col:  w["id"],
                cols[0]:  w["date"],
                cols[1]:  w["exercise"],
                cols[2]:  w["muscle_group"],
                t(lang, "sets"):     w["sets"],
                t(lang, "reps"):     w["reps"],
                t(lang, "weight_kg"): w["weight"],
                cols[4]:  w["notes"] or "",
            })
        df = pd.DataFrame(rows)
        edited = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={_id_col: None},   # скрываем id
            key="workout_editor",
        )
        # Сохраняем изменённые строки
        changed = df.compare(edited).index.tolist()
        for idx in changed:
            row = edited.iloc[idx]
            update_exercise(
                row_id=int(row[_id_col]),
                exercise=row[cols[1]],
                muscle_group=row[cols[2]],
                sets=int(row[t(lang, "sets")]),
                reps=int(row[t(lang, "reps")]),
                weight_kg=float(row[t(lang, "weight_kg")]),
                notes=row[cols[4]],
            )
        if changed:
            st.success(t(lang, "recorded") + " ✓")
            st.rerun()
    else:
        st.info(t(lang, "no_workouts"))

# ============================================================
# ВКЛАДКА 3: ПИТАНИЕ
# ============================================================
@st.fragment
def _render_food_tab():
    st.subheader(t(lang, "food_title"))

    f_date = st.date_input(t(lang, "date"), value=date.today(), key="f_date")

    # Автозаполнение КБЖУ по названию продукта
    def _autofill_macros():
        _food = st.session_state.get("f_name", "").strip()
        _w = st.session_state.get("f_weight", 100.0)
        if not _food:
            return
        _prompt = (
            f"Nutrition facts for '{_food}', {_w}g portion. "
            "Return ONLY JSON: {\"calories\": 0, \"protein\": 0, \"fat\": 0, \"carbs\": 0}. "
            "All values as numbers per the given weight. No text, no markdown."
        )
        try:
            _resp = llm_text.invoke(_prompt).content.strip()
            _m = re.search(r'\{.*\}', _resp, re.DOTALL)
            if _m:
                _d = json.loads(_m.group())
                st.session_state["f_cal"] = float(_d.get("calories", 0))
                st.session_state["f_prot"] = float(_d.get("protein", 0))
                st.session_state["f_fat"] = float(_d.get("fat", 0))
                st.session_state["f_carb"] = float(_d.get("carbs", 0))
        except Exception:
            pass

    # --- Форма добавления ---
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        f_meal = st.selectbox(t(lang, "meal_type"), t(lang, "meal_types"), key="f_meal")
        f_name = st.text_input(
            t(lang, "food_name"), placeholder=t(lang, "food_placeholder"),
            key="f_name", on_change=_autofill_macros,
        )
        f_weight = st.number_input(
            t(lang, "food_weight"), min_value=0.0, max_value=5000.0,
            value=100.0, step=10.0, key="f_weight", on_change=_autofill_macros,
        )
    with col_f2:
        f_cal = st.number_input(t(lang, "calories"), min_value=0.0, max_value=5000.0, step=1.0, key="f_cal")
        f_prot = st.number_input(t(lang, "protein"), min_value=0.0, max_value=500.0, step=0.5, key="f_prot")
        f_fat = st.number_input(t(lang, "fat"), min_value=0.0, max_value=500.0, step=0.5, key="f_fat")
        f_carb = st.number_input(t(lang, "carbs"), min_value=0.0, max_value=500.0, step=0.5, key="f_carb")

    col_fadd, col_fdel = st.columns([0.3, 0.7])
    with col_fadd:
        if st.button(t(lang, "add_food"), use_container_width=True):
            if f_name:
                add_food(name, str(f_date), f_meal, f_name,
                         f_cal, f_prot, f_fat, f_carb, f_weight)
                # Сбрасываем поля для следующего продукта
                for _k in ("f_name", "f_cal", "f_prot", "f_fat", "f_carb", "f_weight"):
                    st.session_state.pop(_k, None)
                st.success(f"{t(lang, 'recorded')}: {f_name}")
                st.rerun()
            else:
                st.warning(t(lang, "enter_exercise"))
    with col_fdel:
        if st.button(t(lang, "delete_last_food"), use_container_width=True):
            delete_last_food(name)
            st.rerun()

    # Голосовой ввод еды
    st.caption(t(lang, "voice_add_food"))
    _, _fmic_col, _ = st.columns([0.45, 0.1, 0.45])
    with _fmic_col:
        _food_audio = audio_recorder(
            text="", recording_color="#27ae60", neutral_color="#888888",
            icon_size="sm", key="food_mic",
        )
    if _food_audio and len(_food_audio) > 1000 and _food_audio != st.session_state.get("last_food_audio"):
        st.session_state.last_food_audio = _food_audio
        with st.spinner(t(lang, "recognizing")):
            _food_voice = transcribe_audio(_food_audio)
        if _food_voice:
            st.info(f"🎙️ {_food_voice}")
            with st.spinner(t(lang, "thinking")):
                _food_parse_prompt = (
                    f"Extract food entry from: '{_food_voice}'. "
                    f"Return JSON: {{\"food_name\": \"\", \"meal_type\": \"\", "
                    f"\"weight_g\": 0, \"calories\": 0, \"protein\": 0, \"fat\": 0, \"carbs\": 0}}. "
                    f"meal_type must be one of: {t(lang, 'meal_types')}. "
                    f"If calories/macros not mentioned, estimate based on the food and weight. "
                    f"Return only valid JSON, no explanation."
                )
                _food_raw = llm_text.invoke(_food_parse_prompt).content.strip()
            try:
                _fm = re.search(r'\{.*\}', _food_raw, re.DOTALL)
                if _fm:
                    _fp = json.loads(_fm.group())
                    if _fp.get("food_name"):
                        add_food(name, str(f_date),
                                 _fp.get("meal_type", f_meal),
                                 _fp["food_name"],
                                 float(_fp.get("calories", 0)),
                                 float(_fp.get("protein", 0)),
                                 float(_fp.get("fat", 0)),
                                 float(_fp.get("carbs", 0)),
                                 float(_fp.get("weight_g", 0)))
                        st.success(f"{t(lang, 'recorded')}: {_fp['food_name']}")
                        st.rerun()
            except Exception:
                st.warning(f"Не смог распознать: {_food_voice}")

    # Добавление по фото
    with st.expander("📷 " + t(lang, "food_name") + " по фото", expanded=False):
        food_photo = st.file_uploader(
            "photo", type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed", key="food_photo"
        )
        food_photo_meal = st.selectbox(t(lang, "meal_type"), t(lang, "meal_types"), key="fphoto_meal")
        if food_photo and st.button(t(lang, "analyzing_food"), key="analyze_food_photo"):
            with st.spinner(t(lang, "analyzing_food")):
                _img_bytes = food_photo.read()
                _b64_img = base64.b64encode(_img_bytes).decode()
                _photo_prompt = (
                    "Analyze this food photo. Return JSON: "
                    "{\"food_name\": \"\", \"weight_g\": 0, \"calories\": 0, "
                    "\"protein\": 0, \"fat\": 0, \"carbs\": 0}. "
                    "Estimate portions from the photo. Return only valid JSON."
                )
                _photo_resp = llm_vision.invoke([HumanMessage(content=[
                    {"type": "image_url", "image_url": {"url": f"data:{food_photo.type};base64,{_b64_img}"}},
                    {"type": "text", "text": _photo_prompt},
                ])]).content.strip()
            try:
                _pm = re.search(r'\{.*\}', _photo_resp, re.DOTALL)
                if _pm:
                    _pp = json.loads(_pm.group())
                    if _pp.get("food_name"):
                        add_food(name, str(f_date), food_photo_meal,
                                 _pp["food_name"],
                                 float(_pp.get("calories", 0)),
                                 float(_pp.get("protein", 0)),
                                 float(_pp.get("fat", 0)),
                                 float(_pp.get("carbs", 0)),
                                 float(_pp.get("weight_g", 0)))
                        st.success(f"{t(lang, 'recorded')}: {_pp['food_name']} — {_pp.get('calories', 0):.0f} ккал")
                        st.rerun()
            except Exception:
                st.error("Не удалось распознать блюдо на фото")

    # Дневные итоги
    st.divider()
    _totals = get_daily_totals(name, str(f_date))
    _eaten = _totals["calories"]
    _remaining = DAILY_KCAL - _eaten
    _pct = min(int(_eaten / DAILY_KCAL * 100), 100) if DAILY_KCAL > 0 else 0

    st.markdown(f"**{t(lang, 'daily_total')}:** {_eaten:.0f} / {DAILY_KCAL} ккал")
    st.progress(_pct)

    _tc1, _tc2, _tc3, _tc4 = st.columns(4)
    _delta_color = "inverse" if _remaining < 0 else "normal"
    _tc1.metric(
        "🔥 " + t(lang, "calories"),
        f"{_eaten:.0f}",
        delta=f"{_remaining:+.0f} ккал",
        delta_color=_delta_color,
    )
    _tc2.metric("🥩 " + t(lang, "protein"), f"{_totals['protein']:.0f}г")
    _tc3.metric("🧈 " + t(lang, "fat"), f"{_totals['fat']:.0f}г")
    _tc4.metric("🍞 " + t(lang, "carbs"), f"{_totals['carbs']:.0f}г")

    # История питания за день
    st.subheader(t(lang, "food_history"))
    _day_food = get_food_by_date(name, str(f_date))
    if _day_food:
        for _entry in _day_food:
            _details = f"{_entry['food_name']}"
            if _entry["weight_g"]:
                _details += f" {_entry['weight_g']:.0f}г"
            _macro = []
            if _entry["calories"]:
                _macro.append(f"🔥{_entry['calories']:.0f}")
            if _entry["protein"]:
                _macro.append(f"Б{_entry['protein']:.0f}")
            if _entry["fat"]:
                _macro.append(f"Ж{_entry['fat']:.0f}")
            if _entry["carbs"]:
                _macro.append(f"У{_entry['carbs']:.0f}")
            if _macro:
                _details += "  " + " ".join(_macro)
            st.markdown(f"**{_entry['meal_type']}** — {_details}")
    else:
        st.info(t(lang, "no_food"))

with tab_food:
    _render_food_tab()

# ============================================================
# ВКЛАДКА 4: АНАЛИЗ
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

# ============================================================
# ВКЛАДКА 5: ПРОГРАММА ТРЕНИРОВОК
# ============================================================
def _parse_program_to_calendar(program_text: str) -> list[dict]:
    """Ask LLM to parse program into weeks × days structure."""
    _prompt = f"""You are a JSON converter. Parse this training program into structured JSON.

Return ONLY a valid JSON array with this exact structure:
[
  {{
    "week": 1,
    "days": [
      {{"day": 0, "label": "Monday", "exercises": ["Bench press 3x10", "Push-ups 3x15"], "rest": false}},
      {{"day": 1, "label": "Tuesday", "exercises": [], "rest": true}},
      {{"day": 2, "label": "Wednesday", "exercises": ["Squats 4x8", "Lunges 3x12"], "rest": false}},
      {{"day": 3, "label": "Thursday", "exercises": [], "rest": true}},
      {{"day": 4, "label": "Friday", "exercises": ["Pull-ups 3x8", "Rows 3x10"], "rest": false}},
      {{"day": 5, "label": "Saturday", "exercises": [], "rest": true}},
      {{"day": 6, "label": "Sunday", "exercises": [], "rest": true}}
    ]
  }}
]

Rules:
- days array must always have exactly 7 elements (Mon=0 to Sun=6)
- exercises: short strings like "Exercise name Nsets x Nreps"
- rest: true if no training that day
- If program has no explicit weeks, treat it as week 1
- Output ONLY the JSON array, no markdown, no explanation

Program text:
{program_text[:3000]}"""

    try:
        _raw = llm_text.invoke(_prompt).content.strip()
        # Strip markdown code blocks if present
        _raw = re.sub(r'^```(?:json)?\s*', '', _raw)
        _raw = re.sub(r'\s*```$', '', _raw)
        _m = re.search(r'\[.*\]', _raw, re.DOTALL)
        if _m:
            return json.loads(_m.group())
    except Exception:
        pass
    return []


def _weeks_to_text(weeks: list, day_labels: list, rest_label: str, week_label: str) -> str:
    """Convert structured weeks JSON back to readable text for DB storage."""
    lines = []
    for week in weeks:
        lines.append(f"{week_label} {week.get('week', 1)}:")
        for day in week.get("days", []):
            i = day.get("day", 0)
            label = day_labels[i] if i < len(day_labels) else str(i)
            if day.get("rest") or not day.get("exercises"):
                lines.append(f"  {label}: {rest_label}")
            else:
                exs = ", ".join(day.get("exercises", []))
                lines.append(f"  {label}: {exs}")
        lines.append("")
    return "\n".join(lines)


_SUNDAY_FIRST_LANGS = {"he"}

def _render_program_calendar(weeks: list, lang_code: str, prog_id: int, cache_key: str):
    day_labels = t(lang_code, "week_days")
    rest_label = t(lang_code, "rest_day")
    week_label = t(lang_code, "program_week")
    editing    = st.session_state.get("prog_editing")  # (week_idx, day_idx) or None
    # Sun-first locales display order: Sun(6), Mon(0)..Sat(5)
    day_order = [6, 0, 1, 2, 3, 4, 5] if lang_code in _SUNDAY_FIRST_LANGS else list(range(7))

    for wi, week in enumerate(weeks):
        st.markdown(f"#### {week_label} {week.get('week', wi + 1)}")
        days = week.get("days", [])
        while len(days) < 7:
            days.append({"day": len(days), "exercises": [], "rest": True})

        cols = st.columns(7)
        for di, col in enumerate(cols):
            with col:
                day_data = days[day_order[di]]
                is_rest  = day_data.get("rest", True) or not day_data.get("exercises")
                bg       = "#f5f5f5" if is_rest else "#e8f4fd"
                border   = "#ccc"    if is_rest else "#3498db"
                exs      = day_data.get("exercises", [])
                items_html = "".join(
                    f"<div style='font-size:11px;margin-top:4px;padding:3px 5px;"
                    f"background:#fff;border-radius:4px;"
                    f"border-left:2px solid #3498db;word-break:break-word'>• {ex}</div>"
                    for ex in exs
                ) if not is_rest else (
                    f"<div style='color:#aaa;font-size:12px;margin-top:8px'>💤 {rest_label}</div>"
                )
                st.markdown(
                    f"<div style='background:{bg};border-radius:8px;padding:8px;"
                    f"min-height:110px;border-top:3px solid {border}'>"
                    f"<b style='font-size:12px;color:#333'>{day_labels[di]}</b>"
                    f"{items_html}</div>",
                    unsafe_allow_html=True,
                )
                # Кнопки для каждого упражнения → видео в сайдбаре
                if not is_rest:
                    for ei, ex in enumerate(exs):
                        ex_short = ex.split(" ")[0:3]
                        ex_label = " ".join(ex_short)[:20]
                        if st.button(f"▶ {ex_label}", key=f"vid_{wi}_{di}_{ei}",
                                     use_container_width=True):
                            st.session_state["sidebar_video_exercise"] = ex
                            st.session_state.sidebar_section = "video"
                            st.session_state["sidebar_exercises"] = [ex]
                            st.rerun()
                if st.button("✏️", key=f"edit_{wi}_{di}", use_container_width=True):
                    st.session_state["prog_editing"] = (wi, day_order[di])
                    st.rerun()

        # Edit form — показываем под строкой недели если выбран день этой недели
        if editing and editing[0] == wi:
            _, edi = editing
            day_data_e = days[edi]
            is_rest_e  = day_data_e.get("rest", True) or not day_data_e.get("exercises")
            st.divider()
            _edi_label = day_labels[day_order.index(edi)]
            st.markdown(f"**✏️ {week_label} {week.get('week', wi+1)}, {_edi_label}**")

            rest_toggle = st.checkbox(f"💤 {rest_label}", value=is_rest_e,
                                      key=f"rest_chk_{wi}_{edi}")
            if not rest_toggle:
                _ekey = f"edit_exs_{wi}_{edi}"
                if _ekey not in st.session_state:
                    st.session_state[_ekey] = list(day_data_e.get("exercises", []))
                _exs = st.session_state[_ekey]
                _mgs = t(lang_code, "muscle_groups")

                # ── Current exercises list ──────────────────────────
                if _exs:
                    for _ei, _ex in enumerate(_exs):
                        _ca, _cb = st.columns([0.87, 0.13])
                        with _ca:
                            st.markdown(f"• {_ex}")
                        with _cb:
                            if st.button("❌", key=f"rm_{wi}_{edi}_{_ei}",
                                         use_container_width=True):
                                st.session_state[_ekey].pop(_ei)
                                st.rerun()
                else:
                    st.caption("—")

                st.markdown("---")

                # ── Add from catalog ────────────────────────────────
                _cA, _cB, _cC = st.columns([0.30, 0.52, 0.18])
                with _cA:
                    _mg_i = st.selectbox(
                        "mg", range(len(_mgs)),
                        format_func=lambda i: _mgs[i],
                        label_visibility="collapsed",
                        key=f"mg_{wi}_{edi}",
                    )
                with _cB:
                    _cat_list = _EXERCISE_CATALOG[_mg_i] if _mg_i < len(_EXERCISE_CATALOG) else []
                    _ex_pick = st.selectbox(
                        "ex", _cat_list,
                        label_visibility="collapsed",
                        key=f"exp_{wi}_{edi}",
                    )
                with _cC:
                    if st.button("➕", key=f"addc_{wi}_{edi}",
                                 use_container_width=True) and _ex_pick:
                        if _ex_pick not in _exs:
                            st.session_state[_ekey].append(_ex_pick)
                        st.rerun()

                # ── Превью выбранного упражнения ────────────────────
                if _ex_pick:
                    _lookup = _en_name_for(_ex_pick, _mg_i)
                    _prev_gif = get_exercise_gif(_lookup)
                    _prev_schema = get_exercise_schema(_lookup)
                    if _prev_gif or _prev_schema:
                        with st.expander(f"📷 {_ex_pick}", expanded=True):
                            if _prev_gif:
                                st.image(_prev_gif, use_container_width=True)
                            if _prev_schema:
                                st.caption(_prev_schema)

                # ── Add custom exercise ─────────────────────────────
                _cX, _cY = st.columns([0.82, 0.18])
                with _cX:
                    _custom = st.text_input(
                        "own", label_visibility="collapsed",
                        placeholder="Bench Press 3x10 @ 80 kg",
                        key=f"cust_{wi}_{edi}",
                    )
                with _cY:
                    if st.button("➕ +", key=f"addx_{wi}_{edi}",
                                 use_container_width=True) and _custom.strip():
                        st.session_state[_ekey].append(_custom.strip())
                        st.session_state[f"cust_{wi}_{edi}"] = ""
                        st.rerun()

            col_s, col_c = st.columns(2)
            with col_s:
                if st.button(f"💾 {t(lang_code, 'btn_save')}", key=f"save_{wi}_{edi}",
                             use_container_width=True):
                    if rest_toggle:
                        weeks[wi]["days"][edi] = {"day": edi, "exercises": [], "rest": True}
                    else:
                        _saved = st.session_state.get(f"edit_exs_{wi}_{edi}", [])
                        weeks[wi]["days"][edi] = {"day": edi, "exercises": _saved, "rest": False}
                    st.session_state[cache_key] = weeks
                    new_text = _weeks_to_text(weeks, day_labels, rest_label, week_label)
                    update_program_text(prog_id, new_text)
                    st.session_state.pop("prog_editing", None)
                    st.session_state.pop(f"edit_exs_{wi}_{edi}", None)
                    st.success(t(lang_code, "program_saved"))
                    st.rerun()
            with col_c:
                if st.button("✖ Отмена", key=f"cancel_{wi}_{edi}", use_container_width=True):
                    st.session_state.pop("prog_editing", None)
                    st.session_state.pop(f"edit_exs_{wi}_{edi}", None)
                    st.rerun()
            st.divider()


with tab_program:
    st.subheader(t(lang, "tab_program"))

    active = get_active_program(name)
    all_progs = get_all_programs(name)

    if active:
        st.success(f"✅ {t(lang, 'active_program')}: **{active['title']}**  "
                   f"— {active['updated_at'][:10]}")

        # Переключатель вид
        _prog_view = st.radio(
            "view", [t(lang, "view_calendar"), t(lang, "view_text")],
            horizontal=True, label_visibility="collapsed", key="prog_view_toggle"
        )

        if _prog_view == t(lang, "view_calendar"):
            # Парсим программу в структуру (кэшируем по id программы)
            _cache_key = f"prog_calendar_{active['id']}"
            if _cache_key not in st.session_state:
                with st.spinner(t(lang, "thinking")):
                    st.session_state[_cache_key] = _parse_program_to_calendar(active["raw_text"])
            _weeks = st.session_state[_cache_key]
            if _weeks:
                _render_program_calendar(_weeks, lang, active["id"], _cache_key)
            else:
                st.warning("Не удалось распознать структуру программы. Переключись на режим 'Текст'.")

        else:
            edited_text = st.text_area(
                t(lang, "program_text"),
                value=active["raw_text"],
                height=420,
                key="program_edit_area",
            )
            col_save, col_ask = st.columns(2)
            with col_save:
                if st.button(f"💾 {t(lang, 'btn_save')}", use_container_width=True):
                    update_program_text(active["id"], edited_text)
                    # Сбрасываем кэш календаря чтобы перепарсить
                    st.session_state.pop(f"prog_calendar_{active['id']}", None)
                    st.success(t(lang, "program_saved"))
                    st.rerun()
            with col_ask:
                if st.button(f"🤖 {t(lang, 'program_ask_correction')}", use_container_width=True):
                    _diary_text = get_workouts_as_text(name, limit=30)
                    _correction_prompt = (
                        f"Вот моя текущая программа тренировок:\n\n{edited_text}\n\n"
                        f"Вот мой дневник тренировок за последнее время:\n\n{_diary_text}\n\n"
                        f"Проанализируй программу с учётом моих реальных результатов. "
                        f"Предложи конкретные корректировки и верни ПОЛНУЮ обновлённую программу."
                    )
                    with st.chat_message("assistant"):
                        with st.spinner(t(lang, "thinking")):
                            _corr_resp = chain.invoke(get_chain_input(_correction_prompt))
                        st.markdown(_corr_resp)
                    if st.button(f"💾 {t(lang, 'program_saved')} ← применить ответ тренера",
                                 key="apply_correction", use_container_width=True):
                        update_program_text(active["id"], _corr_resp)
                        st.session_state.pop(f"prog_calendar_{active['id']}", None)
                        st.success(t(lang, "program_saved"))
                        st.rerun()
    else:
        st.info(t(lang, "no_program"))
        if st.button(f"🤖 {t(lang, 'program_generate')}", use_container_width=True):
            _gen_prompt = (
                f"Составь мне персональную программу тренировок на 4 недели. "
                f"Учти мои данные, цель и уровень подготовки. "
                f"Структурируй по дням недели с конкретными упражнениями, "
                f"подходами, повторениями и весом."
            )
            with st.chat_message("assistant"):
                with st.spinner(t(lang, "thinking")):
                    _gen_resp = chain.invoke(get_chain_input(_gen_prompt))
                st.markdown(_gen_resp)
            # Автосохранение сгенерированной программы
            try:
                _title_resp = llm_text.invoke(
                    f"Придумай короткое название (3-5 слов) для этой программы тренировок. "
                    f"Только название, без кавычек:\n\n{_gen_resp[:500]}"
                ).content.strip()[:60]
            except Exception:
                _title_resp = t(lang, "tab_program")
            save_program(name, _title_resp, _gen_resp)
            st.success(f"💾 {t(lang, 'program_saved')}: **{_title_resp}**")
            st.rerun()

    # ── Подсказка — чат доступен на вкладке Чат ─────────────
    if active:
        st.divider()
        st.info(f"💬 {t(lang, 'program_chat_hint')}", icon="🤖")

    # История программ
    if len(all_progs) > 1:
        st.divider()
        st.subheader(t(lang, "program_history"))
        for p in all_progs:
            _active_mark = "✅ " if p["is_active"] else ""
            col_lbl, col_btn = st.columns([0.75, 0.25])
            with col_lbl:
                st.markdown(f"{_active_mark}**{p['title']}** — {p['created_at'][:10]}")
            with col_btn:
                if not p["is_active"]:
                    if st.button(t(lang, "program_activate"), key=f"act_{p['id']}",
                                 use_container_width=True):
                        activate_program(name, p["id"])
                        st.rerun()
