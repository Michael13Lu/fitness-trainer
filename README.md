# Fitness Trainer

An AI fitness and nutrition coach built with Streamlit, LangChain, and Groq. The app runs in the browser and combines conversational guidance, workout logging, voice input, image analysis, and progress review in one interface.

## Features

- Personalized training and nutrition advice based on the user's profile
- Persistent chat history stored in SQLite
- Workout diary with strength and cardio logging
- Voice input with speech-to-text
- Image-based exercise recognition and visual analysis
- Workout progress analysis powered by an LLM
- Google Calendar integration for saving workouts as events
- Multilingual UI support

## Tech Stack

- [Streamlit](https://streamlit.io) for the web interface
- [LangChain](https://python.langchain.com) for prompt orchestration
- [Groq](https://groq.com) for text, vision, and speech AI models
- SQLite for local persistence
- Google Calendar API for calendar integration

## Project Architecture

The project is organized around a Streamlit application with supporting storage and integration modules.

### Main Application Flow

- `app/fitness_trainer.py`: main entry point and primary UI
- `app/fitness_trainer.py`: handles sidebar state, chat, workout diary, analysis tab, file uploads, voice input, and Google Calendar actions
- `app/fitness_trainer.py`: builds the LangChain prompt pipeline and calls Groq models for text and vision tasks

### Data Layer

- `app/memory_store.py`: stores and loads chat messages and language preferences in SQLite
- `app/workout_store.py`: stores workout entries, cardio fields, summaries, and workout history queries
- `app/chat_history.db`: local SQLite database used by the app

### Integration Layer

- `app/google_calendar.py`: Google OAuth with PKCE and Calendar event creation helpers
- `app/translations.py`: language dictionary and translation lookup helper

### Supporting Folders

- `playground/`: experimental LangChain and agent examples
- `chains/`: chain-related modules and placeholders for future extraction
- `agents/`: agent-related modules and placeholders for future extraction
- `prompts/`: prompt templates and prompt utilities
- `data/`: project data assets

### Current Architectural Notes

- The current implementation is centered in `app/fitness_trainer.py`, which acts as both UI and application orchestration layer
- Storage and integration concerns are already separated into dedicated modules
- The empty modules in `chains/`, `agents/`, and some files under `app/` suggest a planned future refactor toward a cleaner layered architecture

## Setup

```bash
git clone https://github.com/Michael13Lu/fitness-trainer.git
cd fitness-trainer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:

```env
GROQ_API_KEY=your_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

## Run Locally

```bash
streamlit run app/fitness_trainer.py
```

## Deployment

The app is deployed on Streamlit Cloud:
https://fitness-trainer-hdbkkiytxyqmvse6gksk9j.streamlit.app
