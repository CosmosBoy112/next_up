"""Coordinator view: Calendar page and per-shift task pages, a Notion-style sidebar,
a side peek for quick looks, and a floating assistant chat."""

from __future__ import annotations

import re
from collections import defaultdict

import streamlit as st

from agent.harness import get_run_approvals, get_run_log, run_agent
from core import actions, repo
from ui import floating
from ui import schedule as sched
from ui.common import EMAIL_CHIPS, STATUS_CHIPS, TRIGGER_BADGES, flash, log_line, when

NS = "coord"
SHIFT_REF_RE = re.compile(r"\s*\[shift_id=\w+\]$")
GREETING = ("Hi! Ask me to find volunteers for a shift, check the weather for outdoor shifts, "
            "or run a coverage scan. My proposals show up on the calendar for you to approve.")


def _load(period: str) -> tuple[list[dict], dict, dict]:
    """Shifts (with fill counts), pending proposals by shift id, and each shift's kind."""
    shifts = [s for s in repo.shift_board(sched.fetch_days(period)) if s["status"] != "cancelled"]
    proposals = defaultdict(list)
    for a in repo.pending_approvals():
        proposals[a["shift_id"]].append(a)
    kind = {s["_id"]: _kind(s, proposals.get(s["_id"], [])) for s in shifts}
    return shifts, proposals, kind


def _is_weather(proposals: list[dict]) -> bool:
    return any(a.get("kind") == "weather_alert" for a in proposals)


def _kind(s: dict, proposals: list[dict]) -> str:
    if _is_weather(proposals):
        return "weather"
    return "pending" if proposals else s["status"]


def _status(s: dict, proposals: list[dict]) -> tuple[str, str]:
    if _is_weather(proposals):
        return "weather alert", "weather"
    if proposals:
        return "proposal pending", "pending"
    return STATUS_CHIPS.get(s["status"], s["status"]), s["status"] if s["status"] in sched.KINDS else "muted"


# ---------- sidebar ----------

def sidebar() -> None:
    with st.container(key="side_card"):
        sched.sidebar_nav(NS)
        task_list()


@st.fragment(run_every=3)
def task_list() -> None:
    period = sched.period(NS)
    shifts, _, kind = _load(period)
    todo, covered = [], []
    for s in (s for s in shifts if sched.in_period(s, period)):
        fill = f"{s['confirmed_count']}/{s['required_count']}"
        if kind[s["_id"]] == "weather":
            todo.append((s, "weather", "weather"))
        elif kind[s["_id"]] == "pending":
            todo.append((s, "pending", "review"))
        elif s["open_slots"] > 0:
            todo.append((s, "open", fill))
        else:
            covered.append((s, "filled", fill))
    sched.task_items(NS, [("Needs action", todo), ("Covered", covered)], "No shifts in this period.")


# ---------- pages ----------

def render() -> None:
    page, shift_id = sched.current_page(NS)
    if page == "task" and shift_id:
        task_page(shift_id)
    else:
        calendar_page()
    assistant()


@st.fragment(run_every=3)
def calendar_page() -> None:
    period = sched.period(NS)
    shifts, proposals, kind = _load(period)

    events = [sched.event(s, kind[s["_id"]], f"{s['title']} ({s['confirmed_count']}/{s['required_count']})")
              for s in shifts]
    sched.shift_calendar(events, NS)
    sched.legend([("Needs volunteers", "open"), ("Filled", "filled"), ("Proposal to review", "pending"),
                  ("Weather alert", "weather")])

    by_id = {str(s["_id"]): s for s in shifts}
    sched.peek(NS, by_id.get(sched.peek_id(NS) or ""),
               lambda s: peek_card(s, proposals.get(s["_id"], [])))


def peek_card(s: dict, proposals: list[dict]) -> None:
    sched.shift_header(s, *_status(s, proposals))
    crew = repo.shift_crews([s["_id"]]).get(s["_id"], [])
    details = [f"Crew: {', '.join(crew)}" if crew else "Crew: nobody yet"]
    if s.get("required_skills"):
        details.append(f"Needs: {', '.join(s['required_skills'])}")
    st.caption(" · ".join(details))
    if plan := s.get("weather_plan"):
        st.caption(f":material/partly_cloudy_day: Weather plan: **{plan['title']}**")
    if proposals:
        label = "Review weather plan" if _is_weather(proposals) else f"Review {len(proposals)} proposal(s)"
        if st.button(label, icon=":material/fact_check:", type="primary", key=f"peek_review_{s['_id']}"):
            sched.go(NS, "task", str(s["_id"]))
            st.rerun()
    elif s["open_slots"] > 0:
        find_button(s)


