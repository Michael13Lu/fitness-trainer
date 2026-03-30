import os
import base64
import json
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from audio_recorder_streamlit import audio_recorder
from groq import Groq

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
        st.session_state.history = ChatMessageHistory()
        st.session_state.messages = []
        st.rerun()

if "history" not in st.session_state:
    st.session_state.history = ChatMessageHistory()
if "messages" not in st.session_state:
    st.session_state.messages = []

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


# --- История чата ---
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
        st.session_state.messages.append({"role": "assistant", "content": response})

# --- Текст + фото в одном поле ---
msg = st.chat_input(
    "Напиши тренеру или прикрепи фото  📎",
    accept_file=True,
    file_type=["jpg", "jpeg", "png", "webp"],
)

if msg:
    user_input = msg.text or ""
    uploaded_image = msg["files"][0] if msg["files"] else None
    image_data = uploaded_image.read() if uploaded_image else None
    mime = uploaded_image.type if uploaded_image else None

    with st.chat_message("user"):
        if image_data:
            st.image(image_data, width=200)
        if user_input:
            st.markdown(user_input)

    st.session_state.messages.append({
        "role": "user", "content": user_input or "_(фото)_", "image": image_data,
    })

    with st.chat_message("assistant"):
        with st.spinner("Тренер думает..."):
            if image_data:
                response = analyze_with_image(image_data, mime, user_input)
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

    st.session_state.history.add_user_message(user_input or "[фото]")
    st.session_state.history.add_ai_message(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
