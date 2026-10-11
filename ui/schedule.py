"""Building blocks shared by the coordinator and volunteer views: page navigation, the
sidebar (Calendar + task list), the calendar, the side peek, and shift page pieces."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import streamlit as st
from streamlit_calendar import calendar

from core import repo
from ui.common import time_range

CALENDAR_DAYS = 28
PERIODS = ["Week", "Month"]
# kind -> (st.badge color, event background, event text, left accent bar). Pastel blocks
# with a bold bar, after the reference calendar: sky = open, green = covered/yours,
# purple = needs your decision, rose = recommended, gray = not for you.
KINDS = {
    "open": ("blue", "#e4f3fb", "#1f6f9e", "#3aa0d8"),
    "filled": ("green", "#e7f5eb", "#3a7a4a", "#5aa469"),
    "mine": ("green", "#e7f5eb", "#3a7a4a", "#5aa469"),
    "pending": ("violet", "#ece8fb", "#4c32b0", "#6c4fd8"),
    "request": ("violet", "#ece8fb", "#4c32b0", "#6c4fd8"),
    "recommended": ("red", "#fdecf0", "#b8405a", "#e86a7f"),
    "muted": ("gray", "#f2f3f7", "#7b839a", "#c3c8d6"),
    "cancelled": ("gray", "#f5f6f9", "#a0a6b8", "#dde1ea"),
}
_HOUR_24 = {"hour": "2-digit", "minute": "2-digit", "hour12": False}
CALENDAR_OPTIONS = {
    "views": {"timeGrid7": {"type": "timeGrid", "duration": {"days": 7},
                            "dayHeaderFormat": {"weekday": "short", "month": "numeric", "day": "numeric",
                                                "omitCommas": True}},
              "dayGridMonth": {"displayEventTime": False, "dayHeaderFormat": {"weekday": "short"}}},
    "headerToolbar": {"left": "prev,next title", "center": "", "right": "today"},
    "buttonText": {"today": "Today"},
    "slotMinTime": "07:00:00", "slotMaxTime": "21:00:00", "slotLabelFormat": _HOUR_24,
    "eventTimeFormat": _HOUR_24, "allDaySlot": False, "nowIndicator": True,
    "contentHeight": 660, "eventDisplay": "block",
}
# The component's own theme styles win without !important. The font is loaded again here
# because the calendar renders in its own iframe.
CALENDAR_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;600;700;800&display=swap');
.fc { font-family: 'Nunito Sans', sans-serif; color: #1f2547; }
.fc .fc-toolbar.fc-header-toolbar { margin-bottom: 1.1rem; }
.fc .fc-toolbar-chunk:first-child { display: flex; align-items: center; gap: .25rem; }
.fc-toolbar-title { font-size: 1.55rem !important; font-weight: 800; letter-spacing: -.02em; margin-left: .4rem !important; }
.fc .fc-prev-button, .fc .fc-next-button {
    background: transparent !important; border: none !important; box-shadow: none !important;
    color: #1f2547 !important; font-size: 1.15rem; padding: .2rem .35rem !important; }
.fc .fc-prev-button:hover, .fc .fc-next-button:hover { color: #5b5ff0 !important; }
.fc .fc-today-button {
    background: #f1f3f9 !important; color: #1f2547 !important; border: none !important;
    border-radius: 999px !important; box-shadow: none !important; font-weight: 700; padding: .45rem 1.1rem !important;
    opacity: 1 !important; }
.fc .fc-today-button:not(:disabled):hover { background: #5b5ff0 !important; color: #fff !important; }
.fc-theme-standard .fc-scrollgrid { border: none !important; }
.fc-theme-standard td, .fc-theme-standard th { border-color: #eef0f6 !important; }
.fc .fc-col-header { background: #f7f8fc; }
.fc .fc-col-header-cell { border: none !important; padding: 12px 0; }
.fc .fc-col-header-cell-cushion { text-transform: uppercase; color: #8a90a8; font-weight: 700;
    font-size: .95rem; letter-spacing: .03em; }
.fc .fc-day-today .fc-col-header-cell-cushion { color: #5b5ff0; }
.fc .fc-day-today { background: transparent !important; }
.fc .fc-daygrid-day.fc-day-today .fc-daygrid-day-number {
    background: #5b5ff0; color: #fff; border-radius: 999px; min-width: 1.8em; text-align: center; }
.fc .fc-timegrid-slot { height: 2.3em; }
.fc .fc-timegrid-slot-minor { border-top-style: none !important; }
.fc .fc-timegrid-slot-label-cushion { color: #8a90a8; font-size: .8rem; font-weight: 600; }
.fc .fc-daygrid-day-number { color: #4b5270; font-weight: 600; font-size: .85rem; }
.fc .fc-timegrid-axis, .fc .fc-timegrid-slot-label { border: none !important; }
.fc-event { cursor: pointer; border-width: 0 0 0 5px !important; border-radius: 4px 12px 12px 4px !important;
            box-shadow: none !important; transition: transform .15s ease, box-shadow .15s ease; }
.fc-event:hover { transform: translateY(-1px); box-shadow: 0 8px 18px rgba(76,86,150,.14) !important; }
.fc-timegrid-event .fc-event-main { padding: 6px 8px; }
.fc-timegrid-event .fc-event-main-frame { flex-direction: column-reverse; justify-content: space-between; height: 100%; }
.fc-event-title { font-weight: 700; font-size: .88rem; line-height: 1.25; white-space: normal; }
.fc-event-time { font-weight: 600; font-size: .76rem; opacity: .85; }
.fc-daygrid-event { padding: 2px 6px; }
.fc .fc-timegrid-now-indicator-line { border-color: #5b5ff0; border-width: 2px 0 0; }
.fc .fc-timegrid-now-indicator-arrow { border-color: #5b5ff0; border-bottom-color: transparent; border-top-color: transparent; }
"""

