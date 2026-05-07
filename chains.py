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


MOCK_QUESTIONS: dict[str, dict[str, dict[str, dict[str, Any]]]] = {
    "AI Engineer": {
        "tool calling": {
            "Easy": {
                "question": "What is tool calling in an AI agent?",
                "choices": [
                    "A way for a model to call predefined functions or APIs",
                    "A method for manually editing every model response",
                    "A database table that stores interview questions",
                    "A replacement for prompts and instructions",
                ],
                "correct_answer": "A way for a model to call predefined functions or APIs",
                "expected_points": [
                    "model can call functions",
                    "tools extend model capability",
                    "tool results are returned to the model",
                ],
            },
            "Medium": {
                "question": "Which workflow best describes safe tool calling in an AI app?",
                "choices": [
                    "Let the model run any system command it wants",
                    "Define tool schemas, validate inputs, execute the tool, then return results to the model",
                    "Skip validation so tools respond faster",
                    "Store the user's API key inside every prompt",
                ],
                "correct_answer": "Define tool schemas, validate inputs, execute the tool, then return results to the model",
                "expected_points": [
                    "tool schemas define allowed inputs",
                    "inputs should be validated",
                    "tool results are passed back to the model",
                ],
            },
            "Hard": {
                "question": "An agent repeatedly calls the same search tool without answering. What is the best fix?",
                "choices": [
                    "Increase temperature so the model explores more",
                    "Add loop limits, clearer stopping criteria, and better tool result summaries",
                    "Remove all system instructions",
                    "Tell users to refresh the browser",
                ],
                "correct_answer": "Add loop limits, clearer stopping criteria, and better tool result summaries",
                "expected_points": [
                    "agent loops need iteration limits",
                    "stopping criteria should be clear",
                    "tool outputs should be summarized for the model",
                ],
            },
        },
        "RAG": {
            "Easy": {
                "question": "What problem does RAG usually help solve?",
                "choices": [
                    "It gives the model relevant external context before answering",
                    "It guarantees every answer is short",
                    "It removes the need for documents",
                    "It turns Python code into SQL",
                ],
                "correct_answer": "It gives the model relevant external context before answering",
                "expected_points": [
                    "retrieves relevant external context",
                    "reduces unsupported answers",
                    "combines retrieval with generation",
                ],
            }
        },
    },
    "Frontend Developer": {
        "React": {
            "Easy": {
                "question": "What is the difference between props and state in React?",
                "choices": [
                    "Props are passed into a component, while state is managed inside a component",
                    "Props are only used for CSS, while state is only used for HTML",
                    "Props trigger network requests, while state stores API keys",
                    "There is no difference",
                ],
                "correct_answer": "Props are passed into a component, while state is managed inside a component",
                "expected_points": [
                    "props are passed from parent",
                    "state is managed inside component",
                    "state changes can trigger re-render",
                ],
            },
            "Medium": {
                "question": "A React component needs to update the screen after a button click. What should usually change?",
                "choices": [
                    "The component's state",
                    "The package-lock file",
                    "The browser URL only",
                    "The HTML file outside React",
                ],
                "correct_answer": "The component's state",
                "expected_points": [
                    "state stores changing UI data",
                    "state updates trigger re-render",
                    "events can update state",
                ],
            },
            "Hard": {
                "question": "A React page re-renders too often because derived data is recalculated every render. What is a likely optimization?",
                "choices": [
                    "Use memoization carefully and avoid unnecessary state updates",
                    "Move all code into one giant component",
                    "Disable accessibility labels",
                    "Replace every prop with global variables",
                ],
                "correct_answer": "Use memoization carefully and avoid unnecessary state updates",
                "expected_points": [
                    "avoid unnecessary state changes",
                    "memoization can reduce repeated calculations",
                    "measure performance before over-optimizing",
                ],
            },
        },
        "accessibility": {
            "Easy": {
                "question": "Which choice makes a form input more accessible?",
                "choices": [
                    "Connect a visible label to the input",
                    "Use placeholder text as the only label",
                    "Remove keyboard focus styles",
                    "Put all form fields inside images",
                ],
                "correct_answer": "Connect a visible label to the input",
                "expected_points": [
                    "labels identify inputs",
                    "keyboard and screen reader users benefit",
                    "semantic HTML improves accessibility",
                ],
            }
        },
    },
    "Backend Developer": {
        "REST APIs": {
            "Easy": {
                "question": "What usually happens when a client sends a request to a REST API endpoint?",
                "choices": [
                    "The server routes the request, runs logic, and returns a response",
                    "The browser edits the database directly",
                    "The API automatically writes frontend CSS",
                    "The request is ignored unless it is a POST",
                ],
                "correct_answer": "The server routes the request, runs logic, and returns a response",
                "expected_points": [
                    "request reaches server",
                    "route or controller handles it",
                    "response is returned",
                ],
            },
            "Medium": {
                "question": "A REST endpoint receives invalid JSON. What should the backend usually do?",
                "choices": [
                    "Validate the input and return a clear 400-level error",
                    "Crash the server so the bug is obvious",
                    "Store the invalid JSON anyway",
                    "Return a successful response with empty data",
                ],
                "correct_answer": "Validate the input and return a clear 400-level error",
                "expected_points": [
                    "validate request input",
                    "return appropriate client error",
                    "avoid crashing the server",
                ],
            },
            "Hard": {
                "question": "An API is slow because it repeatedly fetches unchanged reference data. What is a practical fix?",
                "choices": [
                    "Add caching with clear invalidation rules",
                    "Remove all error handling",
                    "Make every request run in the browser console",
                    "Return less accurate data without telling users",
                ],
                "correct_answer": "Add caching with clear invalidation rules",
                "expected_points": [
                    "caching can reduce repeated work",
                    "invalidation keeps cached data correct",
                    "performance changes should be measured",
                ],
            },
        },
        "authentication": {
            "Easy": {
                "question": "What is authentication?",
                "choices": [
                    "Verifying who a user is",
                    "Choosing a website color palette",
                    "Compressing images",
                    "Sorting database rows",
                ],
                "correct_answer": "Verifying who a user is",
                "expected_points": [
                    "authentication verifies identity",
                    "authorization checks permissions",
                    "both protect resources",
                ],
            }
        },
    },
    "Data Analyst": {
        "SQL": {
            "Easy": {
                "question": "What is the difference between WHERE and HAVING in SQL?",
                "choices": [
                    "WHERE filters rows before grouping, while HAVING filters groups after aggregation",
                    "WHERE only works in Excel, while HAVING only works in Python",
                    "WHERE sorts results, while HAVING joins tables",
                    "They always do exactly the same thing",
                ],
                "correct_answer": "WHERE filters rows before grouping, while HAVING filters groups after aggregation",
                "expected_points": [
                    "WHERE filters rows before grouping",
                    "HAVING filters groups after aggregation",
                    "HAVING is often used with aggregate functions",
                ],
            },
            "Medium": {
                "question": "You need sales totals by region, but only for regions above $10,000 total sales. What should you use?",
                "choices": [
                    "GROUP BY region with HAVING SUM(sales) > 10000",
                    "WHERE SUM(sales) > 10000 before GROUP BY",
                    "ORDER BY sales without grouping",
                    "DELETE rows below 10000",
                ],
                "correct_answer": "GROUP BY region with HAVING SUM(sales) > 10000",
                "expected_points": [
                    "GROUP BY creates regional groups",
                    "SUM aggregates sales",
                    "HAVING filters aggregated groups",
                ],
            },
            "Hard": {
                "question": "A dashboard metric changes after duplicate customer rows appear. What is the best first step?",
                "choices": [
                    "Inspect joins and deduplication rules before changing the metric",
                    "Hide the metric until nobody asks",
                    "Round all numbers down",
                    "Switch from SQL to screenshots",
                ],
                "correct_answer": "Inspect joins and deduplication rules before changing the metric",
                "expected_points": [
                    "duplicates can come from joins",
                    "deduplication rules should match business logic",
                    "metric changes need investigation",
                ],
            },
        },
        "data cleaning": {
            "Easy": {
                "question": "What should you do first when you find missing values in a dataset?",
                "choices": [
                    "Investigate why values are missing and how many are affected",
                    "Always replace them with zero",
                    "Delete the full dataset",
                    "Ignore them in every analysis",
                ],
                "correct_answer": "Investigate why values are missing and how many are affected",
                "expected_points": [
                    "inspect why values are missing",
                    "measure the amount of missing data",
                    "choose removal or imputation carefully",
                ],
            }
        },
    },
}


