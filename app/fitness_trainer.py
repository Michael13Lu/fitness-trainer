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
from memory_store import load_messages, save_message, clear_history
from workout_store import (add_exercise, get_workouts, get_muscle_summary,
                           get_workouts_as_text, delete_last_exercise)

load_dotenv()

st.set_page_config(page_title="Фитнес-тренер", page_icon="💪", layout="wide")
st.title("💪 Персональный фитнес-тренер")

with st.sidebar:
    st.header("👤 Твой профиль")
    name = st.text_input("Имя", value="Михаил")
    age = st.number_input("Возраст", min_value=10, max_value=100, value=25)
    weight = st.number_input("Вес (кг)", min_value=30, max_value=200, value=75)
    height = st.number_input("Рост (см)", min_value=100, max_value=250, value=175)
    goal = st.selectbox("Цель", ["Похудеть", "Набрать мышечную массу", "Поддерживать форму", "Улучшить выносливость"])
    level = st.selectbox("Уровень подготовки", ["Новичок", "Средний", "Продвинутый"])
    trainer_style = st.selectbox("Стиль тренера", ["Мотивирующий", "Строгий", "Мягкий и поддерживающий"])
    st.divider()
    voice_response = st.toggle("🔊 Тренер говорит вслух", value=False)

    if st.button("🗑️ Очистить чат"):
        clear_history(name)
        st.session_state.history = ChatMessageHistory()
        st.session_state.messages = []
        st.rerun()

# Загружаем историю из БД при первом запуске сессии
if "history" not in st.session_state:
    st.session_state.history = ChatMessageHistory()
    saved = load_messages(name)
    for msg in saved:
        if msg["role"] == "user":
            st.session_state.history.add_user_message(msg["content"])
        else:
            st.session_state.history.add_ai_message(msg["content"])

if "messages" not in st.session_state:
    st.session_state.messages = load_messages(name)

if "loaded_for" not in st.session_state:
    st.session_state.loaded_for = name
elif st.session_state.loaded_for != name:
    # Имя изменилось — загружаем историю другого пользователя
    st.session_state.history = ChatMessageHistory()
    saved = load_messages(name)
    for msg in saved:
        if msg["role"] == "user":
            st.session_state.history.add_user_message(msg["content"])
        else:
            st.session_state.history.add_ai_message(msg["content"])
    st.session_state.messages = load_messages(name)
    st.session_state.loaded_for = name

llm_text = ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)
llm_vision = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0.7)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

system_prompt = """Ты — персональный фитнес-тренер и диетолог.

Информация о клиенте:
- Имя: {name}
- Возраст: {age} лет
- Вес: {weight} кг, Рост: {height} см
- Цель: {goal}
- Уровень подготовки: {level}
- Твой стиль общения: {trainer_style}

Ты даёшь конкретные советы по тренировкам и питанию, учитывая профиль клиента.
Мотивируй и поддерживай. Отвечай на русском языке. Будь конкретным и практичным."""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])
chain = prompt | llm_text | StrOutputParser()


def transcribe_audio(audio_bytes: bytes) -> str:
    result = groq_client.audio.transcriptions.create(
        file=("voice.wav", audio_bytes),
        model="whisper-large-v3",
        language="ru",
    )
    return result.text


def get_system_text():
    return system_prompt.format(
        name=name, age=age, weight=weight, height=height,
        goal=goal, level=level, trainer_style=trainer_style
    )


def extract_text_from_file(file) -> str:
    """Извлекает текст из PDF или CSV файла."""
    if file.name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file.read()))
        return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    elif file.name.endswith(".csv"):
        df = pd.read_csv(file)
        return df.to_string(index=False)
    return ""


