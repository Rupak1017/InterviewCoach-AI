"""JSON-only storage for guided practice sessions."""

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
    """Create the JSON data file and recover if it becomes corrupted."""
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


def create_session(
    role: str,
    selected_topic: str,
    difficulty: str,
    max_questions: int,
) -> str:
    """Create a new guided practice session and return its id."""
    data = _read_data()
    session_id = uuid.uuid4().hex[:8]

    data["sessions"].append(
        {
            "session_id": session_id,
            "role": role,
            "selected_topic": selected_topic,
            "difficulty": difficulty,
            "max_questions": max_questions,
            "created_at": _now(),
            "answers": [],
            "scores": [],
            "weak_areas": [],
            "study_sources": [],
            "final_report": {},
        }
    )
    _write_data(data)
    return session_id


def _merge_sources(existing: list[dict[str, Any]], new_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for source in existing + new_sources:
        url = source.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        merged.append(
            {
                "title": source.get("title", "Study source"),
                "url": url,
                "snippet": source.get("snippet", ""),
            }
        )
    return merged[:20]


def save_answer(session_id: str, answer_data: dict[str, Any]) -> None:
    """Append one graded answer to a session and update summary fields."""
    data = _read_data()
    for session in data["sessions"]:
        if session.get("session_id") == session_id:
            saved_answer = dict(answer_data)
            saved_answer.setdefault("created_at", _now())

            session.setdefault("answers", []).append(saved_answer)
            session.setdefault("scores", []).append(int(saved_answer.get("score", 0)))

            weak_area = saved_answer.get("weak_area", "")
            if weak_area:
                session.setdefault("weak_areas", []).append(weak_area)

            links = saved_answer.get("useful_links", [])
            session["study_sources"] = _merge_sources(session.get("study_sources", []), links)
            _write_data(data)
            return

    raise ValueError(f"Session not found: {session_id}")


def save_session_to_json(session_data: dict[str, Any]) -> None:
    """Save final session fields to JSON."""
    data = _read_data()
    session_id = session_data.get("session_id")

    for session in data["sessions"]:
        if session.get("session_id") == session_id:
            for key, value in session_data.items():
                if key == "study_sources":
                    session[key] = _merge_sources(session.get(key, []), value)
                elif key != "answers":
                    session[key] = value
            _write_data(data)
            return

    new_session = dict(session_data)
    new_session.setdefault("session_id", uuid.uuid4().hex[:8])
    new_session.setdefault("created_at", _now())
    new_session.setdefault("answers", [])
    data["sessions"].append(new_session)
    _write_data(data)


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

    scores = [int(score) for score in session.get("scores", [])]
    average_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    return {
        "session_id": session["session_id"],
        "role": session["role"],
        "selected_topic": session.get("selected_topic", ""),
        "difficulty": session["difficulty"],
        "created_at": session["created_at"],
        "questions_answered": len(session.get("answers", [])),
        "average_score": average_score,
        "weak_areas": session.get("weak_areas", []),
        "answers": session.get("answers", []),
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
