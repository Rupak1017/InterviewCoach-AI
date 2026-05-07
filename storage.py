"""JSON-only storage for interview sessions."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "interview_sessions.json"
BACKUP_FILE = DATA_DIR / "interview_sessions_backup.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _empty_data() -> dict[str, list[dict[str, Any]]]:
    return {"sessions": []}


def ensure_data_file() -> None:
    """Create the data file, or recover cleanly from corrupted JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_FILE.exists():
        _write_data(_empty_data())
        return

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict) or not isinstance(data.get("sessions"), list):
            raise json.JSONDecodeError("Invalid session structure", "", 0)
    except json.JSONDecodeError:
        shutil.copy2(DATA_FILE, BACKUP_FILE)
        _write_data(_empty_data())


def _read_data() -> dict[str, Any]:
    ensure_data_file()
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_data(data: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = DATA_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    temp_file.replace(DATA_FILE)


def create_session(role: str, difficulty: str, max_questions: int) -> str:
    """Create a new interview session and return its id."""
    data = _read_data()
    session_id = uuid.uuid4().hex[:8]

    data["sessions"].append(
        {
            "session_id": session_id,
            "role": role,
            "difficulty": difficulty,
            "max_questions": max_questions,
            "created_at": _now(),
            "answers": [],
        }
    )
    _write_data(data)
    return session_id


def save_answer(
    session_id: str,
    question: str,
    answer: str,
    score: int,
    feedback: str,
    weak_area: str,
) -> None:
    """Append one graded answer to a saved session."""
    data = _read_data()
    for session in data["sessions"]:
        if session.get("session_id") == session_id:
            session.setdefault("answers", []).append(
                {
                    "question": question,
                    "answer": answer,
                    "score": int(score),
                    "feedback": feedback,
                    "weak_area": weak_area,
                    "created_at": _now(),
                }
            )
            _write_data(data)
            return

    raise ValueError(f"Session not found: {session_id}")


def get_session(session_id: str) -> dict[str, Any] | None:
    """Return one session by id."""
    data = _read_data()
    for session in data["sessions"]:
        if session.get("session_id") == session_id:
            return session
    return None


def get_session_results(session_id: str) -> dict[str, Any] | None:
    """Return a compact summary for one session."""
    session = get_session(session_id)
    if not session:
        return None

    answers = session.get("answers", [])
    scores = [int(item.get("score", 0)) for item in answers]
    average_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    weak_areas = [item.get("weak_area", "") for item in answers if item.get("weak_area")]

    return {
        "session_id": session["session_id"],
        "role": session["role"],
        "difficulty": session["difficulty"],
        "created_at": session["created_at"],
        "questions_answered": len(answers),
        "average_score": average_score,
        "weak_areas": weak_areas,
        "answers": answers,
    }


def reset_storage() -> None:
    """Clear all saved sessions."""
    _write_data(_empty_data())


def list_sessions() -> list[dict[str, Any]]:
    """Return saved sessions, newest first."""
    data = _read_data()
    return sorted(
        data["sessions"],
        key=lambda session: session.get("created_at", ""),
        reverse=True,
    )
