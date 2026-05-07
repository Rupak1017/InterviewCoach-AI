"""Shared Streamlit styling for InterviewCoach AI."""

from __future__ import annotations

import streamlit as st


def apply_styles() -> None:
    """Apply small product polish without changing Streamlit's core layout."""
    st.markdown(
        """
<style>
.stApp {
    --ic-card-bg: var(--secondary-background-color, #fafafa);
    --ic-feedback-bg: var(--background-color, #ffffff);
    --ic-border: rgba(120, 120, 120, 0.24);
    --ic-strong-border: rgba(120, 120, 120, 0.34);
    --ic-text: var(--text-color, #111827);
    --ic-pill-bg: var(--secondary-background-color, #f8fafc);
    --ic-pill-border: rgba(120, 120, 120, 0.28);
    --ic-tour-bg: #fffbeb;
    --ic-tour-border: #f59e0b;
    --ic-tour-text: #7c2d12;
    --ic-input-bg: #ffffff;
    --ic-input-border: rgba(255, 82, 82, 0.5);
    --ic-placeholder: rgba(55, 65, 81, 0.75);
    --ic-helper-text: #7f1d1d;
    --ic-accent: #ff4b4b;
    --ic-accent-hover: #e83e3e;
}

.main-title {
    font-size: 2.35rem;
    font-weight: 800;
    margin-bottom: 0rem;
    line-height: 1.08;
}

.subtitle {
    font-size: 1.05rem;
    color: var(--ic-text);
    opacity: 0.68;
    margin-bottom: 1.2rem;
}

.setup-shell {
    max-width: 1180px;
    margin: 0 auto;
}

.info-card, .feedback-card {
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid var(--ic-border);
    background: var(--ic-card-bg);
    color: var(--ic-text);
    margin-bottom: 1rem;
    overflow-wrap: anywhere;
}

.info-card *, .feedback-card * {
    color: inherit;
}

.feedback-card {
    border-color: var(--ic-strong-border);
    background: var(--ic-feedback-bg);
}

.feedback-card h3 {
    margin-top: 0;
    line-height: 1.2;
}

.small-muted {
    color: var(--ic-text);
    opacity: 0.68;
    font-size: 0.9rem;
}

.pill {
    display: inline-block;
    padding: 0.25rem 0.55rem;
    border-radius: 999px;
    border: 1px solid var(--ic-pill-border);
    background: var(--ic-pill-bg);
    color: var(--ic-text);
    margin: 0.15rem 0.2rem 0.15rem 0;
    font-size: 0.88rem;
    max-width: 100%;
    overflow-wrap: anywhere;
}

.loading-inline {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    color: var(--ic-text);
    opacity: 0.82;
    font-size: 0.92rem;
    margin-top: 0.75rem;
}

.loading-spinner {
    width: 1rem;
    height: 1rem;
    border-radius: 999px;
    border: 2px solid rgba(148, 163, 184, 0.35);
    border-top-color: #ff5252;
    animation: ic-spin 0.8s linear infinite;
}

@keyframes ic-spin {
    to {
        transform: rotate(360deg);
    }
}

.tour-note {
    padding: 0.65rem;
    border-radius: 8px;
    border: 1px solid var(--ic-tour-border);
    background: var(--ic-tour-bg);
    color: var(--ic-tour-text);
    margin: 0.35rem 0 0.75rem 0;
    font-size: 0.92rem;
    overflow-wrap: anywhere;
}

.topic-helper {
    border-left: 3px solid var(--ic-accent);
    color: var(--ic-helper-text);
    font-size: 0.88rem;
    font-weight: 650;
    line-height: 1.35;
    margin: 0.42rem 0 0.3rem 0;
    padding: 0.2rem 0 0.2rem 0.55rem;
}

[data-testid="stTextInput"] input {
    border: 1px solid var(--ic-input-border) !important;
    background: var(--ic-input-bg) !important;
    color: var(--ic-text) !important;
    caret-color: #111827 !important;
    box-shadow: 0 0 0 1px rgba(255, 82, 82, 0.06);
}

[data-testid="stTextInput"] input::placeholder {
    color: var(--ic-placeholder) !important;
    opacity: 1 !important;
}

[data-testid="stTextInput"]:focus-within input {
    border-color: var(--ic-accent) !important;
    caret-color: #111827 !important;
    box-shadow: 0 0 0 3px rgba(255, 82, 82, 0.16) !important;
}

.stButton > button[kind="primary"] {
    background: var(--ic-accent) !important;
    border-color: var(--ic-accent) !important;
    color: #ffffff !important;
    font-weight: 750 !important;
    box-shadow: 0 10px 22px rgba(255, 75, 75, 0.2);
}

.stButton > button[kind="primary"]:hover {
    background: var(--ic-accent-hover) !important;
    border-color: var(--ic-accent-hover) !important;
    color: #ffffff !important;
}

.stButton > button[kind="primary"]:disabled {
    background: rgba(255, 75, 75, 0.68) !important;
    border-color: rgba(255, 75, 75, 0.45) !important;
    color: rgba(255, 255, 255, 0.86) !important;
    box-shadow: none;
}

[data-testid="stDialogOverlay"] {
    backdrop-filter: blur(2px);
    background: rgba(15, 23, 42, 0.28);
}

div[role="dialog"] {
    border-radius: 12px;
}

[data-testid="stMarkdownContainer"],
[data-testid="stCaptionContainer"],
[data-testid="stChatMessageContent"] {
    overflow-wrap: anywhere;
}

div[data-testid="element-container"]:has([data-testid="stIFrame"]),
div[data-testid="element-container"]:has(iframe[title="streamlit.components.v1.html"]) {
    height: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}

[data-testid="stIFrame"],
[data-testid="stIFrame"] iframe,
iframe[title="streamlit.components.v1.html"] {
    height: 0 !important;
    min-height: 0 !important;
    border: 0 !important;
    display: block !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}

@media (prefers-color-scheme: dark) {
    .stApp {
        --ic-card-bg: rgba(31, 41, 55, 0.72);
        --ic-feedback-bg: rgba(17, 24, 39, 0.78);
        --ic-border: rgba(148, 163, 184, 0.28);
        --ic-strong-border: rgba(148, 163, 184, 0.34);
        --ic-text: #f8fafc;
        --ic-pill-bg: rgba(15, 23, 42, 0.7);
        --ic-pill-border: rgba(148, 163, 184, 0.36);
        --ic-tour-bg: rgba(120, 53, 15, 0.55);
        --ic-tour-border: rgba(251, 191, 36, 0.65);
        --ic-tour-text: #fde68a;
        --ic-input-bg: rgba(15, 23, 42, 0.86);
        --ic-input-border: rgba(255, 82, 82, 0.58);
        --ic-placeholder: rgba(226, 232, 240, 0.78);
        --ic-helper-text: #fecaca;
    }
}

html[data-theme="dark"] .stApp,
body[data-theme="dark"] .stApp,
.stApp[data-theme="dark"],
[data-theme="dark"] .stApp,
[data-baseweb-theme="dark"] .stApp {
    --ic-card-bg: rgba(31, 41, 55, 0.72);
    --ic-feedback-bg: rgba(17, 24, 39, 0.78);
    --ic-border: rgba(148, 163, 184, 0.28);
    --ic-strong-border: rgba(148, 163, 184, 0.34);
    --ic-text: #f8fafc;
    --ic-pill-bg: rgba(15, 23, 42, 0.7);
    --ic-pill-border: rgba(148, 163, 184, 0.36);
    --ic-tour-bg: rgba(120, 53, 15, 0.55);
    --ic-tour-border: rgba(251, 191, 36, 0.65);
    --ic-tour-text: #fde68a;
    --ic-input-bg: rgba(15, 23, 42, 0.86);
    --ic-input-border: rgba(255, 82, 82, 0.58);
    --ic-placeholder: rgba(226, 232, 240, 0.78);
    --ic-helper-text: #fecaca;
}

@media (min-width: 769px) {
    .block-container {
        max-width: 1240px;
        padding-top: 5.25rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    .app-header {
        max-width: 1180px;
        margin: 0 auto 2.25rem auto;
    }

    .main-title {
        font-size: clamp(2.35rem, 3vw, 3.15rem);
    }

    .subtitle {
        max-width: 720px;
    }

    .setup-shell [data-testid="stVerticalBlock"] {
        gap: 1rem;
    }
}

@media (max-width: 768px) {
    .block-container {
        padding: 2.25rem 0.85rem 2rem 0.85rem !important;
    }

    .app-header {
        padding-top: 0.25rem;
        margin-bottom: 1rem;
    }

    .main-title {
        font-size: clamp(1.42rem, 6vw, 1.62rem);
        line-height: 1.1;
        max-width: 100%;
        white-space: nowrap;
        text-align: left;
    }

    .subtitle {
        font-size: 0.88rem;
        line-height: 1.35;
        margin-bottom: 0.85rem;
        max-width: 100%;
    }

    .info-card, .feedback-card {
        padding: 0.85rem;
        margin-bottom: 0.75rem;
    }

    .feedback-card h3 {
        font-size: 1.18rem;
    }

    [data-testid="stChatMessage"] {
        padding: 0.65rem 0.35rem;
    }

    [data-testid="stChatMessageContent"] {
        max-width: calc(100vw - 4rem);
    }

    [data-testid="stMetric"] {
        padding: 0.6rem 0;
    }

    [data-testid="stRadio"] div[role="radiogroup"] {
        gap: 0.35rem;
        flex-wrap: wrap;
    }

    [data-testid="stRadio"] label {
        min-height: 2.7rem;
        align-items: flex-start;
        border: 1px solid rgba(148, 163, 184, 0.35);
        border-radius: 8px;
        background: transparent;
        color: inherit !important;
        margin-bottom: 0.4rem;
        width: 100%;
        padding-top: 0.35rem;
        padding-left: 0.65rem;
        padding-right: 0.65rem;
        padding-bottom: 0.35rem;
    }

    [data-testid="stRadio"] label:has(input:checked) {
        border-color: #ff5252;
        background: rgba(255, 82, 82, 0.12);
    }

    [data-testid="stRadio"] label p {
        color: inherit !important;
        line-height: 1.35;
    }

    .stButton > button {
        min-height: 2.75rem;
        white-space: normal;
    }

    [data-testid="stTextInput"] input {
        min-height: 2.75rem;
        font-size: 16px;
    }

    [data-testid="stExpander"] {
        max-width: 100%;
    }

    div[role="dialog"] {
        width: calc(100vw - 1.5rem) !important;
        max-width: calc(100vw - 1.5rem) !important;
    }
}

@media (max-width: 480px) {
    .main-title {
        font-size: clamp(1.32rem, 5.8vw, 1.48rem);
    }

    .subtitle {
        font-size: 0.9rem;
    }

    .pill {
        margin-right: 0.1rem;
    }
}
</style>
        """,
        unsafe_allow_html=True,
    )