def _generic_question(role: str, topic: str, difficulty: str) -> QuestionOutput:
    if difficulty == "Hard":
        question = f"In a {role} interview, what is the strongest way to reason about a tricky {topic} problem?"
    elif difficulty == "Medium":
        question = f"In a practical {role} scenario, what is the best way to use {topic}?"
    else:
        question = f"Which option best describes {topic} for a {role} role?"

    correct_answer = (
        f"Define {topic}, connect it to a real use case, and explain the tradeoff or result"
    )
    return QuestionOutput(
        question=question,
        topic=topic,
        difficulty=difficulty,
        choices=[
            "Memorize a keyword without context",
            correct_answer,
            "Avoid explaining the concept unless asked twice",
            "Treat it as unrelated to the role",
        ],
        correct_answer=correct_answer,
        expected_points=[
            "define the concept clearly",
            "connect it to the role",
            "include a practical example or tradeoff",
        ],
    )


def _fallback_question(role: str, topic: str, difficulty: str) -> QuestionOutput:
    role_questions = MOCK_QUESTIONS.get(role, {})
    topic_questions = role_questions.get(topic, {})
    spec = topic_questions.get(difficulty) or topic_questions.get("Easy")

    if not spec:
        return _generic_question(role, topic, difficulty)

    return QuestionOutput(
        question=spec["question"],
        topic=topic,
        difficulty=difficulty,
        choices=spec["choices"],
        correct_answer=spec["correct_answer"],
        expected_points=spec["expected_points"],
    )


