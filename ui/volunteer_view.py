"""Volunteer view: same layout as the coordinator. Calendar of shifts in the main column,
requests and recommendations in the side panel, profile editing in a dialog."""

from __future__ import annotations

import re

import streamlit as st

from core import actions, repo
from core.repo import WEEKDAYS
from scripts.seed import ORG, SKILLS
from ui import schedule as sched
from ui.common import STATUS_CHIPS, flash, when

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
MSG_KINDS = {"sent": "request", "accepted": "mine", "declined": "muted", "withdrawn": "muted"}


def render(volunteer: dict) -> None:
    main, side = st.columns([5, 2], gap="large")
    with main:
        schedule(volunteer)
    with side:
        side_panel(volunteer)


def _cal_key(volunteer: dict) -> str:
    return f"vol_calendar_{volunteer['_id']}"


@st.cache_data(ttl=60, show_spinner=False)
def _recommended(volunteer_id: str) -> list[dict]:
    """Vector search is the slow part; the schedule fragment reruns every few seconds."""
    return repo.recommended_shifts(volunteer_id)


def _refresh_recommendations() -> None:
    _recommended.clear()


# ---------- schedule (main) ----------

def _classify(volunteer: dict) -> tuple[dict[str, dict], dict[str, str], dict[str, dict]]:
    """shift id -> shift, shift id -> kind, shift id -> context (signup / message / score)."""
    vid = volunteer["_id"]
    board = {str(s["_id"]): s for s in repo.shift_board(sched.CALENDAR_DAYS)
             if s["status"] != "cancelled"}
    shifts, kinds, ctx = {}, {}, {}

    for sid, s in board.items():
        if s["open_slots"] > 0:
            shifts[sid], kinds[sid] = s, "open" if repo.is_available(volunteer, s) else "muted"
    for r in _recommended(str(vid)):
        sid = str(r["_id"])
        if sid in board:
            shifts[sid], kinds[sid] = board[sid], "recommended"
            ctx[sid] = {"score": r.get("score", 0)}
    for m in repo.inbox(vid):
        sid = str(m["shift_id"])
        if m["status"] == "sent" and sid in board:
            shifts[sid], kinds[sid] = board[sid], "request"
            ctx[sid] = {"message": m}
    for r in repo.my_upcoming_shifts(vid):
        sid = str(r["shift"]["_id"])
        if sid in board:
            shifts[sid], kinds[sid] = board[sid], "mine"
            ctx[sid] = {"signup": r["signup"]}
    return shifts, kinds, ctx


@st.fragment(run_every=3)
def schedule(volunteer: dict) -> None:
    st.title(f"{volunteer['name'].split()[0]}'s schedule")
    st.caption(f"{volunteer['org']} volunteer · {', '.join(volunteer.get('skills', [])) or 'no skills listed'}"
               + (" · can drive" if volunteer.get("can_drive") else ""))

    shifts, kinds, ctx = _classify(volunteer)
    count = lambda k: sum(1 for v in kinds.values() if v == k)  # noqa: E731
    c = st.columns(4)
    c[0].metric("My upcoming shifts", count("mine"))
    c[1].metric("Hours completed", f"{repo.completed_hours(volunteer['_id']):g} h")
    c[2].metric("Requests for you", count("request"))
    c[3].metric("Open shifts that fit you", count("open") + count("recommended"))

    titles = {"mine": "{t}", "request": "Request: {t}", "recommended": "{t} · for you",
              "open": "{t}", "muted": "{t}"}
    events = [sched.event(s, kinds[sid], titles[kinds[sid]].format(t=s["title"]))
              for sid, s in sorted(shifts.items(), key=lambda kv: kv[1]["start"])]
    key = _cal_key(volunteer)
    selected_id = sched.shift_calendar(events, key)
    sched.legend([("My shift", "mine"), ("Request for you", "request"), ("Recommended", "recommended"),
                  ("Open, fits you", "open"), ("Outside your availability", "muted")])

    if selected_id not in shifts:
        st.caption("Click a shift on the calendar to see details and sign up.")
        return
    s = shifts[selected_id]
    sched.day_heading(s)
    shift_card(volunteer, s, kinds[selected_id], ctx.get(selected_id, {}))


def shift_card(volunteer: dict, s: dict, kind: str, ctx: dict) -> None:
    sid = str(s["_id"])
    labels = {"mine": "you're signed up", "request": "request for you", "recommended": "recommended",
              "open": f"{s['open_slots']} spot(s) left", "muted": "outside your availability"}
    with st.container(border=True):
        sched.shift_header(s, labels[kind], kind)
        details = [s["description"]]
        if s.get("required_skills"):
            details.append(f"Needs: {', '.join(s['required_skills'])}")
        if "score" in ctx:
            details.append(f"Match with your bio: {ctx['score']:.0%}")
        st.caption(" · ".join(details))

        if kind == "request":
            m = ctx["message"]
            with st.container(border=True):
                st.write(m["body"])
                st.caption(f"Suggested by the coordinator's assistant, approved by {ORG} coordinator")
                _respond_buttons(m, "card")
        elif kind == "mine":
            signup = ctx["signup"]
            if signup.get("source") == "agent":
                st.caption("Joined via coordinator request")
            with st.popover("Cancel this shift"):
                st.write("Cancel this shift? Your coordinator will be notified.")
                if st.button("Yes, cancel", key=f"cancel_{signup['_id']}", type="primary"):
                    try:
                        repo.cancel_signup(signup["_id"])
                        flash("Shift cancelled. Thanks for letting us know.")
                    except ValueError as e:
                        flash(str(e))
                    _refresh_recommendations()
                    st.rerun()
        elif st.button("Sign up", key=f"signup_{sid}", type="primary"):
            try:
                repo.signup(volunteer["_id"], s["_id"], source="self")
                flash(f"Signed up for {s['title']}!")
            except ValueError as e:
                flash(str(e))
            _refresh_recommendations()
            st.rerun()


