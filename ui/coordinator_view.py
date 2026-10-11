"""Coordinator view: the shift schedule is the main surface; the agent lives in a chat panel."""

from __future__ import annotations

import re
import threading
import time
from collections import defaultdict
from datetime import timedelta

import streamlit as st

from agent.harness import get_run_approvals, get_run_log, run_agent
from core import actions, repo
from ui import schedule as sched
from ui.common import STATUS_CHIPS, TRIGGER_BADGES, flash, log_line, when

CAL_KEY = "coord_calendar"
SHIFT_REF_RE = re.compile(r"\s*\[shift_id=\w+\]$")
GREETING = ("Hi! Ask me to find volunteers for a shift, or run a coverage scan. "
            "My proposals show up on the schedule for you to approve.")


def render() -> None:
    main, side = st.columns([5, 2], gap="large")
    with main:
        schedule()
    with side:
        agent_panel()


# ---------- schedule (main) ----------

@st.fragment(run_every=3)
def schedule() -> None:
    st.title("Schedule")
    shifts = [s for s in repo.shift_board(sched.CALENDAR_DAYS) if s["status"] != "cancelled"]
    proposals = defaultdict(list)
    for a in repo.pending_approvals():
        proposals[a["shift_id"]].append(a)
    metrics_row(shifts, sum(len(v) for v in proposals.values()))

    events = [sched.event(s, "pending" if s["_id"] in proposals else s["status"],
                          f"{s['title']} ({s['confirmed_count']}/{s['required_count']})") for s in shifts]
    selected_id = sched.shift_calendar(events, CAL_KEY)
    sched.legend([("Needs volunteers", "open"), ("Filled", "filled"), ("Proposal to review", "pending")])

    by_id = {str(s["_id"]): s for s in shifts}
    review = sorted((by_id[str(sid)] for sid in proposals if str(sid) in by_id), key=lambda s: s["start"])
    if review:
        st.markdown("**Waiting for your review**")
        cols = st.columns(min(len(review), 4))
        for i, s in enumerate(review):
            if cols[i % len(cols)].button(f"{s['title']} · {repo.to_local(s['start']):%a %-I:%M %p}",
                                          key=f"review_{s['_id']}", width="stretch"):
                sched.select(CAL_KEY, str(s["_id"]))
                selected_id = str(s["_id"])

    selected = by_id.get(selected_id or "") or (review[0] if review else None)
    if selected is None:
        st.caption("Click a shift on the calendar to see its crew, open slots and agent proposals.")
        return
    sched.day_heading(selected)
    crew = repo.shift_crews([selected["_id"]]).get(selected["_id"], [])
    shift_card(selected, crew, proposals.get(selected["_id"], []))


def metrics_row(shifts: list[dict], pending: int) -> None:
    week_end = repo.now_utc() + timedelta(days=7)
    week = [s for s in shifts if s["start"] < week_end]
    required = sum(s["required_count"] for s in week)
    confirmed = sum(min(s["confirmed_count"], s["required_count"]) for s in week)
    c = st.columns(4)
    c[0].metric("Shifts · next 7 days", len(week))
    c[1].metric("Open slots", required - confirmed)
    c[2].metric("Fill rate", f"{confirmed / required:.0%}" if required else "100%")
    c[3].metric("Awaiting your approval", pending)


def shift_card(s: dict, crew: list[str], proposals: list[dict]) -> None:
    sid = str(s["_id"])
    with st.container(border=True):
        if proposals:
            sched.shift_header(s, "proposal pending", "pending")
        else:
            sched.shift_header(s, STATUS_CHIPS.get(s["status"], s["status"]),
                               s["status"] if s["status"] in sched.KINDS else "muted")

        details = [f"Crew: {', '.join(crew)}" if crew else "Crew: nobody yet"]
        if s.get("required_skills"):
            details.append(f"Needs: {', '.join(s['required_skills'])}")
        st.caption(" · ".join(details))

        if proposals:
            for a in proposals:
                approval_panel(a)
        elif s["open_slots"] > 0:
            if st.button(f"Find volunteers ({s['open_slots']} open)", key=f"find_{sid}",
                         icon=":material/person_search:"):
                start = repo.to_local(s["start"])
                text = (f"Find {s['open_slots']} volunteer(s) for {s['title']} "
                        f"on {start:%a %b %-d, %-I:%M %p}")
                st.session_state["agent_request"] = (
                    "custom_request", {"text": f"{text} [shift_id={sid}]"}, text)
                st.rerun()


# ---------- approvals (inside a shift card) ----------

def _trigger_text(a: dict) -> str:
    trig = a.get("trigger", {})
    if trig.get("type") == "vacancy":
        signup = repo.get_signup(trig["ref_id"]) if len(trig.get("ref_id", "")) == 24 else None
        if signup and signup["status"] == "cancelled":
            v = repo.get_volunteer(signup["volunteer_id"])
            return f"{v['name'] if v else 'A volunteer'} cancelled"
        return "Re-proposal after candidates declined" if signup is None else "Vacancy"
    if trig.get("type") == "custom_request":
        return f"“{SHIFT_REF_RE.sub('', trig.get('text', ''))}”"
    return "Coverage scan"


