"""Simple tools used by the graph and chains."""

from __future__ import annotations

from collections import Counter
from typing import Any

from middleware import tool_call_logger
from storage import save_answer


ROLE_TOPICS = {
    "AI Engineer Intern": [
        "Python",
        "APIs",
        "LangChain",
        "LangGraph",
        "tool calling",
        "RAG",
        "vector databases",
        "prompt engineering",
        "debugging",
        "deployment basics",
    ],
    "Frontend Developer": [
        "HTML",
        "CSS",
        "JavaScript",
        "React",
        "state management",
        "accessibility",
        "performance",
        "API integration",
        "debugging",
    ],
    "Backend Developer": [
        "Python",
        "REST APIs",
        "databases",
        "authentication",
        "caching",
        "system design basics",
        "error handling",
        "testing",
        "deployment",
    ],
    "Data Analyst": [
        "SQL",
        "Excel",
        "Python",
        "pandas",
        "statistics",
        "dashboards",
        "data cleaning",
        "business metrics",
        "visualization",
    ],
}


def choose_topic(
    role: str,
    difficulty: str,
    weak_areas: list[str] | None,
    next_topic: str | None,
) -> str:
    """Choose the next topic, prioritizing adaptive weak areas."""
    topics = ROLE_TOPICS.get(role, ROLE_TOPICS["AI Engineer Intern"])
    normalized_topics = {topic.lower(): topic for topic in topics}
    starter_topics = {
        "AI Engineer Intern": "tool calling",
        "Frontend Developer": "React",
        "Backend Developer": "REST APIs",
        "Data Analyst": "SQL",
    }

    if next_topic and next_topic.lower() in normalized_topics:
        chosen = normalized_topics[next_topic.lower()]
        tool_call_logger("choose_topic", f"next_topic={next_topic}", chosen)
        return chosen

    if weak_areas:
        weak_counts = Counter(area for area in weak_areas if area)
        for weak_area, _ in weak_counts.most_common():
            if weak_area.lower() in normalized_topics:
                chosen = normalized_topics[weak_area.lower()]
                tool_call_logger("choose_topic", f"weak_area={weak_area}", chosen)
                return chosen

            for topic in topics:
                if topic.lower() in weak_area.lower() or weak_area.lower() in topic.lower():
                    tool_call_logger("choose_topic", f"weak_area={weak_area}", topic)
                    return topic

        chosen = topics[len(weak_areas) % len(topics)]
        tool_call_logger("choose_topic", f"weak_area_unmatched={len(weak_areas)}", chosen)
        return chosen

    starter_topic = starter_topics.get(role)
    if not next_topic and starter_topic and starter_topic.lower() in normalized_topics:
        chosen = normalized_topics[starter_topic.lower()]
        tool_call_logger("choose_topic", f"role={role}, starter=true", chosen)
        return chosen

    difficulty_starts = {"Easy": 0, "Medium": min(2, len(topics) - 1), "Hard": min(4, len(topics) - 1)}
    chosen = topics[difficulty_starts.get(difficulty, 0)]
    tool_call_logger("choose_topic", f"role={role}, difficulty={difficulty}", chosen)
    return chosen


def calculate_average_score(scores: list[int]) -> float:
    """Return the rounded average score."""
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 1)


def get_weak_areas(results_or_state: dict[str, Any]) -> list[str]:
    """Return weak areas ordered by frequency."""
    areas: list[str] = []

    if "weak_areas" in results_or_state:
        areas = [area for area in results_or_state.get("weak_areas", []) if area]
    elif "answers" in results_or_state:
        areas = [
            answer.get("weak_area", "")
            for answer in results_or_state.get("answers", [])
            if answer.get("weak_area")
        ]

    return [area for area, _ in Counter(areas).most_common()]


def create_study_plan(weak_areas: list[str], role: str) -> list[str]:
    """Create short study suggestions from weak areas."""
    if not weak_areas:
        return [
            f"Review common {role} interview fundamentals.",
            "Practice explaining your thinking out loud.",
            "Prepare one honest project example for technical questions.",
        ]

    return [
        f"Review {area} with one short tutorial and one hands-on example."
        for area in weak_areas[:3]
    ]


def save_score_tool(
    session_id: str,
    question: str,
    answer: str,
    score: int,
    feedback: str,
    weak_area: str,
) -> None:
    """Save one graded answer to JSON storage."""
    save_answer(session_id, question, answer, score, feedback, weak_area)
    tool_call_logger("save_score_tool", f"session_id={session_id}, score={score}", weak_area)


def choose_difficulty_adjustment(scores: list[int]) -> str:
    """Suggest whether the next question should feel easier or harder."""
    if len(scores) < 2:
        return "Keep the question aligned with the selected difficulty."

    recent_average = calculate_average_score(scores[-2:])
    if recent_average >= 8:
        return "Ask a slightly harder follow-up while staying beginner-friendly."
    if recent_average <= 5:
        return "Ask a slightly easier fundamentals question to rebuild confidence."
    return "Keep the next question at the same difficulty."
