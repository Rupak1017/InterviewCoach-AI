"""LangGraph workflow for Guided Practice Mode."""

from __future__ import annotations

import time
from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from chains import (
    generate_final_report_chain,
    generate_question_chain,
    generate_quick_prep_chain,
)
from middleware import (
    constructive_feedback_guard,
    limit_feedback_length,
    max_question_guard,
    no_fake_experience_guard,
    validate_score,
)
from tools import (
    choose_subtopic,
    choose_topic,
    fallback_mcq_question,
    is_duplicate_question,
    local_grade_mcq,
    save_answer_to_json,
    save_session_to_json,
    search_study_sources,
)


class InterviewState(TypedDict, total=False):
    session_id: str
    role: str
    selected_topic: str
    difficulty: str
    max_questions: int
    question_count: int
    current_topic: str
    quick_prep: dict[str, Any]
    study_sources: list[dict[str, Any]]
    current_question: str
    current_subtopic: str
    choices: list[str]
    correct_answer: str
    expected_points: list[str]
    user_answer: str
    scores: list[int]
    weak_areas: list[str]
    strong_areas: list[str]
    feedback_history: list[str]
    asked_questions: list[str]
    final_report: dict[str, Any]
    source_cache: dict[str, list[dict[str, Any]]]
    stage: str
    last_grade: dict[str, Any]
    validation_message: str


