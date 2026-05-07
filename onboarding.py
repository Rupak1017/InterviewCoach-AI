"""Guided onboarding tour helpers for InterviewCoach AI."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st
import streamlit.components.v1 as components


TOUR_SEEN_PARAM = "ic_tour_seen"
TOUR_STORAGE_KEY = "interviewcoach_ai_focus_tour_seen"

TOUR_STEPS = [
    {
        "target": "role",
        "title": "Welcome. Pick a role",
        "body": "Choose the interview track you want to practice first.",
    },
    {
        "target": "topic",
        "title": "Now pick any topic",
        "body": "Type the exact topic you want the coach to focus on.",
    },
    {
        "target": "difficulty",
        "title": "Choose a level",
        "body": "Pick how challenging the MCQ questions should feel.",
    },
    {
        "target": "questions",
        "title": "Choose question count",
        "body": "Pick 3 for a quick run, or 5 or 10 for a longer practice session.",
    },
    {
        "target": "start",
        "title": "Start Guided Practice",
        "body": "Now start the session. The coach will prepare notes, one MCQ at a time, feedback, links, and a final report.",
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


def can_use_onboarding_target(target: str) -> bool:
    """Disable non-focused setup controls while the guided journey is active."""
    current_target = current_tour_target()
    return current_target is None or current_target == target


def _current_step_index() -> int:
    return min(st.session_state.get("onboarding_step", 0), len(TOUR_STEPS) - 1)


def advance_onboarding_step() -> None:
    step_index = _current_step_index()
    if step_index >= len(TOUR_STEPS) - 1:
        mark_onboarding_seen()
    else:
        st.session_state.onboarding_step = step_index + 1


def go_back_onboarding_step() -> None:
    st.session_state.onboarding_step = max(0, _current_step_index() - 1)


def render_tour_note(target: str, text: str | None = None) -> None:
    if current_tour_target() == target:
        step_index = _current_step_index()
        step = TOUR_STEPS[step_index]
        detail = text or step["body"]
        st.markdown(
            f"""
<div class="tour-note">
    <strong>{step["title"]}</strong>
    <p>{detail}</p>
</div>
            """,
            unsafe_allow_html=True,
        )


def render_tour_controls(
    target: str,
    can_continue: bool = True,
    blocked_message: str = "",
    validate_on_continue: Callable[[], bool] | None = None,
    validation_message: str = "",
) -> None:
    if current_tour_target() != target:
        return

    step_index = _current_step_index()
    is_last = step_index == len(TOUR_STEPS) - 1
    message_key = f"tour_validation_{target}"

    if blocked_message and not can_continue:
        st.caption(blocked_message)
    if st.session_state.get(message_key):
        st.caption(st.session_state[message_key])

    back_col, ok_col, skip_col = st.columns([1, 1.35, 1])
    with back_col:
        if st.button(
            "Back",
            key=f"tour_back_{target}",
            disabled=step_index == 0,
            use_container_width=True,
        ):
            go_back_onboarding_step()
            st.rerun()

    with ok_col:
        label = "Finish tour" if is_last else "OK, continue"
        if st.button(
            label,
            key=f"tour_ok_{target}",
            disabled=not can_continue,
            use_container_width=True,
        ):
            if validate_on_continue and not validate_on_continue():
                st.session_state[message_key] = validation_message
                st.rerun()

            st.session_state.pop(message_key, None)
            advance_onboarding_step()
            st.rerun()

    with skip_col:
        if st.button("Skip", key=f"tour_skip_{target}", use_container_width=True):
            mark_onboarding_seen()
            st.rerun()


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


def render_onboarding_tour() -> None:
    """Legacy hook kept for app compatibility. The tour now renders inline."""
    return