def approval_panel(a: dict) -> None:
    aid = str(a["_id"])
    names = repo.volunteer_names([c["volunteer_id"] for c in a["candidates"]])
    with st.container(border=True):
        badge = TRIGGER_BADGES.get(a["trigger"].get("type"), "Agent")
        st.markdown(f"**Agent proposal** · :gray[{badge} · {_trigger_text(a)}]")
        st.write(a["summary"])

        selected, drafts = [], {}
        for c in a["candidates"]:
            vid = str(c["volunteer_id"])
            with st.container(border=True):
                head = st.columns([3, 2])
                checked = head[0].checkbox(f"**#{c['rank']} {names.get(c['volunteer_id'], vid)}**",
                                           value=c.get("selected", c["rank"] <= 2),
                                           key=f"sel_{aid}_{vid}")
                hours = c.get("hours_28d", 0.0)
                head[1].progress(min(hours / 30, 1.0), text=f"{hours:g} h in last 28 days")
                st.markdown("\n".join(f"- {r}" for r in c.get("reasons", [])))
                drafts[vid] = st.text_area("Draft message", c["draft_message"], key=f"draft_{aid}_{vid}",
                                           height=90, label_visibility="collapsed")
                if checked:
                    selected.append(vid)

        note = st.text_input("Note (optional)", key=f"note_{aid}", placeholder="e.g. prefer Wei, he asked for more shifts")
        b = st.columns([2, 1, 3])
        if b[0].button(f"Approve selected ({len(selected)})", key=f"approve_{aid}", type="primary",
                       disabled=not selected):
            res = actions.approve(aid, selected, drafts, note)
            flash(res.message)
            st.rerun()
        if b[1].button("Reject", key=f"reject_{aid}"):
            res = actions.reject(aid, note)
            flash(res.message)
            st.rerun()
        with st.expander("Why? (agent reasoning & tool calls)"):
            render_run_log(a["agent_run_id"])


def render_run_log(run_id: str) -> None:
    entries = get_run_log(run_id)
    if not entries:
        st.caption("No log for this run.")
    for e in entries:
        st.markdown(f"`{e['step']:>2}` {log_line(e)}")


# ---------- agent chat panel (side) ----------

def agent_panel() -> None:
    st.subheader("Assistant")
    history = st.session_state.setdefault("chat", [{"role": "assistant", "content": GREETING}])
    box = st.container(height=520, border=True)
    with box:
        for m in history:
            st.chat_message(m["role"]).markdown(m["content"])

    if st.button("Run coverage scan (next 7 days)", icon=":material/radar:", width="stretch"):
        st.session_state["agent_request"] = ("coverage_scan", {"days": 7},
                                             "Run a coverage scan for the next 7 days")
    if prompt := st.chat_input("Need 2 more drivers for Saturday's pantry delivery"):
        st.session_state["agent_request"] = ("custom_request", {"text": prompt}, prompt)

    if req := st.session_state.pop("agent_request", None):
        trigger, payload, shown = req
        with box:
            st.chat_message("user").markdown(shown)
            with st.chat_message("assistant"):
                reply = _run_with_status(trigger, payload)
        history += [{"role": "user", "content": shown}, {"role": "assistant", "content": reply}]

    with st.expander("Activity log"):
        activity_feed()


def _run_with_status(trigger: str, payload: dict) -> str:
    """Run the agent in a thread, stream its agent_log steps into st.status, return a chat reply."""
    started = repo.now_utc()
    box: dict = {}

    def target():
        try:
            box["run_id"] = run_agent(trigger, payload)
        except Exception as e:  # noqa: BLE001 - surface in UI, keep app alive
            box["error"] = f"{type(e).__name__}: {e}"

    t = threading.Thread(target=target, daemon=True)
    t.start()
    shown = 0
    with st.status("Working on it…", expanded=True) as status:
        while t.is_alive() or shown == 0:
            entries = repo.agent_log_since(trigger, started)
            for e in entries[shown:]:
                if e["kind"] in ("tool_call", "final", "error", "thought"):
                    st.markdown(log_line(e))
            shown = len(entries)
            if not t.is_alive():
                break
            time.sleep(0.5)
        t.join()
        if "error" in box:
            status.update(label="Agent failed", state="error")
            return f"Sorry, something went wrong: {box['error']}"
        run_id = box["run_id"]
        log = get_run_log(run_id)
        errors = [e for e in log if e["kind"] == "error"]
        approvals = get_run_approvals(run_id)
        if errors and not approvals:
            status.update(label="Couldn't finish", state="error")
            return f"I couldn't finish this one: {errors[-1]['content'][:200]}"
        status.update(label="Done", state="complete", expanded=False)

    finals = [e["content"] for e in log if e["kind"] == "final"]
    lines = []
    for a in approvals:
        s = repo.get_shift(a["shift_id"])
        lines.append(f"- **{s['title']}** · {when(s['start'], s['end'])}" if s else "- (unknown shift)")
    reply = finals[-1] if finals else "Done."
    if approvals:
        reply += (f"\n\n{len(approvals)} proposal(s) are waiting for your approval on the schedule:\n"
                  + "\n".join(lines))
    else:
        reply += "\n\nNo new proposals this time."
    return reply


@st.fragment(run_every=3)
def activity_feed() -> None:
    entries = repo.recent_agent_log(30)
    with st.container(height=320):
        if not entries:
            st.caption("No agent activity yet.")
        for e in entries:
            badge = TRIGGER_BADGES.get(e.get("trigger", ""), "")
            st.markdown(f":gray[{repo.to_local(e['ts']):%H:%M:%S} · {badge}]  \n{log_line(e)}")
