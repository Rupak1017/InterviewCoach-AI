"""LangChain Gemini chains with a deterministic mock fallback."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from middleware import (
    constructive_feedback_guard,
    limit_feedback_length,
    no_fake_experience_guard,
    validate_score,
)
from models import FinalReport, GradeOutput, QuestionOutput
from prompts import ANSWER_GRADING_PROMPT, FINAL_REPORT_PROMPT, QUESTION_GENERATION_PROMPT
from tools import (
    ROLE_TOPICS,
    calculate_average_score,
    choose_difficulty_adjustment,
    create_study_plan,
    get_weak_areas,
)


load_dotenv()

PLACEHOLDER_KEYS = {
    "your_gemini_api_key_here",
    "your_key_here",
    "your_real_key_here",
}


def _clean_api_key(value: str | None) -> str | None:
    if not value:
        return None

    stripped = value.strip()
    if not stripped or stripped in PLACEHOLDER_KEYS:
        return None
    return stripped


GEMINI_API_KEY = _clean_api_key(os.getenv("GEMINI_API_KEY"))
GOOGLE_API_KEY = _clean_api_key(os.getenv("GOOGLE_API_KEY"))

if GEMINI_API_KEY and not GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
    GOOGLE_API_KEY = GEMINI_API_KEY

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash")
_LLM: ChatGoogleGenerativeAI | None = None


def is_mock_mode() -> bool:
    """Return True when no Gemini API key is available."""
    return not bool(GEMINI_API_KEY or GOOGLE_API_KEY)


def get_llm() -> ChatGoogleGenerativeAI | None:
    """Create the Gemini chat model only when an API key exists."""
    global _LLM

    if is_mock_mode():
        return None

    if _LLM is None:
        _LLM = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.35)
    return _LLM


MOCK_QUESTIONS: dict[str, dict[str, tuple[str, list[str]]]] = {
    "AI Engineer Intern": {
        "tool calling": (
            "What is tool calling in an AI agent, and why is it useful?",
            [
                "model can call functions",
                "tools extend model capability",
                "tool results are returned to the model",
                "useful for search, calculation, databases, APIs",
            ],
        ),
        "LangChain": (
            "How does LangChain help developers build LLM applications?",
            [
                "connects prompts, models, and tools",
                "supports chains and structured workflows",
                "integrates with retrievers and external services",
            ],
        ),
        "RAG": (
            "What problem does retrieval augmented generation solve?",
            [
                "retrieves relevant external context",
                "reduces unsupported answers",
                "combines search results with model generation",
            ],
        ),
    },
    "Frontend Developer": {
        "React": (
            "What is the difference between state and props in React?",
            [
                "props are passed from parent",
                "state is managed inside component",
                "state changes trigger re-render",
            ],
        ),
        "accessibility": (
            "How would you make a form more accessible?",
            [
                "use labels connected to inputs",
                "support keyboard navigation",
                "show clear validation messages",
                "use semantic HTML",
            ],
        ),
    },
    "Backend Developer": {
        "REST APIs": (
            "What happens when a client sends a request to a REST API endpoint?",
            [
                "request reaches server",
                "route/controller handles it",
                "business logic runs",
                "database may be queried",
                "response is returned",
            ],
        ),
        "authentication": (
            "What is the difference between authentication and authorization?",
            [
                "authentication verifies identity",
                "authorization checks permissions",
                "both protect application resources",
            ],
        ),
    },
    "Data Analyst": {
        "SQL": (
            "What is the difference between WHERE and HAVING in SQL?",
            [
                "WHERE filters rows before grouping",
                "HAVING filters groups after aggregation",
            ],
        ),
        "data cleaning": (
            "How would you handle missing values in a dataset?",
            [
                "inspect why values are missing",
                "decide whether to remove or impute",
                "document the decision",
                "check impact on analysis",
            ],
        ),
    },
}


def _fallback_question(role: str, topic: str, difficulty: str) -> QuestionOutput:
    role_questions = MOCK_QUESTIONS.get(role, {})
    if topic in role_questions:
        question, expected_points = role_questions[topic]
    else:
        question = f"Can you explain a core {topic} concept for a {role} interview?"
        expected_points = [
            "define the concept clearly",
            "explain why it matters",
            "give a practical example",
        ]

    return QuestionOutput(
        question=question,
        topic=topic,
        difficulty=difficulty,
        expected_points=expected_points,
    )


def _mock_question(state: dict[str, Any]) -> QuestionOutput:
    role = state.get("role", "AI Engineer Intern")
    topic = state.get("target_topic") or state.get("next_topic") or ""
    difficulty = state.get("difficulty", "Easy")
    topics = ROLE_TOPICS.get(role, ROLE_TOPICS["AI Engineer Intern"])

    if not topic:
        index = min(state.get("question_count", 0), len(topics) - 1)
        topic = topics[index]

    question = _fallback_question(role, topic, difficulty)
    if question.question in state.get("asked_questions", []):
        next_index = (topics.index(question.topic) + 1) % len(topics) if question.topic in topics else 0
        question = _fallback_question(role, topics[next_index], difficulty)
    return question


def generate_question_chain(state: dict[str, Any]) -> QuestionOutput:
    """Generate one role-specific interview question."""
    if is_mock_mode():
        return _mock_question(state)

    llm = get_llm()
    if llm is None:
        return _mock_question(state)

    prompt = ChatPromptTemplate.from_template(QUESTION_GENERATION_PROMPT)
    chain = prompt | llm.with_structured_output(QuestionOutput)

    try:
        return chain.invoke(
            {
                "role": state.get("role", "AI Engineer Intern"),
                "difficulty": state.get("difficulty", "Easy"),
                "topic": state.get("target_topic") or state.get("next_topic") or "fundamentals",
                "weak_areas": ", ".join(state.get("weak_areas", [])) or "None yet",
                "asked_questions": " | ".join(state.get("asked_questions", [])) or "None yet",
                "difficulty_adjustment": choose_difficulty_adjustment(state.get("scores", [])),
            }
        )
    except Exception as error:
        print(f"[chains] Gemini question generation failed; using mock fallback. {error}")
        return _mock_question(state)


def _point_matches_answer(point: str, answer: str) -> bool:
    important_words = [
        word.strip(".,:;()").lower()
        for word in point.split()
        if len(word.strip(".,:;()")) > 3
    ]
    answer_lower = answer.lower()
    return any(word in answer_lower for word in important_words)


def _mock_grade(
    question: str,
    answer: str,
    expected_points: list[str],
    role: str,
    difficulty: str,
) -> GradeOutput:
    matched_points = [point for point in expected_points if _point_matches_answer(point, answer)]
    missing_points = [point for point in expected_points if point not in matched_points]

    score = 4 + len(matched_points) * 2
    if len(answer.split()) >= 35:
        score += 1
    score = validate_score(score)

    weak_area = missing_points[0] if missing_points else "deeper examples"
    sample_answer = (
        f"A strong {role} answer would explain that {question.lower()} "
        f"In practice, it should mention: {', '.join(expected_points)}."
    )

    return GradeOutput(
        score=score,
        strength="You gave a clear starting point." if matched_points else "You attempted the question honestly.",
        improvement=(
            f"Add detail about {missing_points[0]}."
            if missing_points
            else "Add a short real project or practice example."
        ),
        feedback=(
            "Good start. Your answer covers part of the idea, but it needs a little more precision."
            if missing_points
            else "Strong answer. You covered the key points and can improve by adding a concise example."
        ),
        missing_points=missing_points[:3],
        weak_area=weak_area,
        sample_answer=sample_answer,
        next_topic_suggestion=weak_area,
    )


def grade_answer_chain(
    question: str,
    answer: str,
    expected_points: list[str],
    role: str,
    difficulty: str,
) -> GradeOutput:
    """Grade an answer with Gemini structured output or mock logic."""
    if is_mock_mode():
        return _mock_grade(question, answer, expected_points, role, difficulty)

    llm = get_llm()
    if llm is None:
        return _mock_grade(question, answer, expected_points, role, difficulty)

    prompt = ChatPromptTemplate.from_template(ANSWER_GRADING_PROMPT)
    chain = prompt | llm.with_structured_output(GradeOutput)

    try:
        grade = chain.invoke(
            {
                "role": role,
                "difficulty": difficulty,
                "question": question,
                "expected_points": "\n".join(f"- {point}" for point in expected_points),
                "answer": answer,
            }
        )
        grade.score = validate_score(grade.score)
        grade.feedback = constructive_feedback_guard(limit_feedback_length(grade.feedback))
        grade.feedback = no_fake_experience_guard(grade.feedback)
        grade.sample_answer = no_fake_experience_guard(grade.sample_answer)
        return grade
    except Exception as error:
        print(f"[chains] Gemini answer grading failed; using mock fallback. {error}")
        return _mock_grade(question, answer, expected_points, role, difficulty)


def _readiness_from_average(average_score: float) -> str:
    if average_score >= 8:
        return "Strong readiness"
    if average_score >= 6:
        return "Medium readiness"
    return "Needs practice"


def _mock_final_report(state: dict[str, Any]) -> FinalReport:
    scores = state.get("scores", [])
    average_score = calculate_average_score(scores)
    weak_areas = get_weak_areas(state)[:5]
    strong_areas = list(dict.fromkeys(state.get("strong_areas", [])))[:5] or ["Clear communication"]
    recommended_topics = create_study_plan(weak_areas, state.get("role", "the role"))[:3]

    return FinalReport(
        average_score=average_score,
        readiness_level=_readiness_from_average(average_score),
        strong_areas=strong_areas,
        weak_areas=weak_areas or ["No major weak area detected yet"],
        recommended_topics=recommended_topics,
        practice_tasks=[
            "Write a 60-second answer for your weakest topic.",
            "Practice one answer using the STAR structure where relevant.",
            "Review one project and prepare a concise technical explanation.",
        ],
        final_message="Nice work finishing the session. Keep answers specific, honest, and tied to the role.",
    )


def generate_final_report_chain(state: dict[str, Any]) -> FinalReport:
    """Generate the final interview report."""
    if is_mock_mode():
        return _mock_final_report(state)

    llm = get_llm()
    if llm is None:
        return _mock_final_report(state)

    prompt = ChatPromptTemplate.from_template(FINAL_REPORT_PROMPT)
    chain = prompt | llm.with_structured_output(FinalReport)

    try:
        average_score = calculate_average_score(state.get("scores", []))
        report = chain.invoke(
            {
                "role": state.get("role", "AI Engineer Intern"),
                "difficulty": state.get("difficulty", "Easy"),
                "max_questions": state.get("max_questions", 5),
                "scores": state.get("scores", []),
                "average_score": average_score,
                "feedback_history": state.get("feedback_history", []),
                "strong_areas": state.get("strong_areas", []),
                "weak_areas": state.get("weak_areas", []),
            }
        )
        report.average_score = average_score
        report.final_message = no_fake_experience_guard(report.final_message)
        return report
    except Exception as error:
        print(f"[chains] Gemini final report failed; using mock fallback. {error}")
        return _mock_final_report(state)