def find_button(s: dict) -> None:
    sid = str(s["_id"])
    if st.button(f"Find volunteers ({s['open_slots']} open)", key=f"find_{sid}",
                 icon=":material/person_search:"):
        start = repo.to_local(s["start"])
        text = (f"Find {s['open_slots']} volunteer(s) for {s['title']} "
                f"on {start:%a %b %-d, %-I:%M %p}")
        st.session_state["agent_request"] = ("custom_request", {"text": f"{text} [shift_id={sid}]"}, text)
        st.session_state["chat_open"] = True
        st.rerun()


@st.fragment(run_every=3)
def task_page(shift_id: str) -> None:
    sched.back_link(NS)
    shift = repo.get_shift(shift_id)
    if shift is None:
        st.info("This shift no longer exists.")
        return
    confirmed = repo.confirmed_count(shift["_id"])
    s = shift | {"confirmed_count": confirmed, "open_slots": max(0, shift["required_count"] - confirmed)}
    proposals = [a for a in repo.pending_approvals() if a["shift_id"] == s["_id"]]

    sched.page_title(s, *_status(s, proposals))
    plan = s.get("weather_plan")
    sched.properties(s, [("partly_cloudy_day", "Weather plan", f"**{plan['title']}** · {plan['details']}")]
                     if plan else None)
    st.subheader("About")
    st.write(s["description"])

    if proposals:
        proposals_panel(s, proposals)

    st.subheader("Volunteers")
    sched.roster_table(s["_id"])
    if s["open_slots"] > 0 and not proposals:
        find_button(s)

    requests = repo.shift_requests(s["_id"])
    if requests:
        st.subheader("Requests sent")
        st.dataframe([{
            "Volunteer": m["name"],
            "Status": STATUS_CHIPS.get(m["status"], m["status"]),
            "Email": EMAIL_CHIPS.get(m.get("delivery", {}).get("email", {}).get("status"), "—"),
            "Sent":f"{repo.to_local(m['sent_at']):%b %-d, %-I:%M %p}" if m.get("sent_at") else "",
            "Responded": f"{repo.to_local(m['responded_at']):%b %-d, %-I:%M %p}" if m.get("responded_at") else "",
        } for m in requests], hide_index=True, width="stretch")


# ---------- approvals ----------

def proposals_panel(s: dict, proposals: list[dict]) -> None:
    """Agent proposals for this shift, in their own panel on the right. Can be tucked away."""
    hidden_key = f"{NS}__hide_proposals_{s['_id']}"
    if st.session_state.get(hidden_key):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown(f":blue-badge[:material/auto_awesome: {len(proposals)} agent proposal(s) waiting]",
                        width="content")
            if st.button("Review", icon=":material/right_panel_open:", key=f"show_props_{s['_id']}"):
                st.session_state[hidden_key] = False
                st.rerun()
        return
    floating.reserve_right(480)
    with st.container(key="proposals"):
        with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="distribute"):
            st.markdown(":blue[:material/auto_awesome:] **Agent proposal**", width="content")
            if st.button("", icon=":material/close:", type="tertiary", key=f"hide_props_{s['_id']}",
                         help="Hide proposals"):
                st.session_state[hidden_key] = True
                st.rerun()
        st.caption("Nothing reaches a volunteer until you approve.")
        for a in proposals:
            if a.get("kind") == "weather_alert":
                weather_panel(a)
            else:
                approval_panel(a)


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
    if trig.get("type") == "weather_check":
        return "Weather check"
    return "Coverage scan"


def weather_panel(a: dict) -> None:
    """A weather warning: the forecast, the agent's alternatives, and the notice to the crew."""
    aid = str(a["_id"])
    w, f = a["weather"], a["weather"]["forecast"] or {}
    with st.container(border=True):
        badge = "red" if w["severity"] == "severe" else "orange"
        source = " · simulated (demo)" if f.get("source") == "demo" else ""
        st.markdown(f":{badge}-badge[{w['severity']}] **{f.get('condition', 'Forecast').capitalize()}**"
                    f" :gray[· {_trigger_text(a)}{source}]")
        if f:
            tmin, tmax = f["temp_c"]
            st.markdown(f":material/water_drop: {f['rain_chance_pct']}% · :material/rainy: {f['precip_mm']} mm · "
                        f":material/air: {f['gust_kmh']} km/h · :material/thermostat: {tmin}–{tmax}°C")
        st.markdown("\n".join(f"- {r}" for r in w["reasons"]))
        st.write(a["summary"])

        alts = a["alternatives"]
        pick = st.radio("Choose a plan", range(len(alts)), key=f"wx_pick_{aid}",
                        format_func=lambda i: alts[i]["title"], captions=[x["details"] for x in alts])
        notice = st.text_area("Notice to the crew", alts[pick]["notice_message"], key=f"wx_notice_{aid}_{pick}",
                              height=140)
        crew = repo.confirmed_count(a["shift_id"])
        note = st.text_input("Note (optional)", key=f"note_{aid}")
        with st.container(horizontal=True):
            approve = st.button(f"Approve & notify crew ({crew})", key=f"wx_ok_{aid}", type="primary")
            dismiss = st.button("Dismiss", key=f"wx_no_{aid}")
        if approve:
            res = actions.approve_weather(aid, pick, notice, note)
            flash(res.message)
            st.rerun()
        if dismiss:
            res = actions.reject(aid, note)
            flash(res.message)
            st.rerun()
        with st.expander("Why? (agent reasoning & tool calls)"):
            render_run_log(a["agent_run_id"])


