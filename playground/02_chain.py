# ============================================================
# ЭТАП 2: Chain — цепочка из нескольких шагов
# ============================================================
# Концепции:
#   - StrOutputParser  : достаёт текст из ответа модели
#   - Многошаговая цепь: выход шага 1 → вход шага 2
#   - RunnablePassthrough: передаёт входные данные дальше
# ============================================================

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

llm = ChatOllama(model="qwen3-vl:4b-instruct", temperature=0.7)

# --- ШАГ 1: Генерируем идею для поста ---
prompt_idea = ChatPromptTemplate.from_messages([
    ("system", "Ты креативный копирайтер."),
    ("human", "Придумай одну короткую идею для поста в соцсети на тему: {topic}"),
])

# --- ШАГ 2: Пишем пост на основе идеи ---
prompt_post = ChatPromptTemplate.from_messages([
    ("system", "Ты пишешь посты для соцсетей. Пиши коротко и engaging."),
    ("human", "Напиши пост на основе этой идеи:\n{idea}"),
])

# StrOutputParser превращает объект AIMessage в обычную строку
parser = StrOutputParser()

# Цепочка шаг за шагом:
# 1. prompt_idea заполняется через {topic}
# 2. llm генерирует идею
# 3. parser достаёт текст из ответа
# 4. результат идёт в {idea} для prompt_post
# 5. llm пишет финальный пост
chain = (
    {"idea": prompt_idea | llm | parser, "topic": RunnablePassthrough()}
    | prompt_post
    | llm
    | parser
)

print("Генерируем пост...\n")
result = chain.invoke({"topic": "искусственный интеллект меняет мир"})

print("Готовый пост:")
print("-" * 40)
print(result)

# ============================================================
# ПОПРОБУЙ САМ:
#   1. Измени topic на другую тему
#   2. Добавь третий шаг: перевод поста на английский
#      prompt_translate = ChatPromptTemplate.from_messages([
#          ("human", "Переведи на английский: {post}")
#      ])
# ============================================================
