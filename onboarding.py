"""Guided onboarding tour helpers for InterviewCoach AI."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


TOUR_SEEN_PARAM = "ic_tour_seen"
TOUR_STORAGE_KEY = "interviewcoach_ai_focus_tour_seen"

TOUR_STEPS = [
    {
        "target": "role",
        "title": "Step 1: Pick your interview role",
        "body": "Start in the setup panel by choosing the role you want to practice, such as Frontend Developer, Backend Developer, Data Analyst, or AI Engineer.",
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
        "title": "Step 6: Review prep, answer, and improve",
        "body": "After practice starts, this area shows quick prep notes, one MCQ at a time, feedback after each answer, useful interview links, and your final report.",
    },
]


def tour_seen_from_url() -> bool:
    return st.query_params.get(TOUR_SEEN_PARAM) == "1"


def initialize_onboarding_state() -> None:
    """Show the tour only for a first browser visit, unless opened manually."""
    if not st.session_state.tour_state_initialized:
        st.session_state.show_onboarding = not tour_seen_from_url()
        st.session_state.tour_state_initialized = True

    if tour_seen_from_url() and not st.session_state.manual_onboarding_requested:
        st.session_state.show_onboarding = False
        st.session_state.onboarding_step = 0


def mark_onboarding_seen() -> None:
    st.session_state.show_onboarding = False
    st.session_state.onboarding_step = 0
    st.session_state.manual_onboarding_requested = False
    st.session_state.tour_seen_this_browser = True
    st.query_params[TOUR_SEEN_PARAM] = "1"


def open_onboarding_tour() -> None:
    st.session_state.show_onboarding = True
    st.session_state.onboarding_step = 0
    st.session_state.manual_onboarding_requested = True


def current_tour_target() -> str | None:
    if not st.session_state.get("show_onboarding", False):
        return None

    step = min(st.session_state.get("onboarding_step", 0), len(TOUR_STEPS) - 1)
    return TOUR_STEPS[step]["target"]


def render_tour_note(target: str, text: str) -> None:
    if current_tour_target() == target:
        st.markdown(f'<div class="tour-note">{text}</div>', unsafe_allow_html=True)


def render_onboarding_persistence_bridge() -> None:
    """Use browser localStorage so the first-visit tour does not repeat."""
    should_store_seen = (
        st.session_state.get("tour_seen_this_browser", False) or tour_seen_from_url()
    )
    components.html(
        f"""
<style>
html, body {{
    margin: 0;
    padding: 0;
    height: 0;
    min-height: 0;
    overflow: hidden;
    background: transparent;
}}
</style>
<script>
(function () {{
    const storageKey = "{TOUR_STORAGE_KEY}";
    const paramName = "{TOUR_SEEN_PARAM}";
    const shouldStoreSeen = {str(should_store_seen).lower()};

    try {{
        const url = new URL(window.parent.location.href);
        const seenInUrl = url.searchParams.get(paramName) === "1";

        if (shouldStoreSeen || seenInUrl) {{
            window.parent.localStorage.setItem(storageKey, "1");
            return;
        }}

        if (window.parent.localStorage.getItem(storageKey) === "1") {{
            url.searchParams.set(paramName, "1");
            window.parent.history.replaceState(null, "", url.toString());
            window.parent.location.reload();
        }}
    }} catch (error) {{
        console.debug("InterviewCoach tour persistence unavailable", error);
    }}
}})();
</script>
        """,
        height=0,
    )


@st.dialog("Guided onboarding tour")
def render_onboarding_tour() -> None:
    step_index = min(st.session_state.get("onboarding_step", 0), len(TOUR_STEPS) - 1)
    step = TOUR_STEPS[step_index]

    st.caption(f"{step_index + 1} of {len(TOUR_STEPS)}")
    st.progress((step_index + 1) / len(TOUR_STEPS))
    st.markdown(f"### {step['title']}")
    st.write(step["body"])
    st.caption("Move one step at a time. The setup and practice flow both happen on this main page.")

    back_col, next_col, skip_col = st.columns([1, 1, 1])
    with back_col:
        if st.button("Back", disabled=step_index == 0, use_container_width=True):
            st.session_state.onboarding_step = max(0, step_index - 1)
            st.rerun()

    with next_col:
        is_last = step_index == len(TOUR_STEPS) - 1
        if st.button("Finish" if is_last else "Next", use_container_width=True):
            if is_last:
                mark_onboarding_seen()
            else:
                st.session_state.onboarding_step = step_index + 1
            st.rerun()

    with skip_col:
        if st.button("Skip", use_container_width=True):
            mark_onboarding_seen()
            st.rerun()