def _respond_buttons(m: dict, where: str) -> None:
    b = st.columns(2)
    if b[0].button("Accept", key=f"acc_{where}_{m['_id']}", type="primary", width="stretch"):
        res = actions.accept_message(m["_id"])
        flash(res.message)
        _refresh_recommendations()
        st.rerun()
    if b[1].button("Decline", key=f"dec_{where}_{m['_id']}", width="stretch"):
        res = actions.decline_message(m["_id"])
        flash(res.message)
        st.rerun()


# ---------- side panel ----------

def side_panel(volunteer: dict) -> None:
    head = st.columns([3, 2], vertical_alignment="center")
    head[0].subheader("Inbox")
    if head[1].button("Edit profile", icon=":material/person:", width="stretch"):
        profile_dialog(volunteer)
    inbox_panel(volunteer)
    st.subheader("Recommended for you")
    recommended_panel(volunteer)


@st.fragment(run_every=3)
def inbox_panel(volunteer: dict) -> None:
    msgs = repo.inbox(volunteer["_id"])
    with st.container(height=420, border=True):
        if not msgs:
            st.caption("No requests right now. New requests from your coordinator show up here live.")
        for m in msgs:
            shift = m["shift"]
            if shift is None:
                continue
            with st.container(border=True):
                st.markdown(f"**{shift['title']}**  \n:gray[{when(shift['start'], shift['end'])}]")
                sched.badge(STATUS_CHIPS.get(m["status"], m["status"]), MSG_KINDS.get(m["status"], "muted"))
                if m["status"] == "sent":
                    st.caption(m["body"])
                    _respond_buttons(m, "inbox")
                    _show_button(volunteer, shift, "inbox")


def recommended_panel(volunteer: dict) -> None:
    recs = _recommended(str(volunteer["_id"]))
    if not recs:
        st.caption("No matching open shifts in your availability right now.")
    for s in recs:
        with st.container(border=True):
            st.markdown(f"**{s['title']}**  \n:gray[{when(s['start'], s['end'])} · "
                        f"match {s.get('score', 0):.0%}]")
            _show_button(volunteer, s, "rec")


def _show_button(volunteer: dict, shift: dict, where: str) -> None:
    if st.button("Show on calendar", key=f"show_{where}_{shift['_id']}", width="stretch",
                 icon=":material/calendar_month:"):
        sched.select(_cal_key(volunteer), str(shift["_id"]))
        st.rerun()


# ---------- profile ----------

@st.dialog("Edit profile", width="large")
def profile_dialog(volunteer: dict) -> None:
    with st.form(f"profile_{volunteer['_id']}", border=False):
        skills = st.multiselect("Skills", SKILLS, default=[s for s in volunteer.get("skills", []) if s in SKILLS])
        bio = st.text_area("Bio", volunteer.get("bio", ""), help="Used to match you with shifts.")
        can_drive = st.checkbox("I can drive", volunteer.get("can_drive", False))
        st.markdown("**Availability**")
        availability = st.data_editor(
            volunteer.get("availability", []), num_rows="dynamic", width="stretch",
            column_config={
                "day": st.column_config.SelectboxColumn("Day", options=WEEKDAYS, required=True),
                "start": st.column_config.TextColumn("Start (HH:MM)", required=True),
                "end": st.column_config.TextColumn("End (HH:MM)", required=True),
            },
            key=f"avail_{volunteer['_id']}",
        )
        if st.form_submit_button("Save profile", type="primary"):
            if hasattr(availability, "to_dict"):  # DataFrame -> list of dicts
                availability = availability.to_dict("records")
            blocks = [b for b in availability if b and b.get("day")]
            bad = [b for b in blocks if not (TIME_RE.match(str(b.get("start", "")))
                                             and TIME_RE.match(str(b.get("end", "")))
                                             and b["start"] < b["end"])]
            if bad:
                st.error("Times must be HH:MM (24h) and start before end.")
            elif not bio.strip():
                st.error("Bio can't be empty.")
            else:
                repo.update_volunteer_profile(
                    volunteer["_id"], skills=skills, bio=bio.strip(), can_drive=can_drive,
                    availability=[{"day": b["day"], "start": b["start"], "end": b["end"]} for b in blocks])
                flash("Profile saved. Recommendations updated.")
                _refresh_recommendations()
                st.rerun()
