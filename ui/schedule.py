"""Calendar + shift card building blocks shared by the coordinator and volunteer views."""

from __future__ import annotations

import streamlit as st
from streamlit_calendar import calendar

from core import repo
from ui.common import time_range

CALENDAR_DAYS = 28
# kind -> (st.badge color, calendar hex). One palette for both views.
KINDS = {
    "open": ("orange", "#d97706"),
    "filled": ("green", "#16a34a"),
    "mine": ("green", "#16a34a"),
    "pending": ("blue", "#2563eb"),
    "request": ("blue", "#2563eb"),
    "recommended": ("violet", "#7c3aed"),
    "muted": ("gray", "#6b7280"),
    "cancelled": ("gray", "#9ca3af"),
}
CALENDAR_OPTIONS = {
    "initialView": "timeGrid7",
    "views": {"timeGrid7": {"type": "timeGrid", "duration": {"days": 7}, "buttonText": "7 days"}},
    "headerToolbar": {"left": "prev,next today", "center": "title",
                      "right": "timeGrid7,dayGridMonth,listWeek"},
    "slotMinTime": "07:00:00", "slotMaxTime": "21:00:00",
    "allDaySlot": False, "nowIndicator": True, "contentHeight": 620,
}
# The component's own theme styles win without !important.
CALENDAR_CSS = """
.fc-event { cursor: pointer; }
.fc-event-title { font-weight: 600; white-space: normal; }
.fc-toolbar-title { font-size: 1.2rem !important; }
.fc .fc-button, .fc .fc-button-primary {
    background: transparent !important; color: inherit !important; box-shadow: none !important;
    border: 1px solid rgba(128,128,128,.35) !important; text-transform: capitalize; font-size: .85rem; }
.fc .fc-button:hover { background: rgba(128,128,128,.15) !important; }
.fc .fc-button-active, .fc .fc-button:disabled { background: rgba(128,128,128,.28) !important; }
.fc-theme-standard td, .fc-theme-standard th, .fc-theme-standard .fc-scrollgrid,
.fc .fc-timegrid-slot, .fc-theme-standard .fc-list { border-color: rgba(128,128,128,.22) !important; }
.fc .fc-timegrid-slot-minor { border-top-style: none !important; }
.fc .fc-day-today { background: rgba(37,99,235,.08) !important; }
"""


def event(s: dict, kind: str, title: str) -> dict:
    color = KINDS[kind][1]
    return {
        "id": str(s["_id"]), "title": title,
        "start": f"{repo.to_local(s['start']):%Y-%m-%dT%H:%M:%S}",
        "end": f"{repo.to_local(s['end']):%Y-%m-%dT%H:%M:%S}",
        "backgroundColor": color, "borderColor": color,
    }


def shift_calendar(events: list[dict], key: str) -> str | None:
    """Render the calendar; return the selected shift id (last clicked or set via select())."""
    clicked = calendar(events=events, options=CALENDAR_OPTIONS, custom_css=CALENDAR_CSS,
                       callbacks=["eventClick"], key=key)
    click = ((clicked or {}).get("eventClick") or {}).get("event", {}).get("id")
    if click and click != st.session_state.get(f"{key}__last"):
        st.session_state[f"{key}__last"] = click
        st.session_state[f"{key}__selected"] = click
    return st.session_state.get(f"{key}__selected")


def select(key: str, shift_id: str) -> None:
    st.session_state[f"{key}__selected"] = shift_id


def legend(items: list[tuple[str, str]]) -> None:
    """items: (label, kind)"""
    st.markdown(" ".join(f":{KINDS[kind][0]}-badge[{label}]" for label, kind in items))


def badge(label: str, kind: str) -> None:
    st.badge(label, color=KINDS[kind][0])


def day_heading(s: dict) -> None:
    st.markdown(f"#### {repo.to_local(s['start']):%A, %b %-d}")


def shift_header(s: dict, label: str, kind: str) -> None:
    """Top row of a shift card: title/time/location, fill progress, status badge."""
    c = st.columns([4, 3, 2], vertical_alignment="center")
    c[0].markdown(f"**{s['title']}**  \n:gray[{time_range(s['start'], s['end'])} · {s['location']}]")
    req, conf = s["required_count"], s.get("confirmed_count", 0)
    c[1].progress(min(conf / req, 1.0) if req else 1.0, text=f"{conf}/{req} filled")
    with c[2]:
        badge(label, kind)