def approval_panel(a: dict) -> None:
    aid = str(a["_id"])
    names = repo.volunteer_names([c["volunteer_id"] for c in a["candidates"]])
    with st.container(border=True):
        badge = TRIGGER_BADGES.get(a["trigger"].get("type"), "Agent")
        st.markdown(f":gray[{badge} · {_trigger_text(a)}]")
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

def assistant() -> None:
    """Floating assistant: a round button bottom-right opens a pill chat bar; the conversation
    shows in a panel above it."""
    is_open = st.session_state.get("chat_open", False)
    with st.container(key="fab"):
        if st.button("", icon=":material/close:" if is_open else ":material/auto_awesome:",
                     key="fab_btn", help="Close assistant" if is_open else "Ask the assistant"):
            st.session_state["chat_open"] = not is_open
            st.rerun()
    if not is_open:
        return

    history = st.session_state.setdefault("chat", [{"role": "assistant", "content": GREETING}])
    with st.container(key="chatbar", horizontal=True, vertical_alignment="center"):
        with st.container(key="chat_spark", width="content"):
            st.markdown(":material/auto_awesome:")
        prompt = st.chat_input("Ask the assistant to find volunteers…", key="chat_prompt")
        if st.button("", icon=":material/forum:", type="tertiary", key="chat_panel_btn",
                     help="Show conversation"):
            st.session_state["chat_panel"] = not st.session_state.get("chat_panel", False)

    req = st.session_state.pop("agent_request", None)
    if prompt:
        req = ("custom_request", {"text": prompt}, prompt)
    if req:
        st.session_state["chat_panel"] = True
    if not st.session_state.get("chat_panel"):
        return

    with st.container(key="chatpanel"):
        with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="distribute"):
            st.markdown("**Assistant**", width="content")
            with st.container(horizontal=True, width="content"):
                if st.button("Weather check", icon=":material/partly_cloudy_day:", type="tertiary",
                             key="chat_weather"):
                    st.session_state["agent_request"] = ("weather_check", {"days": 7},
                                                         "Check the weather for outdoor shifts this week")
                    st.rerun()
                if st.button("Coverage scan", icon=":material/radar:", type="tertiary", key="chat_scan"):
                    st.session_state["agent_request"] = ("coverage_scan", {"days": 7},
                                                         "Run a coverage scan for the next 7 days")
                    st.rerun()
        for m in history:
            st.chat_message(m["role"]).markdown(m["content"])
        if req:
            trigger, payload, shown = req
            st.chat_message("user").markdown(shown)
            with st.chat_message("assistant"):
                reply = _run_with_status(trigger, payload)
            history += [{"role": "user", "content": shown}, {"role": "assistant", "content": reply}]
        with st.expander("Activity log"):
            activity_feed()


def _run_with_status(trigger: str, payload: dict) -> str:
    """Run the agent behind a spinner and return only the outcome as a chat reply
    (the steps stay in the proposal's Why? log)."""
    try:
        with st.spinner("Working on it…"):
            run_id = run_agent(trigger, payload)
    except Exception as e:  # noqa: BLE001 - surface in UI, keep app alive
        return f"Sorry, something went wrong: {type(e).__name__}: {e}"
    log = get_run_log(run_id)
    approvals = get_run_approvals(run_id)
    errors = [e for e in log if e["kind"] == "error"]
    if approvals:
        lines = []
        for a in approvals:
            s = repo.get_shift(a["shift_id"])
            lines.append(f"- **{s['title']}** · {when(s['start'], s['end'])}" if s else "- (unknown shift)")
        return (f"{len(approvals)} new proposal(s) are waiting for your approval:\n" + "\n".join(lines))
    if errors:
        return f"I couldn't finish this one: {errors[-1]['content'][:200]}"
    final = next((e["content"] for e in reversed(log) if e["kind"] == "final"), "")
    return final or "I didn't find anything to propose."


def activity_feed() -> None:
    entries = repo.recent_agent_log(30)
    with st.container(height=280):
        if not entries:
            st.caption("No agent activity yet.")
        for e in entries:
            badge = TRIGGER_BADGES.get(e.get("trigger", ""), "")
            st.markdown(f":gray[{repo.to_local(e['ts']):%H:%M:%S} · {badge}]  \n{log_line(e)}")
