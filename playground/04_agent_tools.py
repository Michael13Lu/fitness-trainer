# ============================================================
# ЭТАП 4: Agent + Tools — агент с инструментами
# ============================================================
# Концепции:
#   - Tool       : функция которую агент может вызвать
#   - @tool      : декоратор превращает функцию в инструмент
#   - Agent      : модель которая сама решает какой tool использовать
#   - AgentExecutor: запускает агента в цикле до финального ответа
#
# Логика агента (ReAct loop):
#   Thought → Action (выбор tool) → Observation → ... → Final Answer
# ============================================================

from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

llm = ChatOllama(model="qwen3-vl:4b-instruct", temperature=0)

# --- Определяем инструменты ---
# @tool декоратор сообщает LangChain:
#   - название инструмента (имя функции)
#   - что он делает (docstring)
#   - какие аргументы принимает (параметры функции)

@tool
def calculator(expression: str) -> str:
    """Вычисляет математическое выражение. Пример: '2 + 2', '10 * 5 / 2'"""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Результат: {result}"
    except Exception as e:
        return f"Ошибка: {e}"


@tool
def get_weather(city: str) -> str:
    """Возвращает текущую погоду в городе."""
    # В реальном проекте здесь был бы запрос к API погоды
    fake_data = {
        "москва": "Москва: -5°C, снег, ветер 10 м/с",
        "лондон": "Лондон: 8°C, дождь, ветер 15 м/с",
        "токио": "Токио: 15°C, солнечно, ветер 5 м/с",
    }
    return fake_data.get(city.lower(), f"Данные для '{city}' не найдены")


@tool
def word_counter(text: str) -> str:
    """Подсчитывает количество слов в тексте."""
    count = len(text.split())
    return f"В тексте {count} слов"


# Список доступных инструментов
tools = [calculator, get_weather, word_counter]

# Создаём агента — он сам решит когда и какой tool использовать
agent = create_react_agent(llm, tools)


def ask_agent(question: str):
    print(f"\nВопрос: {question}")
    print("-" * 40)

    result = agent.invoke({
        "messages": [("human", question)]
    })

    # Последнее сообщение — финальный ответ агента
    final = result["messages"][-1].content
    print(f"Ответ: {final}")


# --- Тестируем агента ---
ask_agent("Сколько будет 1234 умножить на 567?")
ask_agent("Какая погода сейчас в Токио?")
ask_agent("Посчитай слова: 'Я учу LangChain и это очень интересно'")
ask_agent("Какая погода в Москве и сколько будет 100 / 4?")  # агент использует 2 tool сразу!

# ============================================================
# ПОПРОБУЙ САМ:
#   Добавь свой инструмент, например:
#
#   @tool
#   def reverse_text(text: str) -> str:
#       """Переворачивает текст задом наперёд."""
#       return text[::-1]
#
#   И добавь его в список tools = [...]
# ============================================================
