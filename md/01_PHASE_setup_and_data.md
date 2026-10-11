# Phase 1 — Scaffold, connectivity, data layer, seed (target: 40 min)

Read `00_SPEC.md` fully first. This phase builds the foundation only. No agent and no UI yet.

## Tasks
1. Create the repo layout from SPEC §3. Fill in `requirements.txt`, `.env.example`, and `.gitignore`.
2. `core/config.py`: load env vars with `python-dotenv` and fail fast with a clear message for any missing variable.
3. `scripts/check_env.py`: check each item and print ✅/❌ for each:
   - Atlas ping and write/read of a temp doc
   - LLM endpoint: one tiny chat completion; then one completion **with a dummy tool**, reporting whether native tool calling works
   - embedding model loads and returns 384 dims
4. `core/db.py`: client singleton, collection handles, and `ensure_indexes()` covering every index in SPEC §4, including both vector search indexes (with the fallback behavior described there).
5. `core/embeddings.py`: load the model once (module-level cache); `embed(text)` and `embed_many(texts)`.
6. `core/repo.py`: implement these helpers now (the agent and UI will reuse them):
   - `get_volunteer`, `list_volunteers`, `update_volunteer_profile` (re-embeds the bio)
   - `get_shift`, `list_upcoming_shifts(days)`, `refresh_shift_status(shift_id)`
   - `confirmed_count(shift_id)`, `signup(volunteer_id, shift_id, source)`, `cancel_signup(signup_id)`
   - `hours_28d(volunteer_ids) -> dict` (**aggregation pipeline**)
   - `coverage_gaps(days) -> list` (**aggregation pipeline**)
   - `is_available(volunteer, shift) -> bool` (America/New_York weekday and time logic)
   - `vector_search_volunteers(query_vec, filter, limit)` and `vector_search_shifts(query_vec, filter, limit)` with the in-Python cosine fallback
7. `scripts/seed.py` and `scripts/reset_demo.py` per SPEC §9, including the planted "Saturday Delivery Run" with Alex Rivera.

## Files you MAY create or change
`requirements.txt`, `.env.example`, `.gitignore`, `core/*`, `scripts/*`, empty `__init__.py` files.

## Files FROZEN in this phase
`00_SPEC.md`, all phase files, `agent/*`, `ui/*`, `app.py`, `worker.py` (do not create these yet).

## Acceptance checks (run them yourself)
- `python scripts/check_env.py` → all ✅, or a clear ❌ with a reason (report the tool-calling result explicitly).
- `python scripts/reset_demo.py` → prints the counts: 40 volunteers, 14 shifts, about 120 signups.
- A quick Python snippet shows:
  - `coverage_gaps(7)` returns at least 3 shifts
  - `hours_28d` returns skewed values
  - a vector search for "can drive a van and lift boxes" returns drivers in the top results (either via `$vectorSearch` or the fallback; report which one was used)
- The "Saturday Delivery Run" is `filled` and includes Alex Rivera.

## Report back
What works, which fallbacks were triggered (vector index, tool calling), and the exact Atlas index JSON if I need to paste it manually.
