"""Encrypted SQLite database for storing sessions, transcripts, and feedback."""

import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# NOTE: For production, replace sqlite3 with pysqlcipher3 for encryption.
# Using sqlite3 for initial development to reduce setup friction.
# TODO: Switch to pysqlcipher3 before any real patient data is stored.

DB_DIR = Path.home() / ".note-taker-for-mom"
DB_PATH = DB_DIR / "sessions.db"


def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    # TODO: When switching to pysqlcipher3, add:
    # conn.execute(f"PRAGMA key = '{passphrase}'")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            audio_path TEXT,
            duration_seconds REAL,
            status TEXT NOT NULL DEFAULT 'recorded'
        );

        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            speaker TEXT NOT NULL,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            format TEXT NOT NULL DEFAULT 'DAP',
            word_target INTEGER NOT NULL DEFAULT 75,
            content TEXT NOT NULL,
            edited_content TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            feature_area TEXT NOT NULL,
            rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
            comment TEXT,
            app_version TEXT,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def create_session(audio_path: str, duration_seconds: float) -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO sessions (created_at, audio_path, duration_seconds, status) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), audio_path, duration_seconds, "recorded"),
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def save_transcript_segments(session_id: int, segments: list[dict]):
    """Save diarized transcript segments.

    Each segment: {"speaker": str, "start": float, "end": float, "text": str}
    """
    conn = get_connection()
    conn.executemany(
        "INSERT INTO transcripts (session_id, speaker, start_time, end_time, text) VALUES (?, ?, ?, ?, ?)",
        [(session_id, s["speaker"], s["start"], s["end"], s["text"]) for s in segments],
    )
    conn.execute(
        "UPDATE sessions SET status = ? WHERE id = ?", ("transcribed", session_id)
    )
    conn.commit()
    conn.close()


def save_summary(session_id: int, content: str, word_target: int = 75, fmt: str = "DAP") -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO summaries (session_id, format, word_target, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, fmt, word_target, content, datetime.now().isoformat()),
    )
    summary_id = cursor.lastrowid
    conn.execute(
        "UPDATE sessions SET status = ? WHERE id = ?", ("summarized", session_id)
    )
    conn.commit()
    conn.close()
    return summary_id


def save_feedback(feature_area: str, rating: str, session_id: int = None, comment: str = None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO feedback (session_id, feature_area, rating, comment, app_version, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, feature_area, rating, comment, "0.1.0", datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_session(session_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_transcript(session_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT speaker, start_time, end_time, text FROM transcripts WHERE session_id = ? ORDER BY start_time",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_summary(session_id: int) -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM summaries WHERE session_id = ? ORDER BY id DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_sessions() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
