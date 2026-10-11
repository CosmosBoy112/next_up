# Phase 4 — Streamlit UI: Volunteer and Coordinator views (target: 75 min)

Read `00_SPEC.md` §8 again. Phases 1–3 must be complete. The UI calls only `core/repo.py`, `core/actions.py`, and `agent/harness.run_agent`. No DB logic inside UI files.

## Tasks
1. `app.py`: page config (wide layout, title "VolunteerOps"), sidebar view switch, and a volunteer picker in Volunteer view. Cache the DB client and embedding model with `st.cache_resource`.
2. `ui/volunteer_view.py`: every section in SPEC §8 Volunteer view.
   - The inbox is a `@st.fragment(run_every=3)` that shows new requests live, with a small "🤖 suggested by the coordinator's assistant, approved by <org> coordinator" caption.
   - Cancel requires a confirm step (`st.popover` or a second click).
3. `ui/coordinator_view.py`: every section in SPEC §8 Coordinator view.
   - **Approval queue** as a live fragment. Each card shows:
     - the trigger badge (🚨 vacancy / 📋 coverage / 💬 request), summary, shift title, and local date and time
     - candidate rows: rank, name, reasons as bullets, `hours_28d` with a small bar or number, an editable `text_area` draft, and a checkbox (default: ranks 1–2 selected)
     - **Approve selected** / **Reject** buttons, a note field, and a "🔍 Why?" expander rendering that run's `agent_log` as a readable timeline (tool name, short args, short result)
   - NL request box: on submit, run the agent synchronously with `st.status` showing live step updates (poll `agent_log` for that run), then show the resulting approval.
   - "Run coverage scan" button, same pattern.
   - Metrics row computed via the aggregation helpers.
   - Agent activity feed as a live fragment.
4. Keep state handling simple. After any action, `st.rerun()`. Use `st.toast` for confirmations.

## Files you MAY create or change
`app.py`, `ui/*`. Additive read helpers in `core/repo.py` if necessary.

## Files FROZEN
`00_SPEC.md`, phase files, `agent/*`, `core/actions.py`, `worker.py`, `scripts/*`, `core/db.py`.

## Acceptance checks (do this with `streamlit run app.py` plus `python worker.py` running)
Walk through the full **demo script** and confirm every step works without touching code:
1. `reset_demo.py`. Volunteer view as **Alex Rivera** → cancel "Saturday Delivery Run."
2. Switch to Coordinator → a new approval appears within about 10 s without a manual refresh. Open "Why?" and see the steps.
3. Edit one draft, then approve 2 candidates.
4. Volunteer view as candidate #1 → the inbox shows the request → Accept → toast.
5. Coordinator → shift board shows the delivery run as filled; activity feed updated.
6. Coordinator NL box: "Need 2 more drivers for Saturday's pantry delivery" → live status → the approval shows drivers only.
7. Recommended-for-you shows sensible shifts for a volunteer whose bio mentions kids → "Kids Reading Hour" near the top.

## Report back
Screenshots are not needed. List any step that felt slow (over 15 s) and what caused it.
