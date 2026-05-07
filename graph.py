"""LangGraph workflow for the adaptive interview."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from chains import generate_final_report_chain, generate_question_chain, grade_answer_chain
from middleware import (
    constructive_feedback_guard,
    limit_feedback_length,
    max_question_guard,
    no_fake_experience_guard,
    validate_score,
)
from tools import ROLE_TOPICS, choose_topic, save_score_tool


class InterviewState(TypedDict, total=False):
    session_id: str
    role: str
    difficulty: str
    max_questions: int
    question_count: int
    current_question: str
    current_topic: str
    choices: list[str]
    correct_answer: str
    expected_points: list[str]
    user_answer: str
    scores: list[int]
    feedback_history: list[str]
    weak_areas: list[str]
    strong_areas: list[str]
    asked_questions: list[str]
    next_topic: str
    final_report: dict[str, Any]
    stage: str
    last_grade: dict[str, Any]
    validation_message: str


def generate_question_node(state: InterviewState) -> InterviewState:
    """Generate the next question and pause for user input."""
    updated = dict(state)
    question_count = updated.get("question_count", 0)
    max_questions = updated.get("max_questions", 5)

    if not max_question_guard(question_count, max_questions):
        updated["stage"] = "complete"
        return updated

    topic = choose_topic(
        updated.get("role", "AI Engineer"),
        updated.get("difficulty", "Easy"),
        updated.get("weak_areas", []),
        updated.get("next_topic", ""),
    )
    chain_state = dict(updated)
    chain_state["target_topic"] = topic
    question = generate_question_chain(chain_state)

    updated["current_question"] = question.question
    updated["current_topic"] = question.topic
    updated["choices"] = question.choices
    updated["correct_answer"] = question.correct_answer
    updated["expected_points"] = question.expected_points
    updated["asked_questions"] = updated.get("asked_questions", []) + [question.question]
    updated["user_answer"] = ""
    updated["validation_message"] = ""
    updated["stage"] = "waiting_for_answer"
    return updated


def grade_answer_node(state: InterviewState) -> InterviewState:
    """Grade the submitted answer and update adaptive state."""
    updated = dict(state)
    answer = updated.get("user_answer", "")

    if not answer:
        updated["validation_message"] = "Please select an answer before I grade it."
        updated["stage"] = "waiting_for_answer"
        return updated

    grade = grade_answer_chain(
        question=updated.get("current_question", ""),
        answer=answer,
        choices=updated.get("choices", []),
        correct_answer=updated.get("correct_answer", ""),
        expected_points=updated.get("expected_points", []),
        role=updated.get("role", "AI Engineer"),
        difficulty=updated.get("difficulty", "Easy"),
    )

    grade.score = validate_score(grade.score)
    if grade.score < 8:
        grade.weak_area = updated.get("current_topic", grade.weak_area)
    else:
        grade.weak_area = ""
    grade.feedback = constructive_feedback_guard(limit_feedback_length(grade.feedback))
    grade.feedback = no_fake_experience_guard(grade.feedback)
    grade.sample_answer = no_fake_experience_guard(grade.sample_answer)
    grade.correct_answer = updated.get("correct_answer", grade.correct_answer)

    feedback_line = f"Score {grade.score}/10: {grade.feedback}"
    save_score_tool(
        updated.get("session_id", ""),
        updated.get("current_question", ""),
        answer,
        grade.score,
        grade.feedback,
        grade.weak_area,
    )

    scores = updated.get("scores", []) + [grade.score]
    weak_areas = updated.get("weak_areas", [])
    strong_areas = updated.get("strong_areas", [])

    if grade.weak_area and grade.score < 8:
        weak_areas = weak_areas + [grade.weak_area]
    if grade.score >= 7:
        strong_areas = strong_areas + [updated.get("current_topic", grade.strength)]

    next_topic = grade.next_topic_suggestion
    if grade.score >= 8:
        topics = ROLE_TOPICS.get(updated.get("role", ""), [])
        current_topic = updated.get("current_topic", "")
        if current_topic in topics:
            next_topic = topics[(topics.index(current_topic) + 1) % len(topics)]

    updated["scores"] = scores
    updated["feedback_history"] = updated.get("feedback_history", []) + [feedback_line]
    updated["weak_areas"] = weak_areas
    updated["strong_areas"] = strong_areas
    updated["next_topic"] = next_topic
    updated["question_count"] = updated.get("question_count", 0) + 1
    updated["last_grade"] = grade.model_dump()
    updated["validation_message"] = ""
    updated["stage"] = "graded"
    return updated


def final_report_node(state: InterviewState) -> InterviewState:
    """Create the final interview summary."""
    updated = dict(state)
    report = generate_final_report_chain(updated)
    updated["final_report"] = report.model_dump()
    updated["stage"] = "complete"
    return updated


def route_after_grading(state: InterviewState) -> str:
    """Route to the final report or the next question."""
    if state.get("validation_message"):
        return "end"
    if state.get("question_count", 0) >= state.get("max_questions", 5):
        return "final_report_node"
    return "generate_question_node"


def build_question_graph():
    """Build a graph that only generates a question, then stops."""
    workflow = StateGraph(InterviewState)
    workflow.add_node("generate_question_node", generate_question_node)
    workflow.add_edge(START, "generate_question_node")
    workflow.add_edge("generate_question_node", END)
    return workflow.compile()


def build_answer_graph():
    """Build a graph that grades an answer and decides the next step."""
    workflow = StateGraph(InterviewState)
    workflow.add_node("grade_answer_node", grade_answer_node)
    workflow.add_node("generate_question_node", generate_question_node)
    workflow.add_node("final_report_node", final_report_node)
    workflow.add_edge(START, "grade_answer_node")
    workflow.add_conditional_edges(
        "grade_answer_node",
        route_after_grading,
        {
            "generate_question_node": "generate_question_node",
            "final_report_node": "final_report_node",
            "end": END,
        },
    )
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
