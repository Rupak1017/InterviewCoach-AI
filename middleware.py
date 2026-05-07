"""Small guardrails and middleware-style helpers for the interview flow."""

from __future__ import annotations

import re
from typing import Any


def limit_feedback_length(text: str, max_sentences: int = 4) -> str:
    """Keep generated feedback short enough for the UI."""
    if not text:
        return ""

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:max_sentences]).strip()


def validate_score(score: Any) -> int:
    """Clamp scores into the expected 1-10 range."""
    try:
        value = int(score)
    except (TypeError, ValueError):
        value = 1
    return max(1, min(10, value))


def block_empty_answer(answer: str) -> str | None:
    """Return a helpful message if an answer is too short to grade."""
    clean_answer = (answer or "").strip()
    if not clean_answer or len(clean_answer.split()) < 5:
        return "Please write a more detailed answer before I grade it."
    return None


def max_question_guard(question_count: int, max_questions: int) -> bool:
    """Prevent the app from asking beyond the requested interview length."""
    return question_count < max_questions


def tool_call_logger(tool_name: str, input_summary: str, output_summary: str) -> None:
    """Log lightweight tool activity for debugging in the terminal."""
    print(f"[tool] {tool_name} | input={input_summary} | output={output_summary}")


def constructive_feedback_guard(feedback: str) -> str:
    """Soften unhelpful wording if a model ever returns discouraging text."""
    if not feedback:
        return "Good effort. Add more specific details and connect your answer to the role."

    discouraging_terms = {
        "terrible": "needs more detail",
        "awful": "needs more detail",
        "bad answer": "incomplete answer",
        "you failed": "this answer is not complete yet",
    }

    guarded = feedback
    for rude, replacement in discouraging_terms.items():
        guarded = re.sub(rude, replacement, guarded, flags=re.IGNORECASE)
    return guarded.strip()


def no_fake_experience_guard(text: str) -> str:
    """Discourage advice that tells users to claim experience they do not have."""
    if not text:
        return ""

    risky_patterns = [
        r"claim you (have|built|led|worked)",
        r"say you (have|built|led|worked)",
        r"pretend you (have|built|led|worked)",
        r"make up .*experience",
    ]

    guarded = text
    for pattern in risky_patterns:
        guarded = re.sub(
            pattern,
            "describe relevant learning, projects, or honest practice",
            guarded,
            flags=re.IGNORECASE,
        )
    return guarded.strip()
