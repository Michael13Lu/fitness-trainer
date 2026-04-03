import os
import json
import hashlib
import secrets
import base64
import sqlite3
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from config import DB_PATH

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
    try:
        import streamlit as st
        from urllib.parse import urlparse
        parsed = urlparse(st.context.url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")


def is_configured() -> bool:
    return bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))


# ── PKCE helpers (store verifier in SQLite so it survives redirect) ──────────

def _init_pkce_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS oauth_pkce (
                state TEXT PRIMARY KEY,
                code_verifier TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def _save_verifier(state: str, code_verifier: str):
    _init_pkce_table()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO oauth_pkce (state, code_verifier) VALUES (?, ?)",
            (state, code_verifier)
        )


def _load_verifier(state: str) -> str:
    _init_pkce_table()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT code_verifier FROM oauth_pkce WHERE state = ?", (state,)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM oauth_pkce WHERE state = ?", (state,))
    return row[0] if row else ""


def _make_pkce():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


# ── OAuth flow ────────────────────────────────────────────────────────────────

def get_auth_url() -> str:
    verifier, challenge = _make_pkce()
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=_redirect_uri())
    auth_url, state = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        code_challenge=challenge,
        code_challenge_method="S256",
    )
    _save_verifier(state, verifier)
    return auth_url


def exchange_code(code: str, state: str) -> Credentials:
    verifier = _load_verifier(state)
    flow = Flow.from_client_config(
        _client_config(), scopes=SCOPES, redirect_uri=_redirect_uri(), state=state
    )
    flow.fetch_token(code=code, code_verifier=verifier)
    return flow.credentials


# ── Credentials serialization ─────────────────────────────────────────────────

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


# ── Calendar event ────────────────────────────────────────────────────────────

def add_workout_event(creds: Credentials, workout_date: str, exercise: str,
                      muscle_group: str, sets: int, reps: int,
                      weight_kg: float, notes: str = "") -> str:
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
        "colorId": "2",
    }

    created = service.events().insert(calendarId="primary", body=event).execute()
    return created.get("htmlLink", "")
