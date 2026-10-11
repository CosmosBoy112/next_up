"""Small formatting helpers shared by both views."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from core.repo import to_local

STATUS_CHIPS = {"open": "🟡 open", "filled": "🟢 filled", "cancelled": "⚪ cancelled",
                "sent": "📨 awaiting reply", "accepted": "✅ accepted",
                "declined": "🙅 declined", "withdrawn": "↩️ withdrawn"}
TRIGGER_BADGES = {"vacancy": "🚨 vacancy", "coverage_scan": "📋 coverage",
                  "custom_request": "💬 request"}
LOG_ICONS = {"thought": "💭", "tool_call": "🔧", "tool_result": "📄", "final": "🏁", "error": "⚠️"}


def when(start: datetime, end: datetime | None = None) -> str:
    s = to_local(start)
    out = f"{s:%a %b %d} · {s:%-I:%M %p}"
    return out + (f"–{to_local(end):%-I:%M %p}" if end else "")


def flash(message: str, icon: str = "✅") -> None:
    """Queue a toast that survives the st.rerun() that follows an action."""
    st.session_state["_flash"] = (message, icon)


def show_flash() -> None:
    if msg := st.session_state.pop("_flash", None):
        st.toast(msg[0], icon=msg[1])


def log_line(e: dict) -> str:
    icon = LOG_ICONS.get(e["kind"], "•")
    tool = f"`{e['tool']}` " if e.get("tool") else ""
    content = e.get("content", "").replace("\n", " ")
    if e["kind"] == "tool_call":
        content = content[:140]
    elif e["kind"] == "tool_result":
        content = content[:180] + ("…" if len(content) > 180 else "")
    return f"{icon} {tool}{content}"
