import os
import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory

load_dotenv()

# --- Настройки страницы ---
st.set_page_config(page_title="Фитнес-тренер", page_icon="💪", layout="wide")
st.title("💪 Персональный фитнес-тренер")

# --- Боковая панель: профиль пользователя ---
with st.sidebar:
    st.header("👤 Твой профиль")
    name = st.text_input("Имя", value="Михаил")
    age = st.number_input("Возраст", min_value=10, max_value=100, value=25)
    weight = st.number_input("Вес (кг)", min_value=30, max_value=200, value=75)
    height = st.number_input("Рост (см)", min_value=100, max_value=250, value=175)
    goal = st.selectbox("Цель", ["Похудеть", "Набрать мышечную массу", "Поддерживать форму", "Улучшить выносливость"])
    level = st.selectbox("Уровень подготовки", ["Новичок", "Средний", "Продвинутый"])
    trainer_style = st.selectbox("Стиль тренера", ["Мотивирующий", "Строгий", "Мягкий и поддерживающий"])

    if st.button("🗑️ Очистить чат"):
        st.session_state.history = ChatMessageHistory()
        st.session_state.messages = []
        st.rerun()

# --- Инициализация состояния ---
# st.session_state — это память Streamlit, сохраняется пока открыта страница
if "history" not in st.session_state:
    st.session_state.history = ChatMessageHistory()
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- LangChain: модель и цепочка ---
llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)

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

chain = prompt | llm | StrOutputParser()

# --- Отображение истории чата ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Поле ввода ---
if user_input := st.chat_input("Напиши тренеру..."):

    # Показываем сообщение пользователя
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Получаем ответ от модели
    with st.chat_message("assistant"):
        with st.spinner("Тренер думает..."):
            response = chain.invoke({
                "name": name,
                "age": age,
                "weight": weight,
                "height": height,
                "goal": goal,
                "level": level,
                "trainer_style": trainer_style,
                "history": st.session_state.history.messages,
                "input": user_input,
            })
        st.markdown(response)

    # Сохраняем в историю
    st.session_state.history.add_user_message(user_input)
    st.session_state.history.add_ai_message(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
