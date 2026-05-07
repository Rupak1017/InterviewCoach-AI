"""Simple tools for Guided Practice Mode."""

from __future__ import annotations

import os
import re
import string
import time
from collections import Counter
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv

from middleware import tool_call_logger
from models import GradeOutput, PrepSource, QuestionOutput
from storage import save_answer, save_session_to_json as storage_save_session_to_json


load_dotenv()

PLACEHOLDER_KEYS = {
    "your_tavily_api_key_here",
    "your_key_here",
    "your_real_key_here",
}


ROLE_TOPICS = {
    "AI Engineer": [
        "Python",
        "AWS Bedrock",
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


SUBTOPICS = {
    "langchain": [
        "overview",
        "prompt templates",
        "chains",
        "tools",
        "agents",
        "structured output",
        "RAG",
        "memory",
        "callbacks",
        "use cases",
    ],
    "langgraph": [
        "state",
        "nodes",
        "edges",
        "conditional routing",
        "loops",
        "persistence",
        "human-in-the-loop",
        "tool workflows",
    ],
    "react hooks": [
        "useState",
        "useEffect",
        "dependency array",
        "cleanup functions",
        "useMemo",
        "useCallback",
        "useRef",
        "custom hooks",
    ],
    "sql joins": [
        "INNER JOIN",
        "LEFT JOIN",
        "RIGHT JOIN",
        "FULL JOIN",
        "join conditions",
        "filtering joined data",
        "duplicate rows",
    ],
    "rest apis": [
        "routes",
        "methods",
        "status codes",
        "request body",
        "authentication",
        "error handling",
        "pagination",
    ],
    "python": [
        "variables",
        "functions",
        "decorators",
        "classes",
        "exceptions",
        "list comprehensions",
        "modules",
    ],
}


GENERIC_SUBTOPICS = [
    "definition",
    "use case",
    "common mistake",
    "example",
    "comparison",
    "debugging",
]


MCQ_BANKS = {
    "langchain": [
        {
            "subtopic": "tools",
            "question": "What is the main purpose of LangChain tools?",
            "choices": [
                "To let the model call external functions or APIs",
                "To train a new language model from scratch",
                "To store CSS styles",
            ],
            "correct_answer": "To let the model call external functions or APIs",
            "expected_points": [
                "tools connect models to external functions",
                "tools can call APIs or app logic",
                "tool results are returned to the model",
            ],
        },
        {
            "subtopic": "structured output",
            "question": "Why is structured output useful in LangChain?",
            "choices": [
                "It forces model responses into predictable fields",
                "It makes the model run without prompts",
                "It removes the need to validate important data",
            ],
            "correct_answer": "It forces model responses into predictable fields",
            "expected_points": [
                "structured output creates predictable fields",
                "Pydantic schemas help validation",
                "apps can safely render or store results",
            ],
        },
        {
            "subtopic": "RAG",
            "question": "In a RAG app, what role can LangChain help with?",
            "choices": [
                "Connecting retrieval, prompts, and model calls",
                "Designing HTML layouts",
                "Compiling Java code",
            ],
            "correct_answer": "Connecting retrieval, prompts, and model calls",
            "expected_points": [
                "retrieval finds relevant context",
                "prompts combine context with the question",
                "model calls generate the final answer",
            ],
        },
    ],
    "langgraph": [
        {
            "subtopic": "state",
            "question": "What is LangGraph state used for?",
            "choices": [
                "Passing shared data between graph nodes",
                "Styling Streamlit buttons",
                "Replacing all prompts",
            ],
            "correct_answer": "Passing shared data between graph nodes",
            "expected_points": [
                "state stores shared workflow data",
                "nodes can read and update state",
                "state helps keep the graph organized",
            ],
        },
        {
            "subtopic": "conditional routing",
            "question": "Why would you use conditional routing in LangGraph?",
            "choices": [
                "To decide the next node based on current state",
                "To make every node run at the same time",
                "To hide errors from users",
            ],
            "correct_answer": "To decide the next node based on current state",
            "expected_points": [
                "routing can inspect state",
                "different paths support different outcomes",
                "conditions keep workflows flexible",
            ],
        },
        {
            "subtopic": "nodes",
            "question": "What is a node in a LangGraph workflow?",
            "choices": [
                "A function that performs one step and returns state updates",
                "A database table for storing chat messages",
                "A CSS component for page layout",
            ],
            "correct_answer": "A function that performs one step and returns state updates",
            "expected_points": [
                "nodes are workflow steps",
                "nodes run logic",
                "nodes update graph state",
            ],
        },
    ],
    "react hooks": [
        {
            "subtopic": "useState",
            "question": "What does useState do in React?",
            "choices": [
                "Stores component state and triggers re-renders when updated",
                "Creates a backend API endpoint",
                "Deletes props from a parent component",
            ],
            "correct_answer": "Stores component state and triggers re-renders when updated",
            "expected_points": [
                "useState stores local component data",
                "state updates trigger re-renders",
                "it is useful for interactive UI",
            ],
        },
        {
            "subtopic": "useEffect",
            "question": "When is useEffect commonly used?",
            "choices": [
                "For side effects like fetching data or syncing with external systems",
                "For writing HTML outside React",
                "For replacing JavaScript functions",
            ],
            "correct_answer": "For side effects like fetching data or syncing with external systems",
            "expected_points": [
                "useEffect handles side effects",
                "effects can fetch or sync data",
                "dependencies control when effects run",
            ],
        },
        {
            "subtopic": "cleanup functions",
            "question": "Why might a React effect return a cleanup function?",
            "choices": [
                "To unsubscribe or clean up work before the effect runs again or unmounts",
                "To permanently disable component rendering",
                "To convert JSX into SQL",
            ],
            "correct_answer": "To unsubscribe or clean up work before the effect runs again or unmounts",
            "expected_points": [
                "cleanup prevents leaks",
                "cleanup can unsubscribe listeners",
                "cleanup runs before rerun or unmount",
            ],
        },
    ],
    "sql joins": [
        {
            "subtopic": "INNER JOIN",
            "question": "What does an INNER JOIN return?",
            "choices": [
                "Rows that have matching values in both joined tables",
                "Every row from both tables whether matched or not",
                "Only rows with NULL values",
            ],
            "correct_answer": "Rows that have matching values in both joined tables",
            "expected_points": [
                "INNER JOIN requires matches",
                "join conditions define matching rows",
                "unmatched rows are excluded",
            ],
        },
        {
            "subtopic": "LEFT JOIN",
            "question": "What does a LEFT JOIN preserve?",
            "choices": [
                "All rows from the left table and matching rows from the right table",
                "Only rows that match in both tables",
                "Only rows from the right table",
            ],
            "correct_answer": "All rows from the left table and matching rows from the right table",
            "expected_points": [
                "LEFT JOIN keeps all left rows",
                "right table values are NULL when unmatched",
                "join conditions still matter",
            ],
        },
        {
            "subtopic": "duplicate rows",
            "question": "Why can SQL joins accidentally create duplicate rows?",
            "choices": [
                "One row can match multiple rows in the other table",
                "SELECT always duplicates rows by default",
                "WHERE clauses only work after duplicates appear",
            ],
            "correct_answer": "One row can match multiple rows in the other table",
            "expected_points": [
                "many-to-one or many-to-many matches can duplicate rows",
                "join keys affect row counts",
                "deduplication should follow business logic",
            ],
        },
    ],
    "rest apis": [
        {
            "subtopic": "status codes",
            "question": "What does a 404 response usually mean in a REST API?",
            "choices": [
                "The requested resource was not found",
                "The request succeeded and returned data",
                "The server requires a CSS file",
            ],
            "correct_answer": "The requested resource was not found",
            "expected_points": [
                "404 means not found",
                "status codes communicate response outcomes",
                "clients can handle errors based on status",
            ],
        },
        {
            "subtopic": "methods",
            "question": "Which REST method is usually used to retrieve data?",
            "choices": [
                "GET",
                "PATCH",
                "DELETE",
            ],
            "correct_answer": "GET",
            "expected_points": [
                "GET retrieves data",
                "methods communicate intent",
                "safe methods should not modify resources",
            ],
        },
        {
            "subtopic": "pagination",
            "question": "Why do APIs often use pagination?",
            "choices": [
                "To return large result sets in smaller, manageable chunks",
                "To force every response to fail once",
                "To remove authentication requirements",
            ],
            "correct_answer": "To return large result sets in smaller, manageable chunks",
            "expected_points": [
                "pagination limits response size",
                "clients can request more pages",
                "pagination improves performance and usability",
            ],
        },
    ],
    "python": [
        {
            "subtopic": "decorators",
            "question": "What is a Python decorator commonly used for?",
            "choices": [
                "Wrapping a function to add behavior without changing its core code",
                "Changing Python into JavaScript",
                "Storing database rows automatically",
            ],
            "correct_answer": "Wrapping a function to add behavior without changing its core code",
            "expected_points": [
                "decorators wrap functions",
                "decorators add reusable behavior",
                "decorators keep core function code cleaner",
            ],
        },
        {
            "subtopic": "exceptions",
            "question": "Why use try/except in Python?",
            "choices": [
                "To handle expected errors without crashing the whole program",
                "To make code run in reverse order",
                "To delete all variables after a function",
            ],
            "correct_answer": "To handle expected errors without crashing the whole program",
            "expected_points": [
                "try/except handles errors",
                "expected failures can be managed",
                "programs can recover or show helpful messages",
            ],
        },
        {
            "subtopic": "list comprehensions",
            "question": "What is a Python list comprehension useful for?",
            "choices": [
                "Creating a list from an iterable with concise transformation or filtering",
                "Opening a web server automatically",
                "Replacing all classes",
            ],
            "correct_answer": "Creating a list from an iterable with concise transformation or filtering",
            "expected_points": [
                "list comprehensions build lists",
                "they can transform iterable values",
                "they can include filtering conditions",
            ],
        },
    ],
}


MOCK_SOURCES = {
    "React": [
        {
            "title": "React Docs",
            "url": "https://react.dev/learn",
            "snippet": "Official React learning docs for components, state, effects, and hooks.",
        },
        {
            "title": "MDN JavaScript Guide",
            "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
            "snippet": "MDN guide covering JavaScript fundamentals used in frontend interviews.",
        },
    ],
    "SQL": [
        {
            "title": "PostgreSQL SELECT Documentation",
            "url": "https://www.postgresql.org/docs/current/sql-select.html",
            "snippet": "Official PostgreSQL docs for SELECT, joins, grouping, and filtering.",
        },
        {
            "title": "Mode SQL Tutorial",
            "url": "https://mode.com/sql-tutorial/",
            "snippet": "Practical SQL tutorial with examples for analysis workflows.",
        },
    ],
    "Python": [
        {
            "title": "Python Tutorial",
            "url": "https://docs.python.org/3/tutorial/",
            "snippet": "Official Python tutorial for syntax, functions, classes, and modules.",
        },
        {
            "title": "Python Standard Library",
            "url": "https://docs.python.org/3/library/",
            "snippet": "Official reference for Python standard library modules.",
        },
    ],
    "LangGraph": [
        {
            "title": "LangGraph Docs",
            "url": "https://docs.langchain.com/oss/python/langgraph/overview",
            "snippet": "Official LangGraph overview for stateful agent and workflow graphs.",
        },
        {
            "title": "LangChain Docs",
            "url": "https://docs.langchain.com/",
            "snippet": "Official LangChain docs for LLM apps, tools, prompts, and structured output.",
        },
    ],
    "RAG": [
        {
            "title": "LangChain RAG Concepts",
            "url": "https://docs.langchain.com/oss/python/langchain/retrieval",
            "snippet": "LangChain retrieval concepts for building RAG applications.",
        },
        {
            "title": "Google Gemini API Docs",
            "url": "https://ai.google.dev/gemini-api/docs",
            "snippet": "Gemini API documentation for model usage and app development.",
        },
    ],
    "AWS Bedrock": [
        {
            "title": "Amazon Bedrock User Guide",
            "url": "https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html",
            "snippet": "Official AWS documentation introducing Amazon Bedrock and foundation model workflows.",
        },
        {
            "title": "Amazon Bedrock Developer Guide",
            "url": "https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html",
            "snippet": "AWS guide for getting started with Bedrock models and application development.",
        },
    ],
}


def _clean_api_key(value: str | None) -> str | None:
    if not value:
        return None
    stripped = value.strip()
    if not stripped or stripped in PLACEHOLDER_KEYS:
        return None
    return stripped


def is_tavily_mock_mode() -> bool:
    """Return True when Tavily is not configured."""
    return _clean_api_key(os.getenv("TAVILY_API_KEY")) is None


def choose_topic(role: str, selected_topic: str, weak_areas: list[str] | None) -> str:
    """Pick the next topic: user choice, weakest area, then role default."""
    selected_topic = (selected_topic or "").strip()
    if selected_topic:
        tool_call_logger("choose_topic", "selected_topic", selected_topic)
        return selected_topic

    if weak_areas:
        weakest = Counter(area for area in weak_areas if area).most_common(1)
        if weakest:
            tool_call_logger("choose_topic", "weak_area", weakest[0][0])
            return weakest[0][0]

    topics = ROLE_TOPICS.get(role, ROLE_TOPICS["AI Engineer"])
    starter_topics = {
        "AI Engineer": "AWS Bedrock",
        "Frontend Developer": "React",
        "Backend Developer": "REST APIs",
        "Data Analyst": "SQL",
    }
    topic = starter_topics.get(role, topics[0])
    tool_call_logger("choose_topic", f"role={role}", topic)
    return topic


def _topic_key(topic: str) -> str | None:
    normalized_topic = topic.lower().replace("-", " ").strip()
    for key in list(SUBTOPICS.keys()) + list(MCQ_BANKS.keys()):
        if key in normalized_topic or normalized_topic in key:
            return key
    if "join" in normalized_topic and "sql" in normalized_topic:
        return "sql joins"
    if "react" in normalized_topic and "hook" in normalized_topic:
        return "react hooks"
    if "api" in normalized_topic or "rest" in normalized_topic:
        return "rest apis"
    if "python" in normalized_topic or "decorator" in normalized_topic:
        return "python"
    return None


def choose_subtopic(topic: str, question_count: int, asked_questions: list[str]) -> str:
    """Rotate through subtopics so fixed topics still get fresh angles."""
    topic_key = _topic_key(topic)
    subtopics = SUBTOPICS.get(topic_key or "", GENERIC_SUBTOPICS)
    selected = subtopics[question_count % len(subtopics)]
    print("[question-generation] subtopic:", selected)
    return selected


def _normalize_question(text: str) -> str:
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\s+", " ", text).strip()


def is_duplicate_question(new_question: str, asked_questions: list[str]) -> bool:
    """Detect exact and simple near-duplicate questions."""
    normalized_new = _normalize_question(new_question)
    if not normalized_new:
        return False

    new_words = set(normalized_new.split())
    for old_question in asked_questions:
        normalized_old = _normalize_question(old_question)
        if normalized_new == normalized_old:
            return True

        old_words = set(normalized_old.split())
        if not old_words:
            continue
        shared_words = new_words & old_words
        overlap = len(shared_words) / max(len(new_words), 1)
        if overlap >= 0.75 and len(shared_words) >= 5:
            return True
    return False


def fallback_mcq_question(
    role: str,
    topic: str,
    difficulty: str,
    subtopic: str,
    asked_questions: list[str],
) -> QuestionOutput:
    """Return a topic-specific local MCQ, avoiding repeats when possible."""
    topic_key = _topic_key(topic)
    bank = MCQ_BANKS.get(topic_key or "")

    if bank:
        sorted_bank = sorted(
            bank,
            key=lambda item: 0 if item["subtopic"].lower() == subtopic.lower() else 1,
        )
        for item in sorted_bank:
            if not is_duplicate_question(item["question"], asked_questions):
                return QuestionOutput(
                    question=item["question"],
                    topic=topic,
                    difficulty=difficulty,
                    choices=item["choices"],
                    correct_answer=item["correct_answer"],
                    expected_points=item["expected_points"],
                )

    question = f"For {role}, which option best explains the {subtopic} angle of {topic}?"
    correct_answer = (
        f"Define {topic}, connect it to {subtopic}, and explain the practical impact."
    )
    choices = [
        correct_answer,
        f"Only name {topic} without connecting it to {subtopic}.",
        f"Treat {topic} as unrelated to {role} interviews.",
    ]
    return QuestionOutput(
        question=question,
        topic=topic,
        difficulty=difficulty,
        choices=choices,
        correct_answer=correct_answer,
        expected_points=[
            f"define {topic}",
            f"connect the answer to {subtopic}",
            "explain the practical impact",
        ],
    )


def local_grade_mcq(
    selected_answer: str,
    correct_answer: str,
    current_topic: str,
    expected_points: list[str],
    sources: list[dict[str, Any]],
) -> GradeOutput:
    """Grade MCQ answers locally so submit is fast."""
    source_models = [
        PrepSource(
            title=source.get("title", "Study source"),
            url=source.get("url", ""),
            snippet=source.get("snippet", ""),
        )
        for source in sources[:4]
    ]
    correct = selected_answer.strip().casefold() == correct_answer.strip().casefold()

    if correct:
        return GradeOutput(
            score=10,
            strength="You selected the correct answer.",
            improvement="Review the explanation to make sure you understand why.",
            feedback="Correct. This option best matches the key concept.",
            missing_points=[],
            weak_area="",
            correct_answer=correct_answer,
            sample_answer=(
                f"The correct answer is: {correct_answer} It matches the key idea because "
                f"{', '.join(expected_points[:3])}."
            ),
            study_next=[f"Review {current_topic} examples to reinforce the concept."],
            recommended_links=source_models,
        )

    return GradeOutput(
        score=4,
        strength="You made a selection and can use the explanation to improve.",
        improvement="Review why the correct answer is better.",
        feedback="Not quite. Review the correct option and the key idea behind it.",
        missing_points=expected_points[:3],
        weak_area=current_topic,
        correct_answer=correct_answer,
        sample_answer=(
            f"The correct answer is: {correct_answer} It is better because "
            f"{', '.join(expected_points[:3])}."
        ),
        study_next=[
            f"Review {current_topic} fundamentals.",
            "Compare the correct option against the distractors.",
        ],
        recommended_links=source_models,
    )


def _mock_sources_for_topic(role: str, topic: str) -> list[dict[str, str]]:
    topic_lower = topic.lower()
    for key, sources in MOCK_SOURCES.items():
        if key.lower() in topic_lower or topic_lower in key.lower():
            return sources[:4]

    if role == "Frontend Developer":
        return MOCK_SOURCES["React"]
    if role == "Data Analyst":
        return MOCK_SOURCES["SQL"]
    if role == "AI Engineer":
        return MOCK_SOURCES["LangGraph"]
    return MOCK_SOURCES["Python"]


def _source_quality_score(source: dict[str, str]) -> int:
    url = source.get("url", "")
    domain = urlparse(url).netloc.lower()
    preferred_domains = [
        "react.dev",
        "developer.mozilla.org",
        "docs.python.org",
        "postgresql.org",
        "docs.langchain.com",
        "ai.google.dev",
        "docs.aws.amazon.com",
    ]
    return 0 if any(domain.endswith(preferred) for preferred in preferred_domains) else 1


def _normalize_tavily_results(raw_results: Any) -> list[dict[str, str]]:
    if isinstance(raw_results, dict):
        results = raw_results.get("results", [])
    elif isinstance(raw_results, list):
        results = raw_results
    else:
        results = []

    sources: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for item in results:
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        sources.append(
            {
                "title": item.get("title") or "Study source",
                "url": url,
                "snippet": item.get("content") or item.get("snippet") or "",
            }
        )

    return sorted(sources, key=_source_quality_score)[:5]


def search_study_sources(role: str, topic: str) -> list[dict[str, str]]:
    """Use Tavily to find 3 to 5 study links, or return mock links."""
    started = time.perf_counter()
    tavily_key = _clean_api_key(os.getenv("TAVILY_API_KEY"))
    try:
        if not tavily_key:
            sources = _mock_sources_for_topic(role, topic)
            tool_call_logger("search_study_sources", "mock=true", f"{len(sources)} sources")
            return sources[:5]

        from langchain_tavily import TavilySearch

        query = (
            f"{topic} {role} interview study official docs MDN React Python "
            "LangChain LangGraph Gemini AWS Bedrock PostgreSQL"
        )
        search = TavilySearch(
            max_results=5,
            search_depth="basic",
            include_raw_content=False,
            include_answer=False,
        )
        raw_results = search.invoke({"query": query})
        sources = _normalize_tavily_results(raw_results)
        if sources:
            tool_call_logger("search_study_sources", "tavily=true", f"{len(sources)} sources")
            return sources[:5]
    except Exception as error:
        print("[tavily] failed, using mock sources:", error)
    finally:
        print(f"[timing] search_study_sources took {time.perf_counter() - started:.2f}s")

    sources = _mock_sources_for_topic(role, topic)[:5]
    tool_call_logger("search_study_sources", "fallback=true", f"{len(sources)} sources")
    return sources


def save_answer_to_json(session_id: str, answer_data: dict[str, Any]) -> None:
    """Save one graded answer to JSON."""
    started = time.perf_counter()
    try:
        save_answer(session_id, answer_data)
        tool_call_logger(
            "save_answer_to_json",
            f"session_id={session_id}, score={answer_data.get('score')}",
            answer_data.get("weak_area", ""),
        )
    finally:
        print(f"[timing] save_answer_to_json took {time.perf_counter() - started:.2f}s")


def calculate_average_score(scores: list[int]) -> float:
    """Return the rounded average score."""
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 1)


def get_weak_areas(state: dict[str, Any]) -> list[str]:
    """Return repeated weak areas ordered by frequency."""
    areas = [area for area in state.get("weak_areas", []) if area]
    return [area for area, _ in Counter(areas).most_common()]


def save_session_to_json(session_data: dict[str, Any]) -> None:
    """Save final session data locally."""
    started = time.perf_counter()
    try:
        storage_save_session_to_json(session_data)
        tool_call_logger("save_session_to_json", session_data.get("session_id", ""), "saved")
    finally:
        print(f"[timing] save_session_to_json took {time.perf_counter() - started:.2f}s")