Item = tuple[dict, str, str]  # (shift, kind, tag)
Groups = list[tuple[str, list[Item]]]


# ---------- navigation state (per view namespace) ----------

def current_page(ns: str) -> tuple[str, str | None]:
    """("calendar", None) or ("task", shift_id)."""
    return st.session_state.get(f"{ns}__page", ("calendar", None))


def go(ns: str, page: str, shift_id: str | None = None) -> None:
    st.session_state[f"{ns}__page"] = (page, shift_id)
    st.session_state[f"{ns}__peek"] = None


def peek_id(ns: str) -> str | None:
    return st.session_state.get(f"{ns}__peek")


def open_peek(ns: str, shift_id: str | None) -> None:
    st.session_state[f"{ns}__peek"] = shift_id


def period(ns: str) -> str:
    return st.session_state.get(f"{ns}__period") or "Week"


# ---------- periods ----------

def period_end(p: str):
    """Exclusive end of the period, at local midnight. Week = today + 6 days (matches the
    calendar's 7-day view); Month = the rest of this calendar month."""
    today = repo.to_local(repo.now_utc()).replace(hour=0, minute=0, second=0, microsecond=0)
    if p == "Week":
        return today + timedelta(days=7)
    return (today.replace(day=28) + timedelta(days=4)).replace(day=1)


def fetch_days(p: str) -> int:
    """How far ahead to load shifts so the calendar has data when paging forward."""
    return max(CALENDAR_DAYS, (period_end(p) - repo.now_utc()).days + 8)


def in_period(s: dict, p: str) -> bool:
    return s["start"] < period_end(p)


# ---------- sidebar ----------

def sidebar_nav(ns: str) -> None:
    """Notion-style sidebar head: Calendar page link and the period switch for the task list.
    Not in a fragment, so changing the period reruns the whole page (calendar included)."""
    page, _ = current_page(ns)
    if st.button("Calendar", icon=":material/calendar_month:", key=f"{ns}__nav_cal", width="stretch",
                 type="secondary" if page == "calendar" else "tertiary"):
        go(ns, "calendar")
        st.rerun()
    with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="distribute"):
        st.markdown(":gray[**Tasks**]", width="content")
        st.segmented_control("Period", PERIODS, default="Week", key=f"{ns}__period",
                             label_visibility="collapsed", width="content")


def task_items(ns: str, groups: Groups, empty: str) -> None:
    """The period's tasks, grouped. Clicking one opens its page. Call from a sidebar fragment."""
    page, active = current_page(ns)
    if not any(items for _, items in groups):
        st.caption(empty)
    for title, items in groups:
        if not items:
            continue
        st.caption(f"{title} · {len(items)}")
        for s, kind, tag in items:
            sid = str(s["_id"])
            start = repo.to_local(s["start"])
            label = (f":{KINDS[kind][0]}-badge[{tag}] **{s['title']}**  \n"
                     f":gray[{start:%a %-m/%-d · %-I:%M %p}]")
            if st.button(label, key=f"{ns}__task_{sid}", width="stretch",
                         type="secondary" if page == "task" and active == sid else "tertiary"):
                go(ns, "task", sid)
                st.rerun()


# ---------- calendar ----------

