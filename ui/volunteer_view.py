"""Volunteer view: same structure as the coordinator. Calendar page and per-shift pages,
a sidebar with requests / my shifts / recommendations, profile editing in a dialog."""

from __future__ import annotations

import re

import streamlit as st

from core import actions, repo
from core.repo import WEEKDAYS
from scripts.seed import ORG, SKILLS
from ui import schedule as sched
from ui.common import flash

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _ns(volunteer: dict) -> str:
    return f"vol_{volunteer['_id']}"


@st.cache_data(ttl=60, show_spinner=False)
def _recommended(volunteer_id: str) -> list[dict]:
    """Vector search is the slow part; the schedule fragment reruns every few seconds."""
    return repo.recommended_shifts(volunteer_id)


def _refresh_recommendations() -> None:
    _recommended.clear()


def _classify(volunteer: dict, period: str) -> tuple[dict[str, dict], dict[str, str], dict[str, dict]]:
    """shift id -> shift, shift id -> kind, shift id -> context (signup / message / score)."""
    vid = volunteer["_id"]
    board = {str(s["_id"]): s for s in repo.shift_board(sched.fetch_days(period))
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
    notices: dict[str, list[dict]] = {}
    for m in repo.inbox(vid):
        sid = str(m["shift_id"])
        if m.get("kind") == "notice":
            notices.setdefault(sid, []).append(m)
        elif m["status"] == "sent" and sid in board:
            shifts[sid], kinds[sid] = board[sid], "request"
            ctx[sid] = {"message": m}
    for r in repo.my_upcoming_shifts(vid):
        sid = str(r["shift"]["_id"])
        if sid in board:
            shifts[sid], kinds[sid] = board[sid], "mine"
            ctx[sid] = {"signup": r["signup"]}
    for sid, ns in notices.items():
        if sid in shifts:
            ctx.setdefault(sid, {})["notices"] = ns
    return shifts, kinds, ctx


LABELS = {"mine": "you're signed up", "request": "request for you", "recommended": "recommended",
          "open": "open", "muted": "outside your availability"}


def _label(s: dict, kind: str) -> str:
    return f"{s['open_slots']} spot(s) left" if kind == "open" else LABELS[kind]


# ---------- sidebar ----------

def sidebar(volunteer: dict) -> None:
    with st.container(key="side_card"):
        sched.sidebar_nav(_ns(volunteer))
        task_list(volunteer)
        st.divider()
        if st.button("Edit profile", icon=":material/manage_accounts:", type="tertiary", key="edit_profile"):
            profile_dialog(volunteer)


@st.fragment(run_every=3)
def task_list(volunteer: dict) -> None:
    ns = _ns(volunteer)
    period = sched.period(ns)
    shifts, kinds, ctx = _classify(volunteer, period)
    groups = {"request": [], "mine": [], "recommended": []}
    tags = {"request": "request", "mine": "signed up", "recommended": "for you"}
    updates = []
    for sid, s in sorted(shifts.items(), key=lambda kv: kv[1]["start"]):
        if any(m["status"] == "unread" for m in ctx.get(sid, {}).get("notices", [])):
            updates.append((s, "weather", "update"))
        if kinds[sid] in groups and sched.in_period(s, period):
            groups[kinds[sid]].append((s, kinds[sid], tags[kinds[sid]]))
    sched.task_items(ns, [("Updates", updates), ("Requests for you", groups["request"]),
                          ("My shifts", groups["mine"]),
                          ("Recommended", groups["recommended"])],
                     "Nothing scheduled in this period. Open shifts are on the calendar.")


# ---------- pages ----------

def render(volunteer: dict) -> None:
    page, shift_id = sched.current_page(_ns(volunteer))
    if page == "task" and shift_id:
        task_page(volunteer, shift_id)
    else:
        calendar_page(volunteer)


@st.fragment(run_every=3)
def calendar_page(volunteer: dict) -> None:
    ns = _ns(volunteer)
    shifts, kinds, ctx = _classify(volunteer, sched.period(ns))
    st.caption(f"{volunteer['name']} · {', '.join(volunteer.get('skills', [])) or 'no skills listed'}"
               + (" · can drive" if volunteer.get("can_drive") else ""))

    titles = {"mine": "{t}", "request": "Request: {t}", "recommended": "{t} · for you",
              "open": "{t}", "muted": "{t}"}
    events = [sched.event(s, kinds[sid], titles[kinds[sid]].format(t=s["title"])
                          + (" · weather plan" if s.get("weather_plan") and kinds[sid] == "mine" else ""))
              for sid, s in sorted(shifts.items(), key=lambda kv: kv[1]["start"])]
    sched.shift_calendar(events, ns)
    sched.legend([("My shift", "mine"), ("Request for you", "request"), ("Recommended", "recommended"),
                  ("Open, fits you", "open"), ("Outside your availability", "muted")])

    def body(s: dict) -> None:
        sid = str(s["_id"])
        sched.shift_header(s, _label(s, kinds[sid]), kinds[sid])
        details = [s["description"]]
        if s.get("required_skills"):
            details.append(f"Needs: {', '.join(s['required_skills'])}")
        st.caption(" · ".join(details))
        for m in ctx.get(sid, {}).get("notices", [])[:1]:
            st.info(m["body"], icon=":material/partly_cloudy_day:")
        shift_actions(volunteer, s, kinds[sid], ctx.get(sid, {}), "peek")

    sched.peek(ns, shifts.get(sched.peek_id(ns) or ""), body)


@st.fragment(run_every=3)
def task_page(volunteer: dict, shift_id: str) -> None:
    ns = _ns(volunteer)
    sched.back_link(ns)
    shifts, kinds, ctx = _classify(volunteer, sched.period(ns))
    s = shifts.get(shift_id)
    kind = kinds.get(shift_id, "muted")
    if s is None:  # e.g. the shift filled up and you're not on it
        shift = repo.get_shift(shift_id)
        if shift is None:
            st.info("This shift no longer exists.")
            return
        confirmed = repo.confirmed_count(shift["_id"])
        s = shift | {"confirmed_count": confirmed, "open_slots": max(0, shift["required_count"] - confirmed)}
    c = ctx.get(shift_id, {})

    sched.page_title(s, _label(s, kind), kind)
    extra = [("auto_awesome", "Match with your bio", f"{c['score']:.0%}")] if "score" in c else []
    if plan := s.get("weather_plan"):
        extra.append(("partly_cloudy_day", "Weather plan", f"**{plan['title']}** · {plan['details']}"))
    sched.properties(s, extra)

    if notices := c.get("notices"):
        st.subheader("Update from your coordinator")
        for m in notices:
            with st.container(border=True):
                st.write(m["body"])
                st.caption(f"Sent {repo.to_local(m['sent_at']):%a %b %-d, %-I:%M %p}")
        if any(m["status"] == "unread" for m in notices):
            actions.mark_notices_read(volunteer["_id"], s["_id"])

    st.subheader("About")
    st.write(s["description"])

    if kind == "request":
        st.subheader("Request from your coordinator")
        with st.container(border=True):
            st.write(c["message"]["body"])
            st.caption(f"Suggested by the coordinator's assistant, approved by {ORG} coordinator")
            shift_actions(volunteer, s, kind, c, "page")
    else:
        shift_actions(volunteer, s, kind, c, "page")

    st.subheader("Who's going")
    crew = repo.shift_crews([s["_id"]]).get(s["_id"], [])
    st.markdown(" ".join(f":gray-badge[{n}]" for n in crew) if crew else ":gray[Nobody yet. Be the first!]")


def shift_actions(volunteer: dict, s: dict, kind: str, ctx: dict, where: str) -> None:
    """The one thing a volunteer can do with this shift right now."""
    sid = str(s["_id"])
    if kind == "request":
        _respond_buttons(ctx["message"], where)
    elif kind == "mine":
        signup = ctx["signup"]
        if signup.get("source") == "agent":
            st.caption("Joined via coordinator request")
        with st.popover("Cancel this shift"):
            st.write("Cancel this shift? Your coordinator will be notified.")
            if st.button("Yes, cancel", key=f"cancel_{where}_{signup['_id']}", type="primary"):
                try:
                    repo.cancel_signup(signup["_id"])
                    flash("Shift cancelled. Thanks for letting us know.")
                except ValueError as e:
                    flash(str(e))
                _refresh_recommendations()
                st.rerun()
    elif s["open_slots"] > 0 and st.button("Sign up", key=f"signup_{where}_{sid}", type="primary"):
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
