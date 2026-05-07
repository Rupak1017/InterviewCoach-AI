"""LangChain Gemini chains with deterministic mock fallbacks."""

from __future__ import annotations

import os
import time
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
from models import FinalReport, GradeOutput, PrepSource, QuestionOutput, QuickPrep
from prompts import (
    ANSWER_GRADING_PROMPT,
    FINAL_REPORT_PROMPT,
    QUESTION_GENERATION_PROMPT,
    QUICK_PREP_PROMPT,
)
from tools import (
    calculate_average_score,
    choose_subtopic,
    fallback_mcq_question,
    get_weak_areas,
    is_duplicate_question,
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


def _prep_sources(sources: list[dict[str, Any]] | list[PrepSource], limit: int = 4) -> list[PrepSource]:
    prepared: list[PrepSource] = []
    for source in sources[:limit]:
        if isinstance(source, PrepSource):
            prepared.append(source)
        else:
            prepared.append(
                PrepSource(
                    title=source.get("title", "Study source"),
                    url=source.get("url", ""),
                    snippet=source.get("snippet", ""),
                )
            )
    return prepared


def _source_snippets(sources: list[dict[str, Any]] | list[PrepSource]) -> str:
    lines = []
    for source in _prep_sources(sources, limit=5):
        lines.append(f"- {source.title}: {source.snippet} ({source.url})")
    return "\n".join(lines) if lines else "No sources available."


def _mock_quick_prep(role: str, topic: str, difficulty: str, sources: list[dict[str, Any]]) -> QuickPrep:
    return QuickPrep(
        overview=(
            f"For a {role} interview, {topic} is worth understanding at a practical level. "
            f"At {difficulty} difficulty, focus on explaining the idea clearly, naming the tradeoff, "
            "and connecting it to a small example."
        ),
        key_points=[
            f"Know the core definition of {topic}.",
            "Be ready to explain when you would use it and what can go wrong.",
        ],
        common_mistake="Giving only a memorized definition without explaining the practical impact.",
        sources=_prep_sources(sources),
    )


def generate_quick_prep_chain(state: dict[str, Any]) -> QuickPrep:
    """Generate a short prep card for the current topic."""
    role = state.get("role", "AI Engineer")
    topic = state.get("current_topic") or state.get("selected_topic") or "fundamentals"
    difficulty = state.get("difficulty", "Easy")
    sources = state.get("study_sources", [])

    if is_mock_mode():
        return _mock_quick_prep(role, topic, difficulty, sources)

    llm = get_llm()
    if llm is None:
        return _mock_quick_prep(role, topic, difficulty, sources)

    prompt = ChatPromptTemplate.from_template(QUICK_PREP_PROMPT)
    chain = prompt | llm.with_structured_output(QuickPrep)

    try:
        prep = chain.invoke(
            {
                "role": role,
                "topic": topic,
                "difficulty": difficulty,
                "source_snippets": _source_snippets(sources),
            }
        )
        prep.sources = _prep_sources(sources)
        return prep
    except Exception as error:
        print(f"[chains] Gemini quick prep failed; using mock fallback. {error}")
        return _mock_quick_prep(role, topic, difficulty, sources)


def _mock_question(state: dict[str, Any]) -> QuestionOutput:
    role = state.get("role", "AI Engineer")
    topic = state.get("current_topic") or state.get("selected_topic") or "fundamentals"
    difficulty = state.get("difficulty", "Easy")
    asked_questions = state.get("asked_questions", [])
    subtopic = state.get("current_subtopic") or choose_subtopic(
        topic,
        state.get("question_count", 0),
        asked_questions,
    )
    return fallback_mcq_question(role, topic, difficulty, subtopic, asked_questions)


def _validate_question_output(question: QuestionOutput, state: dict[str, Any]) -> QuestionOutput:
    choices = [choice.strip() for choice in question.choices if choice and choice.strip()]
    choices = list(dict.fromkeys(choices))
    if len(choices) != 3 or question.correct_answer not in choices:
        return _mock_question(state)

    question.choices = choices
    return question


def generate_question_chain(state: dict[str, Any]) -> QuestionOutput:
    """Generate one role-specific MCQ interview question."""
    started = time.perf_counter()
    topic = state.get("current_topic") or "fundamentals"
    asked_questions = state.get("asked_questions", [])
    subtopic = state.get("current_subtopic") or choose_subtopic(
        topic,
        state.get("question_count", 0),
        asked_questions,
    )
    print("[question-generation] topic:", topic)
    print("[question-generation] subtopic:", subtopic)
    print("[question-generation] asked_count:", len(asked_questions))

    if is_mock_mode():
        question = _mock_question({**state, "current_subtopic": subtopic})
        duplicate = is_duplicate_question(question.question, asked_questions)
        print("[question-generation] generated:", question.question)
        print("[question-generation] duplicate:", duplicate)
        print(f"[timing] Gemini question generation took {time.perf_counter() - started:.2f}s")
        return question

    llm = get_llm()
    if llm is None:
        question = _mock_question({**state, "current_subtopic": subtopic})
        print("[question-generation] generated:", question.question)
        print("[question-generation] duplicate:", is_duplicate_question(question.question, asked_questions))
        print(f"[timing] Gemini question generation took {time.perf_counter() - started:.2f}s")
        return question

    prompt = ChatPromptTemplate.from_template(QUESTION_GENERATION_PROMPT)
    chain = prompt | llm.with_structured_output(QuestionOutput)

    try:
        question = chain.invoke(
            {
                "role": state.get("role", "AI Engineer"),
                "topic": topic,
                "subtopic": subtopic,
                "difficulty": state.get("difficulty", "Easy"),
                "quick_prep": state.get("quick_prep", {}).get("overview", ""),
                "weak_areas": ", ".join(state.get("weak_areas", [])) or "None yet",
                "asked_questions": " | ".join(asked_questions) or "None yet",
                "anti_repeat_note": "First attempt.",
            }
        )
        question = _validate_question_output(question, {**state, "current_subtopic": subtopic})
        duplicate = is_duplicate_question(question.question, asked_questions)
        print("[question-generation] generated:", question.question)
        print("[question-generation] duplicate:", duplicate)
        if not duplicate:
            return question

        question = chain.invoke(
            {
                "role": state.get("role", "AI Engineer"),
                "topic": topic,
                "subtopic": subtopic,
                "difficulty": state.get("difficulty", "Easy"),
                "quick_prep": state.get("quick_prep", {}).get("overview", ""),
                "weak_areas": ", ".join(state.get("weak_areas", [])) or "None yet",
                "asked_questions": " | ".join(asked_questions) or "None yet",
                "anti_repeat_note": (
                    "The previous attempt was too similar. Use a different subtopic angle, "
                    "different wording, and a different correct answer focus."
                ),
            }
        )
        question = _validate_question_output(question, {**state, "current_subtopic": subtopic})
        duplicate = is_duplicate_question(question.question, asked_questions)
        print("[question-generation] generated:", question.question)
        print("[question-generation] duplicate:", duplicate)
        if duplicate:
            return fallback_mcq_question(
                state.get("role", "AI Engineer"),
                topic,
                state.get("difficulty", "Easy"),
                subtopic,
                asked_questions,
            )
        return question
    except Exception as error:
        print(f"[chains] Gemini question generation failed; using mock fallback. {error}")
        return _mock_question({**state, "current_subtopic": subtopic})
    finally:
        print(f"[timing] Gemini question generation took {time.perf_counter() - started:.2f}s")


def _is_correct_choice(answer: str, correct_answer: str) -> bool:
    return answer.strip().casefold() == correct_answer.strip().casefold()


def _mock_grade(
    question: str,
    answer: str,
    choices: list[str],
    correct_answer: str,
    expected_points: list[str],
    role: str,
    difficulty: str,
    topic: str,
    sources: list[dict[str, Any]],
) -> GradeOutput:
    correct = _is_correct_choice(answer, correct_answer)
    score = 10 if correct else {"Easy": 4, "Medium": 3, "Hard": 2}.get(difficulty, 3)
    missing_points = [] if correct else expected_points[:3]
    weak_area = "" if correct else topic
    source_models = _prep_sources(sources)
    sample_answer = (
        f"The best option is: {correct_answer} It works because it covers "
        f"{', '.join(expected_points[:3])}."
    )

    return GradeOutput(
        score=score,
        strength=(
            "You selected the best option."
            if correct
            else "You made a selection and can use the explanation to sharpen the concept."
        ),
        improvement=(
            "Keep watching for scenario details."
            if correct
            else f"Review why the correct option covers {expected_points[0]}."
        ),
        feedback=(
            "Correct. Nice read of the concept."
            if correct
            else "Not quite. Review the correct option and the key idea behind it."
        ),
        missing_points=missing_points[:3],
        weak_area=weak_area,
        correct_answer=correct_answer,
        sample_answer=sample_answer,
        study_next=[
            f"Review {topic} fundamentals.",
            "Practice explaining why the correct option is better than the distractors.",
        ],
        recommended_links=source_models[:4],
    )


def grade_answer_chain(
    question: str,
    answer: str,
    choices: list[str],
    correct_answer: str,
    expected_points: list[str],
    role: str,
    difficulty: str,
    topic: str,
    sources: list[dict[str, Any]],
) -> GradeOutput:
    """Grade an MCQ selection with Gemini structured output or mock logic."""
    started = time.perf_counter()
    if is_mock_mode():
        try:
            return _mock_grade(question, answer, choices, correct_answer, expected_points, role, difficulty, topic, sources)
        finally:
            print(f"[timing] Gemini answer grading took {time.perf_counter() - started:.2f}s")

    llm = get_llm()
    if llm is None:
        try:
            return _mock_grade(question, answer, choices, correct_answer, expected_points, role, difficulty, topic, sources)
        finally:
            print(f"[timing] Gemini answer grading took {time.perf_counter() - started:.2f}s")

    prompt = ChatPromptTemplate.from_template(ANSWER_GRADING_PROMPT)
    chain = prompt | llm.with_structured_output(GradeOutput)

    try:
        grade = chain.invoke(
            {
                "role": role,
                "difficulty": difficulty,
                "topic": topic,
                "question": question,
                "choices": "\n".join(f"- {choice}" for choice in choices),
                "correct_answer": correct_answer,
                "expected_points": "\n".join(f"- {point}" for point in expected_points),
                "answer": answer,
                "source_snippets": _source_snippets(sources),
            }
        )
        if _is_correct_choice(answer, correct_answer):
            grade.score = max(validate_score(grade.score), 8)
            grade.missing_points = []
        else:
            grade.score = min(validate_score(grade.score), 6)
        grade.score = validate_score(grade.score)
        grade.correct_answer = correct_answer
        grade.feedback = no_fake_experience_guard(
            constructive_feedback_guard(limit_feedback_length(grade.feedback))
        )
        grade.sample_answer = no_fake_experience_guard(grade.sample_answer)
        grade.recommended_links = _prep_sources(sources)
        if grade.score >= 8:
            grade.weak_area = ""
        elif not grade.weak_area:
            grade.weak_area = topic
        return grade
    except Exception as error:
        print(f"[chains] Gemini answer grading failed; using mock fallback. {error}")
        return _mock_grade(question, answer, choices, correct_answer, expected_points, role, difficulty, topic, sources)
    finally:
        print(f"[timing] Gemini answer grading took {time.perf_counter() - started:.2f}s")


def _readiness_from_average(average_score: float) -> str:
    if average_score >= 8:
        return "Strong readiness"
    if average_score >= 6:
        return "Medium readiness"
    return "Needs practice"


def _unique_sources(sources: list[dict[str, Any]], limit: int = 5) -> list[PrepSource]:
    unique: list[PrepSource] = []
    seen_urls: set[str] = set()
    for source in _prep_sources(sources, limit=20):
        if source.url in seen_urls:
            continue
        seen_urls.add(source.url)
        unique.append(source)
    return unique[:limit]


def _mock_final_report(state: dict[str, Any]) -> FinalReport:
    scores = state.get("scores", [])
    average_score = calculate_average_score(scores)
    weak_areas = get_weak_areas(state)[:5]
    strong_areas = list(dict.fromkeys(state.get("strong_areas", [])))[:5] or ["Clear communication"]
    sources = _unique_sources(state.get("study_sources", []), limit=5)

    return FinalReport(
        average_score=average_score,
        readiness_level=_readiness_from_average(average_score),
        strong_areas=strong_areas,
        weak_areas=weak_areas or ["No major weak area detected yet"],
        recommended_topics=weak_areas[:3] or [state.get("current_topic", "interview fundamentals")],
        useful_sources=sources,
        practice_tasks=[
            "Write a 60-second answer for your weakest topic.",
            "Practice one answer with a definition, example, and tradeoff.",
            "Review the useful links and rewrite one answer more clearly.",
        ],
        final_message="Nice work finishing Guided Practice Mode. Keep answers honest, specific, and tied to the role.",
    )


def generate_final_report_chain(state: dict[str, Any]) -> FinalReport:
    """Generate the final guided practice report."""
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
                "role": state.get("role", "AI Engineer"),
                "selected_topic": state.get("selected_topic", ""),
                "difficulty": state.get("difficulty", "Easy"),
                "max_questions": state.get("max_questions", 5),
                "scores": state.get("scores", []),
                "average_score": average_score,
                "feedback_history": state.get("feedback_history", []),
                "strong_areas": state.get("strong_areas", []),
                "weak_areas": state.get("weak_areas", []),
                "source_snippets": _source_snippets(state.get("study_sources", [])),
            }
        )
        report.average_score = average_score
        report.final_message = no_fake_experience_guard(report.final_message)
        report.useful_sources = _unique_sources(state.get("study_sources", []), limit=5)
        return report
    except Exception as error:
        print(f"[chains] Gemini final report failed; using mock fallback. {error}")
        return _mock_final_report(state)