def event(s: dict, kind: str, title: str) -> dict:
    _, bg, text, accent = KINDS[kind]
    return {
        "id": str(s["_id"]), "title": title,
        "start": f"{repo.to_local(s['start']):%Y-%m-%dT%H:%M:%S}",
        "end": f"{repo.to_local(s['end']):%Y-%m-%dT%H:%M:%S}",
        "backgroundColor": bg, "borderColor": accent, "textColor": text,
    }


def shift_calendar(events: list[dict], ns: str) -> None:
    """Render the calendar; clicking an event opens it in the side peek."""
    p = period(ns)
    options = CALENDAR_OPTIONS | {"initialView": "timeGrid7" if p == "Week" else "dayGridMonth"}
    # initialView only applies on mount, so the period is part of the component key.
    with st.container(key="calwrap"):
        clicked = calendar(events=events, options=options, custom_css=CALENDAR_CSS,
                           callbacks=["eventClick"], key=f"{ns}__cal_{p}")
    click = ((clicked or {}).get("eventClick") or {}).get("event", {}).get("id")
    if click and click != st.session_state.get(f"{ns}__last_click_{p}"):
        st.session_state[f"{ns}__last_click_{p}"] = click
        open_peek(ns, click)


def legend(items: list[tuple[str, str]]) -> None:
    """items: (label, kind)"""
    st.markdown(" ".join(f":{KINDS[kind][0]}-badge[{label}]" for label, kind in items))


# ---------- side peek ----------

def peek(ns: str, shift: dict | None, body: Callable[[dict], None]) -> None:
    """Floating panel on the right with a quick look at one shift and a link to its page."""
    if shift is None:
        return
    sid = str(shift["_id"])
    with st.container(key="peek"):
        with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="distribute"):
            if st.button("Open page", icon=":material/open_in_full:", type="tertiary", key=f"{ns}__peek_open"):
                go(ns, "task", sid)
                st.rerun()
            if st.button("", icon=":material/close:", type="tertiary", key=f"{ns}__peek_close"):
                open_peek(ns, None)
                st.rerun()
        body(shift)


# ---------- shift pieces ----------

def badge(label: str, kind: str) -> None:
    st.badge(label, color=KINDS[kind][0])


def shift_header(s: dict, label: str, kind: str) -> None:
    """Compact card header: title + status badge, when/where, fill progress."""
    start = repo.to_local(s["start"])
    st.markdown(f"#### {s['title']} :{KINDS[kind][0]}-badge[{label}]")
    st.markdown(f":gray[{start:%A, %b %-d} · {time_range(s['start'], s['end'])} · {s['location']}]")
    fill_bar(s)


def fill_bar(s: dict) -> None:
    req, conf = s["required_count"], s.get("confirmed_count", 0)
    st.progress(min(conf / req, 1.0) if req else 1.0, text=f"{conf}/{req} filled")


def back_link(ns: str) -> None:
    if st.button("Calendar", icon=":material/arrow_back:", type="tertiary", key=f"{ns}__back"):
        go(ns, "calendar")
        st.rerun()


def page_title(s: dict, label: str, kind: str) -> None:
    st.title(f"{s['title']} :{KINDS[kind][0]}-badge[{label}]")


def properties(s: dict, extra: list[tuple[str, str, str]] | None = None) -> None:
    """Notion-style property rows: icon + label on the left, value on the right."""
    start = repo.to_local(s["start"])
    rows = [
        ("event", "Date", f"{start:%A, %B %-d, %Y}"),
        ("schedule", "Time", time_range(s["start"], s["end"])),
        ("location_on", "Location", s["location"]),
        ("handyman", "Skills needed", ", ".join(s.get("required_skills", [])) or "None"),
        *(extra or []),
    ]
    with st.container(key="props"):
        for icon, label, value in rows:
            c = st.columns([1, 3], vertical_alignment="center")
            c[0].markdown(f":gray[:material/{icon}: {label}]")
            c[1].markdown(value)
        c = st.columns([1, 3], vertical_alignment="center")
        c[0].markdown(":gray[:material/group: Volunteers]")
        with c[1]:
            fill_bar(s)


def roster_table(shift_id) -> None:
    roster = repo.shift_roster(shift_id)
    if not roster:
        st.caption("Nobody has signed up yet.")
        return
    st.dataframe([{
        "Name": r["volunteer"]["name"],
        "Skills": ", ".join(r["volunteer"].get("skills", [])),
        "Drives": "Yes" if r["volunteer"].get("can_drive") else "",
        "Joined via": "Coordinator request" if r.get("source") == "agent" else "Self sign-up",
        "Signed up": f"{repo.to_local(r['created_at']):%b %-d, %-I:%M %p}",
    } for r in roster], hide_index=True, width="stretch")
