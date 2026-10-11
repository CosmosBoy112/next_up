"""Coordinator view: metrics, approval queue (the hero), agent requests, shift board, activity."""

from __future__ import annotations


import streamlit as st

from agent.harness import get_run_approvals, get_run_log, run_agent
from core import actions, repo
from ui.common import STATUS_CHIPS, TRIGGER_BADGES, flash, log_line, when


def render() -> None:
    st.title("🧭 Coordinator dashboard")
    metrics_row()
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("✋ Approval queue")
        st.caption("The agent proposes. Nothing reaches a volunteer until you approve.")
        approval_queue()
    with right:
        ask_agent()
        st.subheader("🤖 Agent activity")
        activity_feed()
    st.subheader("🗓️ Shift board · next 14 days")
    shift_board()


@st.fragment(run_every=3)
def metrics_row() -> None:
    m = repo.dashboard_metrics()
    c = st.columns(4)
    c[0].metric("Open slots · 7 days", m["open_slots_7d"])
    c[1].metric("Fill rate · 7 days", f"{m['fill_rate_7d']:.0%}")
    c[2].metric("Pending approvals", m["pending_approvals"])
    c[3].metric("Agent runs today", m["agent_runs_today"])


# ---------- approval queue ----------

@st.fragment(run_every=3)
def approval_queue() -> None:
    approvals = repo.pending_approvals()
    if not approvals:
        st.info("All caught up. New proposals appear here automatically.")
        return
    for a in approvals:
        approval_card(a)


def _trigger_text(a: dict) -> str:
    trig = a.get("trigger", {})
    if trig.get("type") == "vacancy":
        signup = repo.get_signup(trig["ref_id"]) if len(trig.get("ref_id", "")) == 24 else None
        if signup and signup["status"] == "cancelled":
            v = repo.get_volunteer(signup["volunteer_id"])
            return f"{v['name'] if v else 'A volunteer'} cancelled"
        return "Re-proposal after candidates declined" if signup is None else "Vacancy"
    if trig.get("type") == "custom_request":
        return f"“{trig.get('text', '')}”"
    return "Coverage scan"


def approval_card(a: dict) -> None:
    aid = str(a["_id"])
    shift = repo.get_shift(a["shift_id"])
    if shift is None:
        return
    names = repo.volunteer_names([c["volunteer_id"] for c in a["candidates"]])
    with st.container(border=True):
        badge = TRIGGER_BADGES.get(a["trigger"].get("type"), "🤖")
        open_slots = max(0, shift["required_count"] - repo.confirmed_count(shift["_id"]))
        st.markdown(f"**{badge}** · {_trigger_text(a)}")
        st.markdown(f"#### {shift['title']}")
        st.caption(f"{when(shift['start'], shift['end'])} · 📍 {shift['location']} · "
                   f"{open_slots} open slot(s)")
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
        if b[0].button(f"✅ Approve selected ({len(selected)})", key=f"approve_{aid}", type="primary",
                       disabled=not selected):
            res = actions.approve(aid, selected, drafts, note)
            flash(res.message, "📨" if res.ok else "ℹ️")
            st.rerun()
        if b[1].button("Reject", key=f"reject_{aid}"):
            res = actions.reject(aid, note)
            flash(res.message, "🗑️")
            st.rerun()
        with st.expander("🔍 Why? (agent reasoning & tool calls)"):
            render_run_log(a["agent_run_id"])


def render_run_log(run_id: str) -> None:
    entries = get_run_log(run_id)
    if not entries:
        st.caption("No log for this run.")
    for e in entries:
        st.markdown(f"`{e['step']:>2}` {log_line(e)}")


# ---------- agent requests ----------

def _run_with_status(trigger: str, payload: dict, label: str) -> None:
    """Run the agent behind a spinner and show only the outcome (steps stay in 🔍 Why?)."""
    try:
        with st.spinner(label):
            run_id = run_agent(trigger, payload)
    except Exception as e:  # noqa: BLE001 - surface in UI, keep app alive
        st.error(f"Agent error: {type(e).__name__}: {e}")
        return
    log = get_run_log(run_id)
    approvals = get_run_approvals(run_id)
    errors = [e for e in log if e["kind"] == "error"]
    if approvals:
        st.success(f"{len(approvals)} new proposal(s) added to the approval queue.")
    elif errors:
        st.error(f"The agent couldn't finish: {errors[-1]['content'][:200]}")
    else:
        final = next((e["content"] for e in reversed(log) if e["kind"] == "final"), "")
        st.info(final or "The agent didn't find anything to propose.")


def ask_agent() -> None:
    st.subheader("💬 Ask the agent")
    with st.form("nl_request", clear_on_submit=False):
        text = st.text_input("Request", placeholder="Need 2 more drivers for Saturday's pantry delivery",
                             label_visibility="collapsed")
        submitted = st.form_submit_button("Ask", type="primary")
    if submitted and text.strip():
        _run_with_status("custom_request", {"text": text.strip()}, "Agent is working on your request…")
    if st.button("📋 Run coverage scan (next 7 days)"):
        _run_with_status("coverage_scan", {"days": 7}, "Scanning coverage gaps…")


# ---------- feed & board ----------

@st.fragment(run_every=3)
def activity_feed() -> None:
    entries = repo.recent_agent_log(30)
    with st.container(height=380, border=True):
        if not entries:
            st.caption("No agent activity yet.")
        for e in entries:
            badge = TRIGGER_BADGES.get(e.get("trigger", ""), "")
            st.markdown(f":gray[{repo.to_local(e['ts']):%H:%M:%S} · {badge}]  \n{log_line(e)}")


@st.fragment(run_every=3)
def shift_board() -> None:
    rows = [{
        "When": when(s["start"], s["end"]),
        "Shift": s["title"],
        "Location": s["location"],
        "Filled": f"{s['confirmed_count']}/{s['required_count']}",
        "Status": STATUS_CHIPS.get(s["status"], s["status"]),
        "Skills": ", ".join(s.get("required_skills", [])),
    } for s in repo.shift_board(14)]
    st.dataframe(rows, width="stretch", hide_index=True)
