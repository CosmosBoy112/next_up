"""Small formatting helpers shared by both views."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from core.repo import to_local

STATUS_CHIPS = {"open": "open", "filled": "filled", "cancelled": "cancelled",
                "sent": "awaiting reply", "accepted": "accepted",
                "declined": "declined", "withdrawn": "withdrawn",
                "unread": "new update", "read": "update read"}
EMAIL_CHIPS = {"queued": "queued", "sending": "sending", "sent": "emailed", "failed": "failed"}
TRIGGER_BADGES = {"vacancy": "Vacancy", "coverage_scan": "Coverage",
                  "custom_request": "Request", "weather_check": "Weather"}
LOG_LABELS = {"thought": "thought", "tool_call": "call", "tool_result": "result",
              "final": "final", "error": "error"}


def when(start: datetime, end: datetime | None = None) -> str:
    s = to_local(start)
    out = f"{s:%a %b %d} · {s:%-I:%M %p}"
    return out + (f"–{to_local(end):%-I:%M %p}" if end else "")


def time_range(start: datetime, end: datetime) -> str:
    return f"{to_local(start):%-I:%M %p}–{to_local(end):%-I:%M %p}"


def flash(message: str) -> None:
    """Queue a toast that survives the st.rerun() that follows an action."""
    st.session_state["_flash"] = message


def show_flash() -> None:
    if msg := st.session_state.pop("_flash", None):
        st.toast(msg)


def log_line(e: dict) -> str:
    label = LOG_LABELS.get(e["kind"], e["kind"])
    tool = f"`{e['tool']}` " if e.get("tool") else ""
    content = e.get("content", "").replace("\n", " ")
    if e["kind"] == "tool_call":
        content = content[:140]
    elif e["kind"] == "tool_result":
        content = content[:180] + ("…" if len(content) > 180 else "")
    return f":gray[{label}] {tool}{content}"