def _source_dicts(sources: list[Any]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for source in sources:
        if hasattr(source, "model_dump"):
            prepared.append(source.model_dump())
        elif isinstance(source, dict):
            prepared.append(source)
    return prepared


def _merge_sources(existing: list[dict[str, Any]], new_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for source in existing + new_sources:
        url = source.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        merged.append(source)
    return merged[:20]


def _cache_key(role: str, topic: str) -> str:
    return f"{role.lower()}::{topic.lower()}"


def prepare_context_node(state: InterviewState) -> InterviewState:
    """Choose a topic, fetch study links, and create a short prep card."""
    started = time.perf_counter()
    updated = dict(state)
    try:
        role = updated.get("role", "AI Engineer")
        topic = choose_topic(
            role,
            updated.get("selected_topic", ""),
            updated.get("weak_areas", []),
        )
        subtopic = choose_subtopic(
            topic,
            updated.get("question_count", 0),
            updated.get("asked_questions", []),
        )
        source_cache = dict(updated.get("source_cache", {}))
        key = _cache_key(role, topic)
        if key in source_cache and source_cache[key]:
            current_sources = source_cache[key]
            print("[source-cache] hit:", key)
        else:
            print("[source-cache] miss:", key)
            current_sources = search_study_sources(role, topic)
            source_cache[key] = current_sources

        existing_prep = updated.get("quick_prep", {})
        if updated.get("current_topic") == topic and existing_prep:
            quick_prep_data = existing_prep
            print("[quick-prep] cache hit:", topic)
        else:
            print("[quick-prep] cache miss:", topic)
            prep_state = dict(updated)
            prep_state["current_topic"] = topic
            prep_state["current_subtopic"] = subtopic
            prep_state["study_sources"] = current_sources
            quick_prep = generate_quick_prep_chain(prep_state)
            quick_prep.sources = quick_prep.sources[:4]
            quick_prep_data = quick_prep.model_dump()

        updated["current_topic"] = topic
        updated["current_subtopic"] = subtopic
        updated["source_cache"] = source_cache
        updated["quick_prep"] = quick_prep_data
        updated["study_sources"] = _merge_sources(
            updated.get("study_sources", []),
            _source_dicts(quick_prep_data.get("sources", [])) or current_sources,
        )
        updated["validation_message"] = ""
        updated["stage"] = "prepared"
        return updated
    finally:
        print(f"[timing] prepare_context_node took {time.perf_counter() - started:.2f}s")


def generate_question_node(state: InterviewState) -> InterviewState:
    """Generate the next question and pause for user input."""
    started = time.perf_counter()
    updated = dict(state)
    try:
        question_count = updated.get("question_count", 0)
        max_questions = updated.get("max_questions", 5)

        if not max_question_guard(question_count, max_questions):
            updated["stage"] = "complete"
            return updated

        asked_questions = updated.get("asked_questions", [])
        question = generate_question_chain(updated)
        duplicate = is_duplicate_question(question.question, asked_questions)
        if duplicate:
            question = fallback_mcq_question(
                updated.get("role", "AI Engineer"),
                updated.get("current_topic", ""),
                updated.get("difficulty", "Easy"),
                updated.get("current_subtopic", ""),
                asked_questions,
            )
            duplicate = is_duplicate_question(question.question, asked_questions)

        print("[question-generation] duplicate:", duplicate)
        updated["current_question"] = question.question
        updated["current_topic"] = question.topic or updated.get("current_topic", "")
        updated["choices"] = question.choices
        updated["correct_answer"] = question.correct_answer
        updated["expected_points"] = question.expected_points
        updated["asked_questions"] = asked_questions + [question.question]
        updated["user_answer"] = ""
        updated["validation_message"] = ""
        updated["stage"] = "waiting_for_answer"
        return updated
    finally:
        print(f"[timing] generate_question_node took {time.perf_counter() - started:.2f}s")


def grade_answer_node(state: InterviewState) -> InterviewState:
    """Grade the submitted answer and update adaptive state."""
    started = time.perf_counter()
    updated = dict(state)
    try:
        answer = updated.get("user_answer", "")

        if not answer:
            updated["validation_message"] = "Please select an answer before I grade it."
            updated["stage"] = "waiting_for_answer"
            return updated

        current_sources = _source_dicts(updated.get("quick_prep", {}).get("sources", []))
        if not current_sources:
            current_sources = updated.get("study_sources", [])

        grade = local_grade_mcq(
            selected_answer=answer,
            correct_answer=updated.get("correct_answer", ""),
            current_topic=updated.get("current_topic", ""),
            expected_points=updated.get("expected_points", []),
            sources=current_sources,
        )

        grade.score = validate_score(grade.score)
        grade.correct_answer = updated.get("correct_answer", grade.correct_answer)
        grade.feedback = no_fake_experience_guard(
            constructive_feedback_guard(limit_feedback_length(grade.feedback))
        )
        grade.sample_answer = no_fake_experience_guard(grade.sample_answer)
        if grade.score >= 8:
            grade.weak_area = ""
        elif not grade.weak_area:
            grade.weak_area = updated.get("current_topic", "")

        feedback_line = f"Score {grade.score}/10: {grade.feedback}"
        scores = updated.get("scores", []) + [grade.score]
        weak_areas = updated.get("weak_areas", [])
        strong_areas = updated.get("strong_areas", [])

        if grade.weak_area:
            weak_areas = weak_areas + [grade.weak_area]
        if grade.score >= 7:
            strong_areas = strong_areas + [updated.get("current_topic", grade.strength)]

        useful_links = _source_dicts(grade.recommended_links)[:4]
        answer_data = {
            "question": updated.get("current_question", ""),
            "answer": answer,
            "correct_answer": updated.get("correct_answer", ""),
            "score": grade.score,
            "feedback": grade.feedback,
            "weak_area": grade.weak_area,
            "study_next": grade.study_next,
            "useful_links": useful_links,
        }
        save_answer_to_json(updated.get("session_id", ""), answer_data)

        updated["scores"] = scores
        updated["weak_areas"] = weak_areas
        updated["strong_areas"] = strong_areas
        updated["feedback_history"] = updated.get("feedback_history", []) + [feedback_line]
        updated["study_sources"] = _merge_sources(updated.get("study_sources", []), useful_links)
        updated["question_count"] = updated.get("question_count", 0) + 1
        updated["last_grade"] = grade.model_dump()
        updated["validation_message"] = ""
        updated["stage"] = "graded"
        return updated
    finally:
        print(f"[timing] grade_answer_node took {time.perf_counter() - started:.2f}s")


def final_report_node(state: InterviewState) -> InterviewState:
    """Create and save the final interview summary."""
    started = time.perf_counter()
    updated = dict(state)
    try:
        report = generate_final_report_chain(updated)
        updated["final_report"] = report.model_dump()
        updated["stage"] = "complete"
        save_session_to_json(
            {
                "session_id": updated.get("session_id", ""),
                "role": updated.get("role", ""),
                "selected_topic": updated.get("selected_topic", ""),
                "difficulty": updated.get("difficulty", ""),
                "max_questions": updated.get("max_questions", 0),
                "scores": updated.get("scores", []),
                "weak_areas": updated.get("weak_areas", []),
                "study_sources": updated.get("study_sources", []),
                "final_report": updated.get("final_report", {}),
            }
        )
        return updated
    finally:
        print(f"[timing] final_report_node took {time.perf_counter() - started:.2f}s")


def route_after_grading(state: InterviewState) -> str:
    """Route to the next question or final report."""
    if state.get("validation_message"):
        return "end"
    if state.get("question_count", 0) >= state.get("max_questions", 5):
        return "final_report_node"
    return "prepare_context_node"


def build_question_graph():
    """Build the graph for asking one question."""
    workflow = StateGraph(InterviewState)
    workflow.add_node("prepare_context_node", prepare_context_node)
    workflow.add_node("generate_question_node", generate_question_node)
    workflow.add_edge(START, "prepare_context_node")
    workflow.add_edge("prepare_context_node", "generate_question_node")
    workflow.add_edge("generate_question_node", END)
    return workflow.compile()


def build_answer_graph():
    """Build the graph for grading and routing."""
    workflow = StateGraph(InterviewState)
    workflow.add_node("grade_answer_node", grade_answer_node)
    workflow.add_node("prepare_context_node", prepare_context_node)
    workflow.add_node("generate_question_node", generate_question_node)
    workflow.add_node("final_report_node", final_report_node)
    workflow.add_edge(START, "grade_answer_node")
    workflow.add_conditional_edges(
        "grade_answer_node",
        route_after_grading,
        {
            "prepare_context_node": "prepare_context_node",
            "final_report_node": "final_report_node",
            "end": END,
        },
    )
    workflow.add_edge("prepare_context_node", "generate_question_node")
    workflow.add_edge("generate_question_node", END)
    workflow.add_edge("final_report_node", END)
    return workflow.compile()


def generate_next_question(state: InterviewState) -> InterviewState:
    """Run the question graph once."""
    graph = build_question_graph()
    return graph.invoke(state)


def grade_current_answer(state: InterviewState) -> InterviewState:
    """Run the answer graph once after the user submits an answer."""
    graph = build_answer_graph()
    return graph.invoke(state)
