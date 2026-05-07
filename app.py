"""Streamlit UI for InterviewCoach AI."""

from __future__ import annotations

from collections import Counter
from typing import Any

import streamlit as st

from chains import is_mock_mode
from graph import InterviewState, generate_next_question, grade_current_answer
from storage import create_session, ensure_data_file, list_sessions
from tools import calculate_average_score


ROLES = [
    "Frontend Developer",
    "Backend Developer",
    "Data Analyst",
    "AI Engineer",
]
DIFFICULTIES = ["Easy", "Medium", "Hard"]
QUESTION_OPTIONS = [3, 5, 10]


def apply_styles() -> None:
    st.markdown(
        """
<style>
.main-title {
    font-size: 2.5rem;
    font-weight: 800;
    margin-bottom: 0rem;
}
.subtitle {
    font-size: 1.1rem;
    color: #666;
    margin-bottom: 1.5rem;
}
.info-card, .feedback-card, .side-card {
    padding: 1.1rem;
    border-radius: 8px;
    border: 1px solid #e6e6e6;
    background: #fafafa;
    margin-bottom: 1rem;
}
.feedback-card {
    background: #ffffff;
    border-color: #dddddd;
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
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def new_interview_state(role: str, difficulty: str, max_questions: int) -> InterviewState:
    session_id = create_session(role, difficulty, max_questions)
    return {
        "session_id": session_id,
        "role": role,
        "difficulty": difficulty,
        "max_questions": max_questions,
        "question_count": 0,
        "current_question": "",
        "current_topic": "",
        "choices": [],
        "correct_answer": "",
        "expected_points": [],
        "user_answer": "",
        "scores": [],
        "feedback_history": [],
        "weak_areas": [],
        "strong_areas": [],
        "asked_questions": [],
        "next_topic": "",
        "final_report": {},
        "stage": "new",
        "last_grade": {},
        "validation_message": "",
    }


def question_message(state: InterviewState) -> str:
    question_number = state.get("question_count", 0) + 1
    max_questions = state.get("max_questions", 5)
    role = state.get("role", "Interview")
    question = state.get("current_question", "")
    choices = state.get("choices", [])
    choice_text = "\n".join(f"{index}. {choice}" for index, choice in enumerate(choices, start=1))
    return (
        f"**Question {question_number} of {max_questions} - {role}**\n\n"
        f"{question}\n\n"
        f"{choice_text}\n\n"
        "Choose one option below."
    )


def grade_message(grade: dict[str, Any]) -> str:
    missing_points = grade.get("missing_points", [])
    missing_text = ", ".join(missing_points) if missing_points else "No major missing points."
    return f"""
<div class="feedback-card">
<h3>Score: {grade.get("score", 0)}/10</h3>
<p><strong>Strength:</strong> {grade.get("strength", "")}</p>
<p><strong>Improve:</strong> {grade.get("improvement", "")}</p>
<p><strong>Missing points:</strong> {missing_text}</p>
<p><strong>Correct answer:</strong> {grade.get("correct_answer", "")}</p>
<p><strong>Explanation:</strong> {grade.get("sample_answer", "")}</p>
</div>
"""


def reset_active_interview() -> None:
    st.session_state.interview_state = None
    st.session_state.messages = []
    st.session_state.active = False
    st.session_state.last_error = ""


def start_interview(role: str, difficulty: str, max_questions: int) -> None:
    try:
        state = new_interview_state(role, difficulty, max_questions)
        state = generate_next_question(state)
        st.session_state.interview_state = state
        st.session_state.messages = [{"role": "assistant", "content": question_message(state)}]
        st.session_state.active = True
        st.session_state.last_error = ""
    except Exception as error:
        st.session_state.last_error = str(error)


def render_header() -> None:
    st.markdown('<div class="main-title">🎯 InterviewCoach AI</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Practice job interviews with an adaptive AI coach.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
<div class="info-card">
Choose a role, select MCQ answers, get scored feedback, and see your weak areas.
</div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> tuple[str, str, int, bool]:
    with st.sidebar:
        st.header("Interview Setup")
        role = st.radio("Role", ROLES, index=3)
        difficulty = st.radio("Difficulty", DIFFICULTIES, horizontal=True)
        max_questions = st.radio("Number of questions", QUESTION_OPTIONS, index=1, horizontal=True)

        st.divider()
        st.header("Session Controls")
        if st.button("Start Interview", use_container_width=True):
            start_interview(role, difficulty, max_questions)
        if st.button("Reset Interview", use_container_width=True):
            reset_active_interview()

        st.divider()
        st.header("Progress")
        state = st.session_state.get("interview_state") or {}
        answered = state.get("question_count", 0)
        total = state.get("max_questions", max_questions)
        progress = min(answered / total, 1.0) if total else 0.0
        st.caption(f"Question {min(answered + 1, total)} of {total}" if st.session_state.active else "No active interview")
        st.progress(progress)

        scores = state.get("scores", [])
        if scores:
            st.metric("Average Score", f"{calculate_average_score(scores)}/10")
        else:
            st.metric("Average Score", "-")

        st.divider()
        st.header("Settings / Info")
        mode_label = "Mock mode" if is_mock_mode() else "Gemini mode"
        st.caption(f"Mode: {mode_label}")
        show_saved_sessions = st.checkbox("Show saved sessions")

    return role, difficulty, max_questions, show_saved_sessions


def render_welcome() -> None:
    st.markdown("### Start a focused practice interview")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="info-card"><strong>1. Choose a role</strong><br>Pick the job path you want to practice.</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="info-card"><strong>2. Pick an option</strong><br>Select one MCQ choice at a time.</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="info-card"><strong>3. Get a final report</strong><br>See scores, weak areas, and next steps.</div>', unsafe_allow_html=True)

    st.info("Use the sidebar to start your interview.")
    st.markdown("**Example roles:** Frontend Developer, Backend Developer, Data Analyst, AI Engineer")


def render_chat_messages() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)


def render_side_panel(state: InterviewState) -> None:
    scores = state.get("scores", [])
    weak_areas = state.get("weak_areas", [])
    strong_areas = state.get("strong_areas", [])
    answered = state.get("question_count", 0)
    max_questions = state.get("max_questions", 5)

    st.markdown("### Coach Dashboard")
    metric_col1, metric_col2 = st.columns(2)
    metric_col1.metric("Average Score", f"{calculate_average_score(scores)}/10" if scores else "-")
    metric_col2.metric("Answered", f"{answered}/{max_questions}")
    st.metric("Weak Areas Count", len(set(weak_areas)))

    st.markdown('<div class="side-card"><strong>Current score</strong><br>', unsafe_allow_html=True)
    if state.get("last_grade"):
        st.write(f"{state['last_grade'].get('score', '-')}/10")
    else:
        st.write("Choose the first answer to see a score.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="side-card"><strong>Weak areas</strong><br>', unsafe_allow_html=True)
    if weak_areas:
        for area, count in Counter(weak_areas).most_common(4):
            st.markdown(f'<span class="pill">{area} ({count})</span>', unsafe_allow_html=True)
    else:
        st.caption("None yet.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="side-card"><strong>Strong areas</strong><br>', unsafe_allow_html=True)
    if strong_areas:
        for area in list(dict.fromkeys(strong_areas))[:4]:
            st.markdown(f'<span class="pill">{area}</span>', unsafe_allow_html=True)
    else:
        st.caption("Strong areas will appear as you score well.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="side-card"><strong>Interview progress</strong><br>', unsafe_allow_html=True)
    progress = min(answered / max_questions, 1.0) if max_questions else 0.0
    st.progress(progress)
    st.caption(f"{answered} of {max_questions} questions answered")
    st.markdown("</div>", unsafe_allow_html=True)


def readiness_box(readiness: str, message: str) -> None:
    readiness_lower = readiness.lower()
    if "strong" in readiness_lower:
        st.success(message)
    elif "medium" in readiness_lower:
        st.info(message)
    else:
        st.warning(message)


def render_final_report(state: InterviewState) -> None:
    report = state.get("final_report", {})
    if not report:
        return

    st.markdown("## Final Report")
    st.markdown("### Interview Summary")
    st.metric("Average Score", f"{report.get('average_score', 0)}/10")

    st.markdown("### Readiness Verdict")
    readiness_box(report.get("readiness_level", "Needs practice"), report.get("readiness_level", "Needs practice"))

    st.markdown("### Strong Areas")
    for item in report.get("strong_areas", []):
        st.markdown(f"- {item}")

    st.markdown("### Weak Areas")
    for item in report.get("weak_areas", []):
        st.markdown(f"- {item}")

    st.markdown("### Recommended Study Topics")
    for item in report.get("recommended_topics", []):
        st.markdown(f"- {item}")

    st.markdown("### Practice Tasks")
    for item in report.get("practice_tasks", []):
        st.markdown(f"- {item}")

    st.markdown("### Final Message")
    st.write(report.get("final_message", "Keep practicing."))

    if st.button("Start New Interview", use_container_width=True):
        reset_active_interview()
        st.rerun()


def handle_answer_submission(state: InterviewState) -> None:
    if state.get("stage") != "waiting_for_answer":
        return

    choices = state.get("choices", [])
    if not choices:
        st.warning("No answer choices were generated. Please reset and start again.")
        return

    answer_key = (
        f"answer_{state.get('session_id')}_{state.get('question_count')}_"
        f"{len(state.get('asked_questions', []))}"
    )
    selected_answer = st.radio(
        "Select your answer",
        choices,
        index=None,
        key=answer_key,
    )

    if not st.button("Submit Answer", use_container_width=True):
        return

    if not selected_answer:
        st.warning("Please select an answer before I grade it.")
        return

    st.session_state.messages.append({"role": "user", "content": f"Selected: {selected_answer}"})
    state["user_answer"] = selected_answer

    try:
        updated_state = grade_current_answer(state)
    except Exception as error:
        st.error("Something went wrong while grading. Please try again.")
        st.session_state.last_error = str(error)
        return

    validation_from_graph = updated_state.get("validation_message")
    if validation_from_graph:
        st.warning(validation_from_graph)
        return

    grade = updated_state.get("last_grade", {})
    if grade:
        st.session_state.messages.append({"role": "assistant", "content": grade_message(grade)})

    if updated_state.get("stage") == "complete":
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": "Interview complete. Your final report is ready below.",
            }
        )
    else:
        st.session_state.messages.append({"role": "assistant", "content": question_message(updated_state)})

    st.session_state.interview_state = updated_state
    st.rerun()


def render_saved_sessions() -> None:
    sessions = list_sessions()
    st.markdown("## Saved Sessions")
    if not sessions:
        st.info("No saved sessions yet.")
        return

    for session in sessions[:8]:
        answers = session.get("answers", [])
        scores = [int(answer.get("score", 0)) for answer in answers]
        average = calculate_average_score(scores)
        with st.expander(
            f"{session.get('role')} - {session.get('difficulty')} - {session.get('created_at')}"
        ):
            st.write(f"Session ID: `{session.get('session_id')}`")
            st.write(f"Answers: {len(answers)}")
            st.write(f"Average score: {average}/10" if scores else "Average score: -")


def main() -> None:
    st.set_page_config(page_title="InterviewCoach AI", page_icon="🎯", layout="wide")
    ensure_data_file()
    initialize_session_state()
    apply_styles()

    render_header()
    _, _, _, show_saved_sessions = render_sidebar()

    if is_mock_mode():
        st.warning("Running in mock mode because no Gemini API key was found.")
        st.info("Running in mock mode. Add your Gemini API key to .env for real AI responses.")

    if st.session_state.last_error:
        st.error("A friendly heads-up: something failed. Check the terminal for details and try again.")

    state = st.session_state.get("interview_state")
    if not st.session_state.active or not state:
        render_welcome()
    else:
        main_col, side_col = st.columns([2, 1], gap="large")
        with main_col:
            render_chat_messages()
            if state.get("stage") == "complete":
                render_final_report(state)
            else:
                handle_answer_submission(state)
        with side_col:
            render_side_panel(state)

    if show_saved_sessions:
        render_saved_sessions()


if __name__ == "__main__":
    main()