def _mock_question(state: dict[str, Any]) -> QuestionOutput:
    role = state.get("role", "AI Engineer")
    topic = state.get("target_topic") or state.get("next_topic") or ""
    difficulty = state.get("difficulty", "Easy")
    topics = ROLE_TOPICS.get(role, ROLE_TOPICS["AI Engineer"])

    if not topic:
        index = min(state.get("question_count", 0), len(topics) - 1)
        topic = topics[index]

    question = _fallback_question(role, topic, difficulty)
    if question.question in state.get("asked_questions", []):
        next_index = (topics.index(question.topic) + 1) % len(topics) if question.topic in topics else 0
        question = _fallback_question(role, topics[next_index], difficulty)
    return question


def _validate_question_output(question: QuestionOutput, state: dict[str, Any]) -> QuestionOutput:
    choices = [choice.strip() for choice in question.choices if choice and choice.strip()]
    choices = list(dict.fromkeys(choices))
    if len(choices) != 4 or question.correct_answer not in choices:
        return _mock_question(state)

    question.choices = choices
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
        question = chain.invoke(
            {
                "role": state.get("role", "AI Engineer"),
                "difficulty": state.get("difficulty", "Easy"),
                "topic": state.get("target_topic") or state.get("next_topic") or "fundamentals",
                "weak_areas": ", ".join(state.get("weak_areas", [])) or "None yet",
                "asked_questions": " | ".join(state.get("asked_questions", [])) or "None yet",
                "difficulty_adjustment": choose_difficulty_adjustment(state.get("scores", [])),
            }
        )
        return _validate_question_output(question, state)
    except Exception as error:
        print(f"[chains] Gemini question generation failed; using mock fallback. {error}")
        return _mock_question(state)


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
) -> GradeOutput:
    correct = _is_correct_choice(answer, correct_answer)
    score = 10 if correct else {"Easy": 4, "Medium": 3, "Hard": 2}.get(difficulty, 3)
    missing_points = [] if correct else expected_points[:3]
    weak_area = "deeper reasoning" if correct else expected_points[0]
    explanation = (
        f"The correct answer is: {correct_answer}. "
        f"It matters because {', '.join(expected_points[:3])}."
    )

    return GradeOutput(
        score=score,
        strength=(
            "You selected the best option."
            if correct
            else "You made a choice and can use the explanation to sharpen the concept."
        ),
        improvement=(
            "Keep going and watch for scenario details."
            if correct
            else f"Review why this answer points to {expected_points[0]}."
        ),
        feedback=(
            "Correct. Nice read of the concept."
            if correct
            else "Not quite. Review the correct option and the key idea behind it."
        ),
        missing_points=missing_points[:3],
        weak_area=weak_area,
        correct_answer=correct_answer,
        sample_answer=explanation,
        next_topic_suggestion=weak_area,
    )


def grade_answer_chain(
    question: str,
    answer: str,
    choices: list[str],
    correct_answer: str,
    expected_points: list[str],
    role: str,
    difficulty: str,
) -> GradeOutput:
    """Grade an MCQ selection with Gemini structured output or mock logic."""
    if is_mock_mode():
        return _mock_grade(question, answer, choices, correct_answer, expected_points, role, difficulty)

    llm = get_llm()
    if llm is None:
        return _mock_grade(question, answer, choices, correct_answer, expected_points, role, difficulty)

    prompt = ChatPromptTemplate.from_template(ANSWER_GRADING_PROMPT)
    chain = prompt | llm.with_structured_output(GradeOutput)

    try:
        grade = chain.invoke(
            {
                "role": role,
                "difficulty": difficulty,
                "question": question,
                "choices": "\n".join(f"- {choice}" for choice in choices),
                "correct_answer": correct_answer,
                "expected_points": "\n".join(f"- {point}" for point in expected_points),
                "answer": answer,
            }
        )
        if _is_correct_choice(answer, correct_answer):
            grade.score = max(validate_score(grade.score), 8)
            grade.missing_points = []
        else:
            grade.score = min(validate_score(grade.score), 6)
        grade.score = validate_score(grade.score)
        grade.correct_answer = correct_answer
        grade.feedback = constructive_feedback_guard(limit_feedback_length(grade.feedback))
        grade.feedback = no_fake_experience_guard(grade.feedback)
        grade.sample_answer = no_fake_experience_guard(grade.sample_answer)
        return grade
    except Exception as error:
        print(f"[chains] Gemini answer grading failed; using mock fallback. {error}")
        return _mock_grade(question, answer, choices, correct_answer, expected_points, role, difficulty)


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
            "Complete 10 MCQs on your weakest topic.",
            "Review one short tutorial for each missed concept.",
            "Explain one project decision out loud in 60 seconds.",
        ],
        final_message="Nice work finishing the session. Keep choices grounded in the concept and tied to the role.",
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
                "role": state.get("role", "AI Engineer"),
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
