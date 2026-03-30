# ============================================================
# ЭТАП 3: Memory — чат с памятью разговора
# ============================================================
# Концепции:
#   - ChatMessageHistory : хранит историю сообщений
#   - HumanMessage       : сообщение от пользователя
#   - AIMessage          : сообщение от модели
#   - Ручное управление  : мы сами добавляем историю в prompt
# ============================================================

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory

llm = ChatOllama(model="qwen3-vl:4b-instruct", temperature=0.7)

# Хранилище истории сообщений
history = ChatMessageHistory()

# Prompt с местом для истории — MessagesPlaceholder вставляет
# все прошлые сообщения в нужное место
prompt = ChatPromptTemplate.from_messages([
    ("system", "Ты дружелюбный ассистент. Помнишь весь разговор."),
    MessagesPlaceholder(variable_name="history"),  # <- сюда вставляется история
    ("human", "{input}"),
])

parser = StrOutputParser()
chain = prompt | llm | parser


def chat(user_message: str) -> str:
    # 1. Запускаем цепочку, передавая историю и новое сообщение
    response = chain.invoke({
        "history": history.messages,
        "input": user_message,
    })
    # 2. Сохраняем сообщение пользователя и ответ в историю
    history.add_user_message(user_message)
    history.add_ai_message(response)
    return response


# --- Симулируем разговор ---
print("=== Чат с памятью ===\n")

questions = [
    "Привет! Меня зовут Михаил. Я учу LangChain.",
    "Как меня зовут и чем я занимаюсь?",        # проверяем память
    "Что посоветуешь изучить после LangChain?",
]

for question in questions:
    print(f"Ты: {question}")
    answer = chat(question)
    print(f"Бот: {answer}")
    print("-" * 40)

# Покажем что хранится в истории
print(f"\nВ памяти хранится {len(history.messages)} сообщений")

# ============================================================
# ПОПРОБУЙ САМ:
#   Замени симуляцию на реальный диалог в консоли:
#
#   while True:
#       user_input = input("Ты: ")
#       if user_input == "выход":
#           break
#       print(f"Бот: {chat(user_input)}\n")
# ============================================================
