"""Streamlit UI for InterviewCoach AI Guided Practice Mode."""

from __future__ import annotations

from collections import Counter
from typing import Any

import streamlit as st

from chains import is_mock_mode
from graph import InterviewState, generate_next_question, grade_current_answer
from storage import create_session, ensure_data_file, list_sessions
from tools import calculate_average_score, is_tavily_mock_mode, search_study_sources


ROLES = [
    "Frontend Developer",
    "Backend Developer",
    "Data Analyst",
    "AI Engineer",
]
DIFFICULTIES = ["Easy", "Medium", "Hard"]
QUESTION_OPTIONS = [3, 5, 10]
TOPIC_PLACEHOLDER = (
    "AWS Bedrock, LangChain, React Hooks, LangGraph state, RAG, "
    "JavaScript closures, SQL joins..."
)
TOUR_STEPS = [
    {
        "target": "role",
        "title": "Step 1: Choose a role",
        "body": "Pick the interview track you want to practice. The coach adapts examples and expectations to this role.",
    },
    {
        "target": "topic",
        "title": "Step 2: Enter a topic",
        "body": "Choose a focused topic like AWS Bedrock, LangChain, React Hooks, LangGraph state, RAG, or SQL joins.",
    },
    {
        "target": "difficulty",
        "title": "Step 3: Pick difficulty",
        "body": "Easy checks fundamentals, Medium adds practical scenarios, and Hard asks for tradeoffs or deeper reasoning.",
    },
    {
        "target": "questions",
        "title": "Step 4: Choose question count",
        "body": "Start small with 3 questions, or choose 5 or 10 for a longer practice session.",
    },
    {
        "target": "start",
        "title": "Step 5: Start practice",
        "body": "When you click Start, the agent fetches study links, prepares a quick prep card, and generates the first question.",
    },
    {
        "target": "main",
        "title": "Step 6: Practice in the main area",
        "body": "This is where quick prep, questions, your answers, feedback, useful links, and the final report appear.",
    },
]