def speak(text: str):
    """Озвучивает текст через браузер (Web Speech API)."""
    clean = text.replace("`", "").replace("*", "").replace("#", "")
    js = f"""
    <script>
    window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance({json.dumps(clean)});
    u.lang = 'ru-RU';
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
            {"type": "text", "text": user_text or "Проанализируй фото и дай совет исходя из моего профиля."},
        ]),
    ]
    return llm_vision.invoke(messages).content


# === ВКЛАДКИ ===
tab_chat, tab_diary, tab_analysis = st.tabs(["💬 Чат с тренером", "📓 Дневник тренировок", "📊 Анализ прогресса"])

# ============================================================
# ВКЛАДКА 1: ЧАТ
# ============================================================
with tab_chat:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("image"):
                st.image(msg["image"], width=200)
            st.markdown(msg["content"])

# --- Микрофон: маленькая кнопка по центру над полем ввода ---
st.markdown(
    "<div style='display:flex; justify-content:center; margin-bottom:-20px'>",
    unsafe_allow_html=True,
)
_, col_mic, _ = st.columns([0.48, 0.04, 0.48])
with col_mic:
    audio_bytes = audio_recorder(
        text="", recording_color="#e74c3c",
        neutral_color="#888888", icon_size="sm",
    )
st.markdown("</div>", unsafe_allow_html=True)

# --- Голосовой ввод ---
if audio_bytes and len(audio_bytes) > 1000 and audio_bytes != st.session_state.get("last_audio"):
    st.session_state.last_audio = audio_bytes
    with st.spinner("Распознаю речь..."):
        voice_text = transcribe_audio(audio_bytes)
    if voice_text:
        with st.chat_message("user"):
            st.markdown(f"🎙️ {voice_text}")
        st.session_state.messages.append({"role": "user", "content": f"🎙️ {voice_text}"})
        with st.chat_message("assistant"):
            with st.spinner("Тренер думает..."):
                response = chain.invoke({
                    "name": name, "age": age, "weight": weight, "height": height,
                    "goal": goal, "level": level, "trainer_style": trainer_style,
                    "history": st.session_state.history.messages,
                    "input": voice_text,
                })
            st.markdown(response)
        if voice_response:
            speak(response)
        st.session_state.history.add_user_message(voice_text)
        st.session_state.history.add_ai_message(response)
        save_message(name, "user", voice_text)
        save_message(name, "assistant", response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# --- Текст + фото/файл в одном поле ---
msg = st.chat_input(
    "Напиши тренеру или прикрепи фото/файл  📎",
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
        "content": user_input or (f"📄 {attached.name}" if attached else "_(сообщение)_"),
    })

    with st.chat_message("assistant"):
        with st.spinner("Тренер думает..."):
            if is_image:
                image_data = attached.read()
                response = analyze_with_image(image_data, attached.type, user_input)
            elif is_doc:
                file_text = extract_text_from_file(attached)
                if attached.name.endswith(".pdf"):
                    doc_prompt = f"Вот мои анализы или медицинский документ. Проанализируй и дай рекомендации по тренировкам и питанию:\n\n{file_text[:4000]}"
                else:
                    doc_prompt = f"Вот мои данные о питании из приложения. Проанализируй рацион и дай рекомендации:\n\n{file_text[:4000]}"
                response = chain.invoke({
                    "name": name, "age": age, "weight": weight, "height": height,
                    "goal": goal, "level": level, "trainer_style": trainer_style,
                    "history": st.session_state.history.messages,
                    "input": doc_prompt,
                })
            else:
                response = chain.invoke({
                    "name": name, "age": age, "weight": weight, "height": height,
                    "goal": goal, "level": level, "trainer_style": trainer_style,
                    "history": st.session_state.history.messages,
                    "input": user_input,
                })
        st.markdown(response)

    if voice_response:
        speak(response)
    st.session_state.history.add_user_message(user_input or "[файл]")
    st.session_state.history.add_ai_message(response)
    save_message(name, "user", user_input or "[файл]")
    save_message(name, "assistant", response)
    st.session_state.messages.append({"role": "assistant", "content": response})

# ============================================================
# ВКЛАДКА 2: ДНЕВНИК ТРЕНИРОВОК
# ============================================================
MUSCLE_GROUPS = [
    "Грудь", "Спина", "Плечи", "Бицепс", "Трицепс",
    "Пресс", "Квадрицепс", "Бицепс бедра", "Ягодицы", "Икры", "Кардио"
]

with tab_diary:
    st.subheader("Записать тренировку")

    col1, col2 = st.columns(2)
    with col1:
        w_date = st.date_input("Дата", value=date.today())
        w_exercise = st.text_input("Упражнение", placeholder="Жим лёжа, Приседания...")
        w_muscle = st.selectbox("Группа мышц", MUSCLE_GROUPS)
    with col2:
        w_sets = st.number_input("Подходы", min_value=1, max_value=20, value=3)
        w_reps = st.number_input("Повторения", min_value=1, max_value=100, value=10)
        w_weight = st.number_input("Вес (кг)", min_value=0.0, max_value=500.0, value=0.0, step=2.5)

    w_notes = st.text_input("Заметки (необязательно)", placeholder="Хорошо пошло, болело плечо...")

    col_add, col_del = st.columns([0.3, 0.7])
    with col_add:
        if st.button("➕ Добавить", use_container_width=True):
            if w_exercise:
                add_exercise(name, str(w_date), w_exercise, w_muscle,
                             w_sets, w_reps, w_weight, w_notes)
                st.success(f"Записано: {w_exercise}")
                st.rerun()
            else:
                st.warning("Введи название упражнения")
    with col_del:
        if st.button("↩️ Удалить последнюю запись", use_container_width=True):
            delete_last_exercise(name)
            st.rerun()

    st.divider()
    st.subheader("История тренировок")
    workouts = get_workouts(name, limit=50)
    if workouts:
        df = pd.DataFrame(workouts)
        df.columns = ["Дата", "Упражнение", "Группа мышц", "Подходы", "Повторения", "Вес (кг)", "Заметки"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Тренировок ещё нет. Добавь первую!")

# ============================================================
# ВКЛАДКА 3: АНАЛИЗ ПРОГРЕССА
# ============================================================
with tab_analysis:
    st.subheader("Анализ тренировок с тренером")

    workouts_text = get_workouts_as_text(name, limit=50)
    muscle_summary = get_muscle_summary(name)

    # Быстрая сводка
    st.markdown("**Сводка по группам мышц:**")
    st.code(muscle_summary)

    st.divider()

    # Кнопки быстрого анализа
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        analyze_all = st.button("🔍 Полный анализ прогресса", use_container_width=True)
    with col_b:
        analyze_weak = st.button("⚠️ Слабые места", use_container_width=True)
    with col_c:
        analyze_plan = st.button("📋 Новый план на основе данных", use_container_width=True)

    # Выбор конкретной группы мышц
    st.divider()
    selected_muscle = st.selectbox("Анализ конкретной группы мышц:", ["— Выбери —"] + MUSCLE_GROUPS)
    analyze_muscle = st.button("🎯 Анализировать эту группу", use_container_width=False)

    # Выполняем анализ
    analysis_prompt = None

    if analyze_all:
        analysis_prompt = f"""Вот мой дневник тренировок:

