"""Volunteer view: inbox, my shifts, recommendations, browse, profile."""

from __future__ import annotations

import re

import streamlit as st

from core import actions, repo
from core.repo import WEEKDAYS
from scripts.seed import ORG, SKILLS
from ui.common import STATUS_CHIPS, flash, when

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def render(volunteer: dict) -> None:
    vid = volunteer["_id"]
    st.title(f"👋 Hi, {volunteer['name'].split()[0]}")
    st.caption(f"{volunteer['org']} volunteer · {', '.join(volunteer.get('skills', [])) or 'no skills listed'}"
               + (" · 🚗 can drive" if volunteer.get("can_drive") else ""))

    pending = sum(1 for m in repo.inbox(vid) if m["status"] == "sent")
    tabs = st.tabs([f"📬 Inbox{f' ({pending})' if pending else ''}", "🗓️ My shifts",
                    "✨ Recommended", "🔎 Browse shifts", "👤 Profile"])
    with tabs[0]:
        inbox_panel(vid)
    with tabs[1]:
        my_shifts(vid)
    with tabs[2]:
        recommended(volunteer)
    with tabs[3]:
        browse(volunteer)
    with tabs[4]:
        profile(volunteer)


@st.fragment(run_every=3)
def inbox_panel(vid) -> None:
    msgs = repo.inbox(vid)
    if not msgs:
        st.info("No requests right now. New requests from your coordinator show up here live.")
        return
    for m in msgs:
        shift = m["shift"]
        with st.container(border=True):
            top = st.columns([4, 1])
            top[0].markdown(f"**{shift['title']}** · {when(shift['start'], shift['end'])}  \n"
                            f"📍 {shift['location']}")
            top[1].markdown(STATUS_CHIPS.get(m["status"], m["status"]))
            st.write(m["body"])
            st.caption(f"🤖 suggested by the coordinator's assistant, approved by {ORG} coordinator")
            if m["status"] == "sent":
                b = st.columns([1, 1, 4])
                if b[0].button("✅ Accept", key=f"acc_{m['_id']}", type="primary"):
                    res = actions.accept_message(m["_id"])
                    flash(res.message, "🎉" if res.ok else "ℹ️")
                    st.rerun()
                if b[1].button("Decline", key=f"dec_{m['_id']}"):
                    res = actions.decline_message(m["_id"])
                    flash(res.message, "👍")
                    st.rerun()


def my_shifts(vid) -> None:
    st.metric("Completed volunteer hours", f"{repo.completed_hours(vid):g} h")
    rows = repo.my_upcoming_shifts(vid)
    if not rows:
        st.info("No upcoming shifts. Check Recommended or Browse to sign up.")
    for r in rows:
        shift, signup = r["shift"], r["signup"]
        with st.container(border=True):
            c = st.columns([4, 1])
            c[0].markdown(f"**{shift['title']}** · {when(shift['start'], shift['end'])}  \n"
                          f"📍 {shift['location']}"
                          + ("  \n🤖 joined via coordinator request" if signup.get("source") == "agent" else ""))
            with c[1].popover("Cancel"):
                st.write("Cancel this shift? Your coordinator will be notified.")
                if st.button("Yes, cancel", key=f"cancel_{signup['_id']}", type="primary"):
                    try:
                        repo.cancel_signup(signup["_id"])
                        flash("Shift cancelled. Thanks for letting us know.", "👍")
                    except ValueError as e:
                        flash(str(e), "ℹ️")
                    st.rerun()


def _shift_row(volunteer: dict, shift: dict, key_prefix: str, extra: str = "") -> None:
    with st.container(border=True):
        c = st.columns([4, 1])
        fits = "🟢 fits your availability" if repo.is_available(volunteer, shift) else "⚪ outside your availability"
        open_slots = shift.get("open_slots")
        slots = f" · {open_slots} spot(s) left" if open_slots is not None else ""
        c[0].markdown(f"**{shift['title']}** · {when(shift['start'], shift['end'])}{slots}  \n"
                      f"📍 {shift['location']} · {fits}{extra}")
        c[0].caption(shift["description"])
        if c[1].button("Sign up", key=f"{key_prefix}_{shift['_id']}"):
            try:
                repo.signup(volunteer["_id"], shift["_id"], source="self")
                flash(f"Signed up for {shift['title']}!", "🎉")
            except ValueError as e:
                flash(str(e), "ℹ️")
            st.rerun()


def recommended(volunteer: dict) -> None:
    st.caption("Open shifts matched to your bio (MongoDB Atlas Vector Search) and filtered by your availability.")
    recs = repo.recommended_shifts(volunteer["_id"])
    if not recs:
        st.info("No matching open shifts in your availability right now.")
    for s in recs:
        _shift_row(volunteer, s, "rec", extra=f" · match {s.get('score', 0):.0%}")


def browse(volunteer: dict) -> None:
    mine = {r["shift"]["_id"] for r in repo.my_upcoming_shifts(volunteer["_id"])}
    shifts = [s for s in repo.shift_board(14) if s["status"] == "open" and s["_id"] not in mine]
    if not shifts:
        st.info("No open shifts in the next 14 days.")
    for s in shifts:
        _shift_row(volunteer, s, "browse")


def profile(volunteer: dict) -> None:
    with st.form(f"profile_{volunteer['_id']}"):
        skills = st.multiselect("Skills", SKILLS, default=[s for s in volunteer.get("skills", []) if s in SKILLS])
        bio = st.text_area("Bio", volunteer.get("bio", ""), help="Used to match you with shifts.")
        can_drive = st.checkbox("🚗 I can drive", volunteer.get("can_drive", False))
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
                st.rerun()