def apply_styles() -> None:
    st.markdown(
        """
<style>
.main-title {
    font-size: 2.35rem;
    font-weight: 800;
    margin-bottom: 0rem;
}
.subtitle {
    font-size: 1.05rem;
    color: #666;
    margin-bottom: 1.2rem;
}
.info-card, .feedback-card {
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid #e6e6e6;
    background: #fafafa;
    margin-bottom: 1rem;
}
.feedback-card {
    background: #ffffff;
}
.small-muted {
    color: #777;
    font-size: 0.9rem;
}
.pill {
    display: inline-block;
    padding: 0.25rem 0.55rem;
    border-radius: 999px;
    border: 1px solid #e2e8f0;
    background: #f8fafc;
    margin: 0.15rem 0.2rem 0.15rem 0;
    font-size: 0.88rem;
}
.tour-note {
    padding: 0.65rem;
    border-radius: 8px;
    border: 1px solid #f59e0b;
    background: #fffbeb;
    color: #7c2d12;
    margin: 0.35rem 0 0.75rem 0;
    font-size: 0.92rem;
}
[data-testid="stDialogOverlay"] {
    backdrop-filter: blur(2px);
    background: rgba(15, 23, 42, 0.28);
}
div[role="dialog"] {
    border-radius: 12px;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def initialize_session_state() -> None:
    defaults = {
        "interview_state": None,
        "messages": [],
        "active": False,
        "last_error": "",
        "pending_practice": None,
        "show_onboarding": True,
        "onboarding_step": 0,
        "is_processing": False,
        "last_processed_answer_id": "",
        "source_cache": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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


def current_tour_target() -> str | None:
    if not st.session_state.get("show_onboarding", False):
        return None

    step = min(st.session_state.get("onboarding_step", 0), len(TOUR_STEPS) - 1)
    return TOUR_STEPS[step]["target"]


def render_tour_note(target: str, text: str) -> None:
    if current_tour_target() == target:
        st.markdown(f'<div class="tour-note">{text}</div>', unsafe_allow_html=True)


@st.dialog("Guided onboarding tour")
def render_onboarding_tour() -> None:
    step_index = min(st.session_state.get("onboarding_step", 0), len(TOUR_STEPS) - 1)
    step = TOUR_STEPS[step_index]

    st.caption(f"{step_index + 1} of {len(TOUR_STEPS)}")
    st.progress((step_index + 1) / len(TOUR_STEPS))
    st.markdown(f"### {step['title']}")
    st.write(step["body"])
    st.caption("The current section is highlighted behind this tour card. The rest of the app is dimmed while you walk through the steps.")

    back_col, next_col, skip_col = st.columns([1, 1, 1])
    with back_col:
        if st.button("Back", disabled=step_index == 0, use_container_width=True):
            st.session_state.onboarding_step = max(0, step_index - 1)
            st.rerun()

    with next_col:
        is_last = step_index == len(TOUR_STEPS) - 1
        if st.button("Finish" if is_last else "Next", use_container_width=True):
            if is_last:
                st.session_state.show_onboarding = False
                st.session_state.onboarding_step = 0
            else:
                st.session_state.onboarding_step = step_index + 1
            st.rerun()

    with skip_col:
        if st.button("Skip", use_container_width=True):
            st.session_state.show_onboarding = False
            st.session_state.onboarding_step = 0
            st.rerun()


def question_message(state: InterviewState) -> str:
    question_number = state.get("question_count", 0) + 1
    max_questions = state.get("max_questions", 5)
    role = state.get("role", "Interview")
    topic = state.get("current_topic", "Current topic")
    question = state.get("current_question", "")
    choices = state.get("choices", [])
    choice_text = "\n".join(f"{index}. {choice}" for index, choice in enumerate(choices, start=1))
    return (
        f"**Question {question_number} of {max_questions} - {role}**\n\n"
        f"**Topic:** {topic}\n\n"
        f"{question}\n\n"
        f"{choice_text}"
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
        st.session_state.is_processing = False
        st.session_state.last_processed_answer_id = ""
        st.session_state.last_error = ""
    except Exception as error:
        st.session_state.last_error = str(error)


def render_startup_status(config: dict[str, Any]) -> None:
    """Show visible progress while the first question is prepared."""
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
    st.markdown('<div class="main-title">InterviewCoach AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Guided Practice Mode for interview prep, answers, feedback, and study links.</div>',
        unsafe_allow_html=True,
    )


def render_sidebar() -> bool:
    with st.sidebar:
        st.header("Focus Tour")
        st.caption("Follow these steps from top to bottom.")

        with st.container(border=current_tour_target() == "role"):
            st.markdown("**1. Select a role**")
            render_tour_note("role", "Start here. Choose the role that matches the interview you want to practice.")
            role = st.radio("Role", ROLES, index=3)

        with st.container(border=current_tour_target() == "topic"):
            st.markdown("**2. Enter a topic**")
            render_tour_note("topic", "Make the session specific. Good examples: AWS Bedrock, LangChain, React Hooks, LangGraph state.")
            selected_topic = st.text_input(
                "Topic",
                placeholder=TOPIC_PLACEHOLDER,
            )

        with st.container(border=current_tour_target() == "difficulty"):
            st.markdown("**3. Pick difficulty**")
            render_tour_note("difficulty", "Choose the level of challenge before the agent prepares the question.")
            difficulty = st.radio("Difficulty", DIFFICULTIES, horizontal=True)

        with st.container(border=current_tour_target() == "questions"):
            st.markdown("**4. Choose question count**")
            render_tour_note("questions", "Choose a quick 3-question run or a longer practice session.")
            max_questions = st.radio("Questions", QUESTION_OPTIONS, index=1, horizontal=True)

        st.divider()
        with st.container(border=current_tour_target() == "start"):
            render_tour_note("start", "Click Start when the setup is ready. You can skip or finish the tour first if you want.")
            if st.button("Start Guided Practice", use_container_width=True):
                if not selected_topic.strip():
                    st.warning("Please enter a topic before starting.")
                else:
                    st.session_state.show_onboarding = False
                    st.session_state.onboarding_step = 0
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
            if st.button("Reset Practice", use_container_width=True):
                reset_active_interview()

        st.divider()
        st.header("Progress")
        state = st.session_state.get("interview_state") or {}
        answered = state.get("question_count", 0)
        total = state.get("max_questions", max_questions)
        progress = min(answered / total, 1.0) if total else 0.0
        st.progress(progress)
        st.caption(f"{answered} of {total} questions answered" if st.session_state.active else "No active practice")

        scores = state.get("scores", [])
        st.metric("Average Score", f"{calculate_average_score(scores)}/10" if scores else "-")
        st.metric("Questions Answered", answered)

        st.divider()
        st.header("Info")
        st.caption("Gemini mode" if not is_mock_mode() else "Mock Gemini mode")
        if is_tavily_mock_mode():
            st.caption("Using mock study links because TAVILY_API_KEY was not found.")
        if st.button("Show onboarding tour", use_container_width=True):
            st.session_state.show_onboarding = True
            st.session_state.onboarding_step = 0
        show_saved_sessions = st.checkbox("Show saved sessions")

    return show_saved_sessions


def render_welcome() -> None:
    with st.container(border=current_tour_target() == "main"):
        render_tour_note("main", "After setup, this main area becomes your practice workspace.")
        st.markdown(
            """
<div class="info-card">
<strong>Focus Tour</strong><br>
The sidebar is open. Select a role, enter a topic, choose difficulty, choose question count, then start Guided Practice.
</div>
        """,
            unsafe_allow_html=True,
        )
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("**1. Role**  \nPick the interview track.")
        with col2:
            st.markdown("**2. Topic**  \nTry AWS Bedrock, LangChain, React Hooks, or LangGraph.")
        with col3:
            st.markdown("**3. Level**  \nChoose Easy, Medium, or Hard.")
        with col4:
            st.markdown("**4. Start**  \nPick 3, 5, or 10 questions.")
        st.info("Use the sidebar tour to start your first session.")


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


def render_quick_prep(state: InterviewState) -> None:
    if state.get("stage") == "complete":
        return

    prep = state.get("quick_prep", {})
    if not prep:
        return

    with st.container(border=True):
        st.markdown(f"### Quick Prep: {state.get('current_topic', 'Current topic')}")
        st.write(prep.get("overview", ""))

        key_points = prep.get("key_points", [])[:2]
        if key_points:
            st.markdown("**Key points**")
            for point in key_points:
                st.markdown(f"- {point}")

        mistake = prep.get("common_mistake", "")
        if mistake:
            st.markdown(f"**Common mistake:** {mistake}")

        with st.expander("Useful links", expanded=False):
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
        with st.expander("Useful links", expanded=False):
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
    answer = st.radio(
        "Choose one answer",
        choices,
        index=None,
        key=answer_key,
    )

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
        initial_sidebar_state="expanded",
    )
    ensure_data_file()
    initialize_session_state()
    apply_styles()

    render_header()
    show_saved_sessions = render_sidebar()

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
        render_welcome()
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

    if show_saved_sessions:
        render_saved_sessions()

    if st.session_state.get("show_onboarding", False):
        render_onboarding_tour()


if __name__ == "__main__":
    main()
