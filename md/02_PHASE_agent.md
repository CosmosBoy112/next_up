# Phase 2 — Agent harness and tools (target: 75 min)

Read `00_SPEC.md` §6 and §7 again before starting. Phase 1 must be complete.

## Tasks
1. `agent/llm.py`
   - `class LLM` wrapping `openai.OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)`.
   - `chat(messages, tools) -> AssistantTurn(text, tool_calls=[{id, name, args_json}])`.
   - Native tool-calling mode by default. If the first call fails because tools are unsupported, permanently switch to **JSON mode** (SPEC §6 fallback) and synthesize `tool_call` ids, so the harness code path stays identical.
   - Retries: 3 attempts with backoff on transient errors. Timeout: 60 s.
2. `agent/tools.py`
   - OpenAI function-tool JSON schemas for every tool in SPEC §6 (`additionalProperties: false`).
   - Implementations call `core/repo.py`. Return compact JSON strings: IDs as strings, datetimes as local ISO with weekday, no embeddings ever.
   - `propose_action` validation: keep a per-run set `seen_volunteer_ids` filled by `find_candidates`, `search_volunteers`, and `volunteer_history`. Reject unseen IDs, a candidate who is already confirmed for the shift, or more than 3 candidates.
   - `dispatch(name, args_json, run_ctx) -> str`. Errors become strings, never exceptions.
3. `agent/prompts.py`
   - `SYSTEM_PROMPT` following SPEC §6 essentials.
   - `task_prompt(trigger_type, payload)` for `vacancy`, `coverage_scan`, and `custom_request`. Include today's date and time in America/New_York so the model can resolve "Saturday."
4. `agent/harness.py`
   - `run_agent(trigger_type, payload) -> run_id` implementing the ReAct loop, max_steps, recoverable errors, and per-step logging to `agent_log` (SPEC §6).
   - The run ends on the `finish` tool, a final text with no tool calls, or max_steps.
   - Return the `run_id`. Also provide `get_run_log(run_id)`.
5. A CLI for testing: `python -m agent.harness vacancy <shift_id> <cancelled_volunteer_id>`, `python -m agent.harness scan`, and `python -m agent.harness ask "<text>"`. Each prints the step log and resulting approval IDs.

## Files you MAY create or change
`agent/*`. Small additive helpers in `core/repo.py` only if needed (do not change existing function signatures).

## Files FROZEN
`00_SPEC.md`, phase files, `scripts/*`, `core/db.py`, `core/config.py`, `core/embeddings.py`, `ui/*`, `app.py`, `worker.py`.

## Acceptance checks
1. `reset_demo.py`, then cancel Alex Rivera's signup on "Saturday Delivery Run" via a Python snippet, then run the vacancy CLI → exactly one `fill_vacancy` approval with 2–3 candidates who are:
   - available for that time window
   - not Alex and not already confirmed
   - accompanied by concrete reasons and drafts under 60 words
2. `ask "Need 2 more drivers for the Saturday delivery run"` → the proposal contains only `can_drive = true` volunteers.
3. `scan` → 1 to 3 `coverage_invite` approvals.
4. Feed a malformed tool call (unit-test the dispatcher directly) → an error string, no crash.
5. Show the `agent_log` for one run: steps are ordered and every tool result is linked to its call.

## Report back
The mode used (native tools or JSON fallback), the average steps and latency per run, and any prompt changes made to get reliable behavior.
