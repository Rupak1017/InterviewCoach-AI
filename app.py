"""Streamlit UI for InterviewCoach AI Guided Practice Mode."""

from __future__ import annotations

from collections import Counter
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from chains import is_mock_mode
from graph import InterviewState, generate_next_question, grade_current_answer
from onboarding import (
    can_use_onboarding_target,
    current_tour_target,
    initialize_onboarding_state,
    mark_onboarding_seen,
    open_onboarding_tour,
    render_onboarding_persistence_bridge,
    render_tour_controls,
    render_tour_note,
)
from storage import create_session, ensure_data_file, list_sessions
from styles import apply_styles
from tools import calculate_average_score, is_tavily_mock_mode, search_study_sources


ROLES = [
    "Frontend Developer",
    "Backend Developer",
    "Data Analyst",
    "AI Engineer",
]
DIFFICULTIES = ["Easy", "Medium", "Hard"]
QUESTION_OPTIONS = [3, 5, 10]
APP_DESCRIPTION = (
    "AI interview practice app that provides topic notes, MCQ questions, "
    "mistake explanations, weak-topic study links, and a final performance report."
)
TOPIC_PLACEHOLDER = (
    "Type a topic, e.g. AWS Bedrock, LangChain, React Hooks, RAG..."
)


def initialize_session_state() -> None:
    defaults = {
        "interview_state": None,
        "messages": [],
        "active": False,
        "last_error": "",
        "pending_practice": None,
        "start_button_clicked": False,
        "show_onboarding": False,
        "onboarding_step": 0,
        "manual_onboarding_requested": False,
        "tour_seen_this_browser": False,
        "tour_state_initialized": False,
        "is_processing": False,
        "last_processed_answer_id": "",
        "source_cache": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_page_metadata() -> None:
    """Set browser metadata for richer link previews where supported."""
    components.html(
        f"""
<script>
(function () {{
    const title = "InterviewCoach AI";
    const description = "{APP_DESCRIPTION}";
    const head = window.parent.document.head;

    window.parent.document.title = title;

    const entries = [
        ["name", "description", description],
        ["property", "og:title", title],
        ["property", "og:description", description],
        ["property", "twitter:title", title],
        ["property", "twitter:description", description]
    ];

    entries.forEach(([attr, key, content]) => {{
        let tag = head.querySelector(`meta[${{attr}}="${{key}}"]`);
        if (!tag) {{
            tag = window.parent.document.createElement("meta");
            tag.setAttribute(attr, key);
            head.appendChild(tag);
        }}
        tag.setAttribute("content", content);
    }});
}})();
</script>
        """,
        height=0,
    )


def render_scroll_to_startup_status() -> None:
    """Move mobile users to the loading/status area after they start practice."""
    components.html(
        """
<script>
(function () {
    const targetId = "practice-start-status";

    function scrollNow() {
        try {
            const parentWindow = window.parent || window;
            const doc = parentWindow.document;
            const target = doc.getElementById(targetId);

            if (target && target.scrollIntoView) {
                target.scrollIntoView({ behavior: "smooth", block: "start" });
                return;
            }

            parentWindow.scrollTo({ top: 0, left: 0, behavior: "smooth" });
            const scrollTargets = [
                doc.scrollingElement,
                doc.documentElement,
                doc.body,
                doc.querySelector('[data-testid="stAppViewContainer"]'),
                doc.querySelector('[data-testid="stMain"]'),
                doc.querySelector("section.stMain")
            ].filter(Boolean);

            scrollTargets.forEach(function (element) {
                try {
                    element.scrollTo({ top: 0, left: 0, behavior: "smooth" });
                } catch (error) {
                    element.scrollTop = 0;
                }
            });
        } catch (error) {
            // The app should never fail just because the scroll helper cannot run.
        }
    }

    scrollNow();
    setTimeout(scrollNow, 80);
    setTimeout(scrollNow, 240);
    setTimeout(scrollNow, 500);
})();
</script>
        """,
        height=0,
    )


def new_interview_state(
    role: str,
    selected_topic: str,
    difficulty: str,
    max_questions: int,
) -> InterviewState:
    session_id = create_session(role, selected_topic, difficulty, max_questions)
    return {
        "session_id": session_id,
        "role": role,
        "selected_topic": selected_topic,
        "difficulty": difficulty,
        "max_questions": max_questions,
        "question_count": 0,
        "current_topic": "",
        "current_subtopic": "",
        "quick_prep": {},
        "study_sources": [],
        "source_cache": st.session_state.get("source_cache", {}),
        "current_question": "",
        "choices": [],
        "correct_answer": "",
        "expected_points": [],
        "user_answer": "",
        "scores": [],
        "weak_areas": [],
        "strong_areas": [],
        "feedback_history": [],
        "asked_questions": [],
        "final_report": {},
        "stage": "new",
        "last_grade": {},
        "validation_message": "",
    }


def reset_active_interview() -> None:
    st.session_state.interview_state = None
    st.session_state.messages = []
    st.session_state.active = False
    st.session_state.last_error = ""
    st.session_state.pending_practice = None
    st.session_state.start_button_clicked = False
    st.session_state.is_processing = False
    st.session_state.last_processed_answer_id = ""


def _source_cache_key(role: str, topic: str) -> str:
    return f"{role.lower()}::{topic.lower()}"


def get_cached_study_sources(role: str, topic: str) -> list[dict[str, Any]]:
    """Return cached sources or fetch them once per role/topic."""
    cache = st.session_state.setdefault("source_cache", {})
    key = _source_cache_key(role, topic)
    if key in cache and cache[key]:
        print("[source-cache] streamlit hit:", key)
        return cache[key]

    print("[source-cache] streamlit miss:", key)
    sources = search_study_sources(role, topic)
    cache[key] = sources
    return sources


def question_message(state: InterviewState) -> str:
    question_number = state.get("question_count", 0) + 1
    max_questions = state.get("max_questions", 5)
    role = state.get("role", "Interview")
    topic = state.get("current_topic", "Current topic")
    question = state.get("current_question", "")
    return (
        f"**Question {question_number} of {max_questions} - {role}**\n\n"
        f"**Topic:** {topic}\n\n"
        f"{question}"
    )


def start_guided_practice(role: str, selected_topic: str, difficulty: str, max_questions: int) -> None:
    try:
        state = new_interview_state(role, selected_topic.strip(), difficulty, max_questions)
        state["study_sources"] = get_cached_study_sources(role, selected_topic.strip())
        state["source_cache"] = st.session_state.get("source_cache", {})
        state = generate_next_question(state)
        st.session_state.source_cache = state.get("source_cache", st.session_state.source_cache)
        st.session_state.interview_state = state
        st.session_state.messages = [
            {"role": "assistant", "kind": "question", "content": question_message(state)}
        ]
        st.session_state.active = True
        st.session_state.start_button_clicked = False
        st.session_state.is_processing = False
        st.session_state.last_processed_answer_id = ""
        st.session_state.last_error = ""
    except Exception as error:
        st.session_state.last_error = str(error)
        st.session_state.start_button_clicked = False


def render_startup_status(config: dict[str, Any]) -> None:
    """Show visible progress while the first question is prepared."""
    st.markdown('<span id="practice-start-status"></span>', unsafe_allow_html=True)
    render_scroll_to_startup_status()

    with st.container(border=True):
        st.markdown("### Starting Guided Practice")
        st.caption("The coach is setting up your first focused practice question.")

        with st.status("Agent is preparing your session...", expanded=True) as status:
            st.write("Reading role, topic, difficulty, and question count.")
            st.write("Fetching study links with Tavily or mock sources.")
            st.write("Building the Quick Prep card.")
            st.write("Generating the first interview question.")

            start_guided_practice(
                config["role"],
                config["selected_topic"],
                config["difficulty"],
                config["max_questions"],
            )

            if st.session_state.last_error:
                status.update(label="Could not start practice.", state="error")
            else:
                status.update(label="Guided Practice is ready.", state="complete")
                st.session_state.pending_practice = None
                st.rerun()


def render_header() -> None:
    st.markdown(
        """
<div class="app-header">
    <div class="main-title">InterviewCoach AI</div>
    <div class="subtitle">Guided Practice Mode for interview prep, answers, feedback, and study links.</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def queue_guided_practice(
    role: str,
    selected_topic: str,
    difficulty: str,
    max_questions: int,
) -> None:
    mark_onboarding_seen()
    st.session_state.pending_practice = {
        "role": role,
        "selected_topic": selected_topic.strip(),
        "difficulty": difficulty,
        "max_questions": max_questions,
    }
    st.session_state.active = False
    st.session_state.messages = []
    st.session_state.interview_state = None
    st.session_state.last_error = ""
    st.session_state.is_processing = False
    st.session_state.start_button_clicked = True


def render_home_setup() -> None:
    tour_active = st.session_state.get("show_onboarding", False)
    st.markdown('<div class="setup-shell">', unsafe_allow_html=True)
    setup_col, info_col = st.columns([1.75, 1], gap="large")

    with setup_col:
        with st.container(border=True):
            render_tour_note("main", "Use this setup panel to start a focused MCQ practice session.")
            st.markdown("### Set up Guided Practice")
            st.caption("Pick a role, choose a topic, set the level, and start.")

            with st.container(border=current_tour_target() == "role"):
                render_tour_note("role", "Choose the role that matches the interview you want to practice. Then press OK to unlock the next step.")
                role = st.radio(
                    "Pick a role",
                    ROLES,
                    index=3,
                    horizontal=True,
                    label_visibility="visible",
                    disabled=not can_use_onboarding_target("role"),
                )
                render_tour_controls("role")

            with st.container(border=current_tour_target() == "topic"):
                render_tour_note("topic", "Make the session specific by typing one topic. Then press OK to continue.")
                selected_topic = st.text_input(
                    "Pick any topic",
                    placeholder=TOPIC_PLACEHOLDER,
                    key="setup_topic_input",
                    disabled=not can_use_onboarding_target("topic"),
                )
                render_tour_controls(
                    "topic",
                    validate_on_continue=lambda: bool(
                        st.session_state.get("setup_topic_input", "").strip()
                    ),
                    validation_message="Type a topic to continue.",
                )

            col1, col2 = st.columns(2)
            with col1:
                with st.container(border=current_tour_target() == "difficulty"):
                    render_tour_note("difficulty", "Choose how challenging the MCQs should be. Then press OK.")
                    difficulty = st.radio(
                        "Level",
                        DIFFICULTIES,
                        horizontal=True,
                        disabled=not can_use_onboarding_target("difficulty"),
                    )
                    render_tour_controls("difficulty")

            with col2:
                with st.container(border=current_tour_target() == "questions"):
                    render_tour_note("questions", "Choose a quick 3-question run or a longer practice session. Then press OK.")
                    max_questions = st.radio(
                        "Questions",
                        QUESTION_OPTIONS,
                        index=1,
                        horizontal=True,
                        disabled=not can_use_onboarding_target("questions"),
                    )
                    render_tour_controls("questions")

            with st.container(border=current_tour_target() == "start"):
                render_tour_note("start", "Click Start Guided Practice. The coach will take you into the first question.")
                start_label = (
                    "Preparing practice..."
                    if st.session_state.get("start_button_clicked", False)
                    else "Start Guided Practice"
                )
                if st.button(
                    start_label,
                    use_container_width=True,
                    disabled=(
                        st.session_state.get("start_button_clicked", False)
                        or not can_use_onboarding_target("start")
                    ),
                    type="primary",
                ):
                    if not selected_topic.strip():
                        st.warning("Please enter a topic before starting.")
                    else:
                        queue_guided_practice(role, selected_topic, difficulty, max_questions)
                        st.rerun()

                if st.session_state.get("start_button_clicked", False):
                    st.markdown(
                        """
<div class="loading-inline">
    <span class="loading-spinner"></span>
    <span>Preparing your first question...</span>
</div>
                        """,
                        unsafe_allow_html=True,
                    )

    with info_col:
        with st.container(border=True):
            st.markdown("### What you will get")
            st.markdown("- Quick prep before each question")
            st.markdown("- Three MCQ choices per question")
            st.markdown("- Instant scoring and feedback")
            st.markdown("- Useful links and a final report")

        show_saved_sessions = st.checkbox("Show saved sessions", disabled=tour_active)
        if show_saved_sessions:
            render_saved_sessions()

        with st.container(border=True):
            st.markdown("**App mode**")
            st.caption("Bedrock mode" if not is_mock_mode() else "Mock Gemini mode")
            if is_tavily_mock_mode():
                st.caption("Mock study links")
            if st.button("Show onboarding tour", use_container_width=True, disabled=tour_active):
                open_onboarding_tour()

    st.markdown('</div>', unsafe_allow_html=True)


def render_source_links(sources: list[dict[str, Any]], limit: int = 4) -> None:
    for source in sources[:limit]:
        title = source.get("title", "Study source")
        url = source.get("url", "")
        snippet = source.get("snippet", "")
        if url:
            st.markdown(f"- [{title}]({url})")
            st.caption(url)
        else:
            st.markdown(f"- {title}")
        if snippet:
            st.caption(snippet[:220])


def short_text(text: str, max_sentences: int = 2) -> str:
    """Keep prep cards compact for small screens."""
    pieces = [piece.strip() for piece in text.replace("\n", " ").split(".") if piece.strip()]
    if not pieces:
        return text
    return ". ".join(pieces[:max_sentences]) + "."


def render_quick_prep(state: InterviewState) -> None:
    if state.get("stage") == "complete":
        return

    prep = state.get("quick_prep", {})
    if not prep:
        return

    with st.container(border=True):
        st.markdown(f"### Quick Prep: {state.get('current_topic', 'Current topic')}")
        st.write(short_text(prep.get("overview", "")))

        key_points = prep.get("key_points", [])[:2]
        if key_points:
            st.markdown("**Key points**")
            for point in key_points:
                st.markdown(f"- {point}")

        mistake = prep.get("common_mistake", "")
        if mistake:
            st.markdown(f"**Common mistake:** {mistake}")

        with st.expander("Useful links for interview", expanded=False):
            render_source_links(prep.get("sources", []), limit=4)


def render_feedback_message(grade: dict[str, Any]) -> None:
    missing_points = grade.get("missing_points", [])
    study_next = grade.get("study_next", [])
    links = grade.get("recommended_links", [])

    st.markdown(
        f"""
<div class="feedback-card">
<h3>Score: {grade.get("score", 0)}/10</h3>
<p><strong>Strength:</strong> {grade.get("strength", "")}</p>
<p><strong>Improvement:</strong> {grade.get("improvement", "")}</p>
<p><strong>Feedback:</strong> {grade.get("feedback", "")}</p>
<p><strong>Correct answer:</strong> {grade.get("correct_answer", "")}</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    if missing_points:
        with st.expander("Missing points", expanded=False):
            for point in missing_points:
                st.markdown(f"- {point}")

    if study_next:
        with st.expander("Study next", expanded=True):
            for item in study_next[:4]:
                st.markdown(f"- {item}")

    with st.expander("Sample answer", expanded=False):
        st.write(grade.get("sample_answer", ""))

    if links:
        with st.expander("Useful links for interview", expanded=False):
            render_source_links(links, limit=4)


def render_chat_messages() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message.get("kind") == "feedback":
                render_feedback_message(message.get("grade", {}))
            else:
                st.markdown(message.get("content", ""), unsafe_allow_html=True)


def handle_answer_submission(state: InterviewState) -> None:
    if state.get("stage") != "waiting_for_answer":
        return

    choices = state.get("choices", [])
    if len(choices) != 3:
        st.warning("The answer choices were not generated correctly. Please reset and try again.")
        return

    answer_key = (
        f"answer_{state.get('session_id')}_{state.get('question_count')}_"
        f"{len(state.get('asked_questions', []))}"
    )
    choice_labels = [f"{chr(65 + index)}. {choice}" for index, choice in enumerate(choices)]
    st.markdown("### Choose the best answer")
    selected_label = st.radio(
        "Answer choices",
        choice_labels,
        index=None,
        key=answer_key,
        label_visibility="collapsed",
    )
    answer = None
    if selected_label:
        answer = choices[choice_labels.index(selected_label)]

    if not st.button(
        "Submit Answer",
        use_container_width=True,
        disabled=st.session_state.get("is_processing", False),
    ):
        return

    if not answer:
        st.warning("Please select an answer before I grade it.")
        return

    if st.session_state.get("is_processing", False):
        return

    answer_id = f"{state.get('current_question', '')}::{answer}::{state.get('question_count', 0)}"
    if answer_id == st.session_state.get("last_processed_answer_id", ""):
        return

    st.session_state.is_processing = True
    st.session_state.last_processed_answer_id = answer_id

    try:
        st.session_state.messages.append({"role": "user", "kind": "answer", "content": f"Selected: {answer}"})
        state["user_answer"] = answer
        state["source_cache"] = st.session_state.get("source_cache", {})
        updated_state = grade_current_answer(state)
        st.session_state.source_cache = updated_state.get("source_cache", st.session_state.source_cache)
    except Exception as error:
        st.error("Something went wrong while grading. Please try again.")
        st.session_state.last_error = str(error)
        st.session_state.last_processed_answer_id = ""
        st.session_state.is_processing = False
        return

    validation_from_graph = updated_state.get("validation_message")
    if validation_from_graph:
        st.warning(validation_from_graph)
        st.session_state.is_processing = False
        return

    grade = updated_state.get("last_grade", {})
    if grade:
        st.session_state.messages.append(
            {"role": "assistant", "kind": "feedback", "grade": grade}
        )

    if updated_state.get("stage") == "complete":
        st.session_state.messages.append(
            {
                "role": "assistant",
                "kind": "complete",
                "content": "Guided Practice complete. Your final report is ready below.",
            }
        )
    else:
        st.session_state.messages.append(
            {"role": "assistant", "kind": "question", "content": question_message(updated_state)}
        )

    st.session_state.interview_state = updated_state
    st.session_state.is_processing = False
    st.rerun()


def readiness_box(readiness: str) -> None:
    readiness_lower = readiness.lower()
    if "strong" in readiness_lower or "prepared" in readiness_lower:
        st.success(readiness)
    elif "medium" in readiness_lower:
        st.info(readiness)
    else:
        st.warning(readiness)


def render_final_report(state: InterviewState) -> None:
    report = state.get("final_report", {})
    if not report:
        return

    st.markdown("## Final Report")
    col1, col2 = st.columns(2)
    col1.metric("Average Score", f"{report.get('average_score', 0)}/10")
    col2.metric("Questions Answered", len(state.get("scores", [])))

    st.markdown("### Readiness Verdict")
    readiness_box(report.get("readiness_level", "Needs practice"))

    with st.expander("Strong areas", expanded=True):
        for item in report.get("strong_areas", []):
            st.markdown(f"- {item}")

    with st.expander("Weak areas", expanded=True):
        for item in report.get("weak_areas", []):
            st.markdown(f"- {item}")

    with st.expander("Recommended topics", expanded=True):
        for item in report.get("recommended_topics", []):
            st.markdown(f"- {item}")

    with st.expander("Useful sources", expanded=False):
        render_source_links(report.get("useful_sources", []), limit=5)

    with st.expander("Practice tasks", expanded=True):
        for item in report.get("practice_tasks", []):
            st.markdown(f"- {item}")

    st.info(report.get("final_message", "Keep practicing."))

    if st.button("Start New Guided Practice", use_container_width=True):
        reset_active_interview()
        st.rerun()


def render_side_panel(state: InterviewState) -> None:
    scores = state.get("scores", [])
    weak_areas = state.get("weak_areas", [])
    answered = state.get("question_count", 0)
    total = state.get("max_questions", 5)

    st.markdown("### Practice Snapshot")
    st.metric("Average Score", f"{calculate_average_score(scores)}/10" if scores else "-")
    st.metric("Answered", f"{answered}/{total}")
    st.progress(min(answered / total, 1.0) if total else 0.0)

    if weak_areas:
        st.markdown("**Weak areas**")
        for area, count in Counter(weak_areas).most_common(4):
            st.markdown(f'<span class="pill">{area} ({count})</span>', unsafe_allow_html=True)
    else:
        st.caption("Weak areas will appear after graded answers.")


def render_saved_sessions() -> None:
    sessions = list_sessions()
    st.markdown("## Saved Sessions")
    if not sessions:
        st.info("No saved sessions yet.")
        return

    for session in sessions[:8]:
        scores = [int(score) for score in session.get("scores", [])]
        average = calculate_average_score(scores)
        label = (
            f"{session.get('role')} - {session.get('selected_topic') or 'Topic'} - "
            f"{session.get('created_at')}"
        )
        with st.expander(label):
            st.write(f"Difficulty: {session.get('difficulty')}")
            st.write(f"Answers: {len(session.get('answers', []))}")
            st.write(f"Average score: {average}/10" if scores else "Average score: -")


def main() -> None:
    st.set_page_config(
        page_title="InterviewCoach AI",
        page_icon="IC",
        layout="wide",
    )
    ensure_data_file()
    initialize_session_state()
    initialize_onboarding_state()
    apply_styles()
    render_page_metadata()
    render_onboarding_persistence_bridge()

    render_header()

    if is_mock_mode():
        st.warning("Running in mock mode because no Gemini API key was found.")
    if is_tavily_mock_mode():
        st.caption("Using mock study links because TAVILY_API_KEY was not found.")
    if st.session_state.last_error:
        st.error("A friendly heads-up: something failed. Check the terminal for details and try again.")

    if st.session_state.pending_practice:
        render_startup_status(st.session_state.pending_practice)
        return

    state = st.session_state.get("interview_state")
    if not st.session_state.active or not state:
        render_home_setup()
    else:
        main_col, side_col = st.columns([2, 1], gap="large")
        with main_col:
            with st.container(border=current_tour_target() == "main"):
                render_tour_note("main", "This is the workspace for prep, questions, answers, feedback, links, and reports.")
                render_quick_prep(state)
                render_chat_messages()
                if state.get("stage") == "complete":
                    render_final_report(state)
                else:
                    handle_answer_submission(state)
        with side_col:
            render_side_panel(state)


if __name__ == "__main__":
    main()
