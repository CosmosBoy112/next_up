# Phase 3 — Approval actions and change-stream worker (target: 30 min)

Read `00_SPEC.md` §5 (Change Streams) and §7 (flows 1–3) again.

## Tasks
1. `core/actions.py`: business logic shared by the UI. Each function performs the real DB writes.
   - `approve(approval_id, selected_ids, edited_drafts: dict, note)` → creates `messages` (status `sent`) for the selected candidates; sets the approval to `approved` with `decided_at`.
   - `reject(approval_id, note)`.
   - `accept_message(message_id)` → if the shift still has open slots: create a `confirmed` signup (`source="agent"`), mark the message `accepted`, refresh shift status; if the shift is now full, withdraw the other `sent` messages for that shift. If the shift is already full: mark the message `withdrawn` and return a friendly notice.
   - `decline_message(message_id)` → mark it `declined`. If no `sent` messages remain for that approval and the shift still has open slots, insert a re-trigger marker (see below).
   - Use a **MongoDB transaction** (`client.start_session()` + `with_transaction`) for `accept_message`, so double-accepts can't overfill a shift. Mention this in the README later.
2. `worker.py`
   - Opens a change stream on `signups` with a pipeline matching updates where `updateDescription.updatedFields.status == "cancelled"`. Use `full_document="updateLookup"`.
   - Also watches a small `agent_triggers` collection (inserts) for decline re-triggers, so every agent wake-up is event-driven.
   - For each event: `run_agent("vacancy", {...})`. Run agents sequentially (simple queue) and catch and log every exception. The worker must never die.
   - Persist a resume token in an `worker_state` doc, so a restart doesn't miss or double-process events.
   - Fallback: if the change stream raises `OperationFailure` (not supported), poll every 3 s for newly cancelled signups using `updated_at`, and log a warning.
   - Clear console logs, e.g. `[event] cancellation shift=... → agent run ... → approval ...`.

## Files you MAY create or change
`core/actions.py`, `worker.py`. Additive helpers in `core/repo.py` and `core/db.py` (new collections `agent_triggers` and `worker_state` plus their indexes).

## Files FROZEN
`00_SPEC.md`, phase files, `agent/*` (unless there is a real bug; if so, describe it in the report), `scripts/*`, `ui/*`, `app.py`.

## Acceptance checks
1. Start `python worker.py` in one terminal. In another, `reset_demo.py`, then cancel Alex's signup → within about 10 s a new pending `fill_vacancy` approval exists, created by the worker.
2. Approve 2 candidates → 2 `sent` messages. Accept one → the shift becomes `filled`, and the other message becomes `withdrawn`.
3. Repeat with both declining → a re-trigger fires and a new approval is proposed, excluding the decliners.
4. Kill and restart the worker → no duplicate approval for an already-processed event.

## Report back
Whether native change streams worked on the cluster, and the end-to-end latency from cancellation to approval.