{workouts_text}

Сделай полный анализ:
1. Есть ли прогресс (рост весов/объёма)?
2. Какие мышцы проработаны хорошо, какие отстают?
3. Есть ли дисбаланс между мышечными группами?
4. Риски травм?
5. Конкретные рекомендации для улучшения."""

    elif analyze_weak:
        analysis_prompt = f"""Вот мой дневник тренировок:

{workouts_text}

Определи мои слабые места:
- Какие мышцы тренируются редко или с малым весом?
- Где нет прогресса?
- Что нужно усилить исходя из моей цели: {goal}?"""

    elif analyze_plan:
        analysis_prompt = f"""Вот мой дневник тренировок за последнее время:

{workouts_text}

На основе этих данных составь новый оптимальный план тренировок на следующие 2 недели.
Учти мою цель: {goal}, уровень: {level}.
Укажи конкретные упражнения, подходы, повторения и рекомендуемый вес."""

    elif analyze_muscle and selected_muscle != "— Выбери —":
        analysis_prompt = f"""Вот мой дневник тренировок:

{workouts_text}

Сделай детальный анализ группы мышц: **{selected_muscle}**
1. Сколько раз тренировалась эта группа?
2. Есть ли прогресс в весах и объёме?
3. Достаточно ли нагрузки для моей цели ({goal})?
4. Какие упражнения добавить или улучшить?
5. Мотивирующее заключение."""

    if analysis_prompt:
        with st.chat_message("assistant"):
            with st.spinner("Тренер анализирует твои тренировки..."):
                response = chain.invoke({
                    "name": name, "age": age, "weight": weight, "height": height,
                    "goal": goal, "level": level, "trainer_style": trainer_style,
                    "history": [],
                    "input": analysis_prompt,
                })
            st.markdown(response)
        if voice_response:
            speak(response)
