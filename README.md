# 💪 Персональный фитнес-тренер

Персональный AI-тренер по фитнесу и питанию с поддержкой диалога. Работает через браузер на любом устройстве.

## Возможности

- Персональные советы по тренировкам и питанию
- Учитывает твой вес, рост, возраст и цель
- Помнит весь разговор в рамках сессии
- Три стиля тренера: мотивирующий, строгий, мягкий
- Работает на любом устройстве (телефон, планшет, ПК)

## Технологии

- [LangChain](https://python.langchain.com) — оркестрация LLM
- [Groq](https://groq.com) — быстрый облачный AI (llama-3.1-8b-instant)
- [Streamlit](https://streamlit.io) — веб-интерфейс

## Запуск локально

```bash
git clone https://github.com/Michael13Lu/fitness-trainer.git
cd fitness-trainer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Создай файл `.env`:
```
GROQ_API_KEY=твой_ключ
```

Запусти:
```bash
streamlit run app/fitness_trainer.py
```

## Деплой

Приложение задеплоено на Streamlit Cloud:
👉 https://fitness-trainer-hdbkkiytxyqmvse6gksk9j.streamlit.app
