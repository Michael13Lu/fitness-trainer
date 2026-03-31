import os
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def _client_config() -> dict:
    return {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def _redirect_uri() -> str:
    # Auto-detect: on Streamlit Cloud uses the real app URL, locally uses localhost
    try:
        import streamlit as st
        from urllib.parse import urlparse
        parsed = urlparse(st.context.url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")


def is_configured() -> bool:
    return bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))


def get_auth_url() -> tuple:
    """Returns (auth_url, flow) — store the flow in session_state for exchange_code."""
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=_redirect_uri())
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return auth_url, flow


def exchange_code(flow, code: str) -> Credentials:
    """Pass the same flow object returned by get_auth_url."""
    flow.fetch_token(code=code)
    return flow.credentials


def creds_to_dict(creds: Credentials) -> dict:
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else [],
    }


def creds_from_dict(d: dict) -> Credentials:
    return Credentials(
        token=d["token"],
        refresh_token=d.get("refresh_token"),
        token_uri=d["token_uri"],
        client_id=d["client_id"],
        client_secret=d["client_secret"],
        scopes=d.get("scopes", []),
    )


def add_workout_event(creds: Credentials, workout_date: str, exercise: str,
                      muscle_group: str, sets: int, reps: int,
                      weight_kg: float, notes: str = "") -> str:
    """Adds a workout as an all-day event to Google Calendar. Returns the event URL."""
    service = build("calendar", "v3", credentials=creds)

    description_lines = [
        f"Exercise: {exercise}",
        f"Muscle group: {muscle_group}",
        f"Sets × Reps: {sets} × {reps}",
        f"Weight: {weight_kg} kg",
    ]
    if notes:
        description_lines.append(f"Notes: {notes}")

    event = {
        "summary": f"🏋️ {exercise}",
        "description": "\n".join(description_lines),
        "start": {"date": str(workout_date)},
        "end": {"date": str(workout_date)},
        "colorId": "2",  # green
    }

    created = service.events().insert(calendarId="primary", body=event).execute()
    return created.get("htmlLink", "")
