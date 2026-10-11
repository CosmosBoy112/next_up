# VolunteerOps — Project Spec (READ FIRST, DO NOT EDIT)

> This file is the single source of truth. Every phase prompt (01–05) refers to it.
> Claude Code: read this whole file before starting any phase. Never modify this file.

## 0. Context

- Event: c0mpiled-15 hackathon, Penn State. **Hard deadline: 8:00 PM ET today.** Working > polished.
- Target prizes:
  1. **Bloomerang** — "An AI agent for volunteer coordinators. The agent does the work; the coordinator stays in charge."
  2. **MongoDB** — "Highest-aura use of MongoDB."
- Submission = public GitHub repo + 90-second hosted video. No live presentation, so the README and demo flow matter a lot.

## 1. Product in one paragraph

A two-sided volunteer platform with an AI coordinator agent in the middle.
**Volunteers** set their profile and availability, browse and sign up for shifts, cancel, and accept or decline requests.
**Coordinators** see shift coverage, an **approval queue** of agent proposals, an agent activity log, and a natural-language request box.
The **agent** reacts to events in MongoDB (e.g., a cancellation), searches the accumulated data for the best replacements, drafts messages, and **proposes** actions. **Nothing reaches a volunteer until a coordinator approves it.**

## 2. Tech stack (fixed)

- Python 3.11+
- `streamlit` — one app, two views (Volunteer / Coordinator) switched in the sidebar
- `pymongo` (>= 4.7) — MongoDB Atlas (free M0 cluster is fine)
- `openai` Python SDK pointed at **Luminal's OpenAI-compatible endpoint** (env: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`)
- `sentence-transformers` with `all-MiniLM-L6-v2` (384-dim) for embeddings, run locally
- `python-dotenv`
- **No** LangChain, LlamaIndex, or other agent frameworks. The harness is hand-written (small and readable).
- **No** real email or SMS. "Sending" a message = inserting into the `messages` collection, which shows up in the volunteer inbox.

## 3. Repository layout

```
volunteerops/
├── README.md
├── requirements.txt
├── .env.example            # MONGODB_URI, DB_NAME, LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
├── .gitignore              # must include .env
├── app.py                  # Streamlit entry; sidebar switches views
├── ui/
│   ├── volunteer_view.py
│   └── coordinator_view.py
├── core/
│   ├── config.py           # env loading
│   ├── db.py               # Mongo client, collection handles, index setup
│   ├── embeddings.py       # load model once, embed(text) -> list[float]
│   ├── repo.py             # all read/write helpers used by UI and agent
│   └── actions.py          # approve/reject/accept/decline business logic
├── agent/
│   ├── llm.py              # OpenAI-compatible client wrapper, tool-calling + JSON fallback
│   ├── tools.py            # tool schemas + implementations
│   ├── prompts.py          # system prompt + per-trigger task prompts
│   └── harness.py          # ReAct loop: run_agent(trigger, payload) -> run_id
├── worker.py               # change-stream listener that triggers the agent
└── scripts/
    ├── check_env.py        # connectivity checks
    ├── seed.py             # deterministic demo data (random.seed(42))
    └── reset_demo.py       # wipe and reseed for a clean demo
```

## 4. MongoDB data model

All timestamps are timezone-aware UTC datetimes. Use `ObjectId` for `_id`.

**volunteers**
```
{ _id, name, email, org, skills: [str], bio: str, bio_embedding: [float x384],
  can_drive: bool, availability: [{day: "Mon".."Sun", start: "HH:MM", end: "HH:MM"}],
  created_at }
```

**shifts**
```
{ _id, title, org, location, start, end, required_count: int,
  required_skills: [str], description: str, description_embedding: [float x384],
  status: "open" | "filled" | "cancelled", created_at }
```
`status` is derived. Recompute it with `repo.refresh_shift_status(shift_id)` after any signup change.

**signups**
```
{ _id, shift_id, volunteer_id, status: "confirmed" | "cancelled" | "completed",
  source: "self" | "agent", created_at, updated_at }
```

**approvals** (the human-in-the-loop queue)
```
{ _id, kind: "fill_vacancy" | "coverage_invite" | "custom_request",
  shift_id, trigger: {type, ref_id, text?}, agent_run_id,
  summary: str,
  candidates: [{ volunteer_id, rank, reasons: [str], hours_28d: float,
                 draft_message: str, selected: bool }],
  status: "pending" | "approved" | "rejected",
  coordinator_note, created_at, decided_at }
```

**messages** (volunteer inbox)
```
{ _id, approval_id, shift_id, to_volunteer_id, body,
  status: "sent" | "accepted" | "declined" | "withdrawn",
  sent_at, responded_at }
```

**agent_log**
```
{ _id, run_id, trigger, step: int, kind: "thought" | "tool_call" | "tool_result" | "final" | "error",
  tool?, args?, content (short string, truncated to 1,000 chars), ts }
```

**Indexes** (created in `db.ensure_indexes()`, idempotent):
- `shifts`: `start`, `status`
- `signups`: `(shift_id, status)`, `(volunteer_id, status)`
- `approvals`: `(status, created_at)`
- `messages`: `(to_volunteer_id, status)`
- `agent_log`: `(run_id, step)`
- **Atlas Vector Search index** `volunteer_bio_vs` on `volunteers.bio_embedding` (384 dims, cosine), with filter fields `can_drive`, `skills`, `org`
- **Atlas Vector Search index** `shift_desc_vs` on `shifts.description_embedding` (384 dims, cosine), with filter field `status`

Create the vector indexes with `collection.create_search_index(SearchIndexModel(..., type="vectorSearch"))`. If that fails on the cluster, print the exact JSON definition so the user can paste it into the Atlas UI, and continue.
**Fallback:** if `$vectorSearch` errors (index not ready yet), `repo` falls back to in-Python cosine similarity over the embeddings, so the demo never breaks.

## 5. MongoDB features we must visibly use ("aura" checklist)

1. **Flexible document model**: nested availability, skills arrays, embedded candidate lists inside approvals.
2. **Atlas Vector Search** (`$vectorSearch` with `filter`): semantic candidate matching combined with structured filters in one query.
3. **Change Streams**: `worker.py` watches `signups` for status → `cancelled` and fires the agent. No polling. If change streams are unavailable, fall back to polling every 3 s and log a warning.
4. **Aggregation pipelines**: `hours_28d` fairness score, coverage gaps for the next 7 days, and dashboard metrics.
5. **Audit trail**: every agent step is stored in `agent_log` and shown in the UI.

## 6. Agent design

### Principle
- **Deterministic code** does retrieval, filtering, and scoring (DB queries).
- **The LLM** decides which tools to call, ranks and explains candidates, and drafts messages.
- **The agent's only write tools are `propose_action` and `log_note`.** It can never confirm a signup or send a message directly. Approval in the UI performs the real write.

### Tools (`agent/tools.py`)

| name | args | returns |
|---|---|---|
| `get_shift` | `shift_id` | shift doc plus confirmed count and open slots |
| `get_coverage_gaps` | `days: int = 7` | shifts with `open_slots > 0`, sorted by start (aggregation) |
| `find_candidates` | `shift_id`, `need_text?: str`, `require_driver?: bool`, `limit: int = 8` | volunteers available for the shift time window, not already signed up, not the canceller; ranked by vector similarity (need_text or shift description vs bio) with `hours_28d` attached |
| `search_volunteers` | `query: str`, `require_driver?: bool`, `limit: int = 8` | free semantic search over volunteers (`$vectorSearch`) |
| `search_shifts` | `query: str`, `days: int = 14` | semantic search over upcoming open shifts |
| `volunteer_history` | `volunteer_id` | last 5 signups and `hours_28d` |
| `propose_action` | `kind`, `shift_id`, `summary`, `candidates: [{volunteer_id, reasons[], draft_message}]` | approval_id. **Validates that every `volunteer_id` was returned by a candidate or search tool earlier in this run**; otherwise it returns an error string to the model |
| `log_note` | `text` | ok |
| `finish` | `summary` | ends the run |

Availability check: a volunteer is available if any of their `availability` blocks has the same weekday as `shift.start` (in America/New_York) and fully covers the shift's local start–end time.

### Harness (`agent/harness.py`)
- `run_agent(trigger_type, payload) -> run_id`. Trigger types: `vacancy`, `coverage_scan`, `custom_request`.
- Classic ReAct: build messages → call LLM with tool schemas → execute every tool call → append `tool` messages linked by `tool_call_id` → repeat.
- `max_steps = 12`; on exceeding, log an error and stop gracefully.
- Malformed JSON args or an unknown tool → return an error string as the tool result (recoverable). Never crash.
- Log every step to `agent_log`.
- **Tool-calling fallback**: if the model or endpoint rejects `tools=`, switch to JSON mode. The system prompt then lists the tools, and the model replies with `{"tool": name, "args": {...}}` or `{"final": "..."}`. `agent/llm.py` hides this difference from the harness.

### System prompt essentials (`agent/prompts.py`)
- Role: assistant to a human volunteer coordinator. Proposes; never decides.
- Always gather facts with tools before proposing. Propose 2–3 candidates, ranked.
- Fairness: prefer people with lower `hours_28d` when fit is similar; say so in the reasons.
- Reasons must be concrete and short (availability match, skill match, hours, driver).
- Draft messages: warm, under 60 words, include shift title, date and time, and location; no pressure.
- Call `finish` when done.

## 7. Core flows (end-to-end)

1. **Vacancy**: a volunteer cancels in the UI → `signups.status = cancelled` → the change stream in `worker.py` → `run_agent("vacancy", {shift_id, cancelled_volunteer_id})` → an approval of kind `fill_vacancy` appears in the coordinator queue.
2. **Approve**: the coordinator ticks or unticks candidates, can edit each draft, and clicks Approve → `messages` are created (status `sent`) for the selected candidates → approval becomes `approved`.
3. **Respond**: the volunteer sees the message in their inbox → Accept creates a `confirmed` signup (`source = "agent"`), refreshes shift status, and if the shift is now full, sets other `sent` messages for that shift to `withdrawn`. Decline marks it declined. If all candidates declined and the shift is still short, enqueue a new vacancy run.
4. **Custom request**: the coordinator types a request, e.g. "Need 2 more drivers for Saturday's pantry delivery" → `run_agent("custom_request", {text})`, run synchronously with a spinner → approval(s).
5. **Coverage scan**: a button → `run_agent("coverage_scan", {days: 7})` → `coverage_invite` approvals for the top 3 gaps.

## 8. UI requirements

Sidebar: view switch (Volunteer / Coordinator); in Volunteer view, a "Logged in as" dropdown of volunteers. No auth.
Use `@st.fragment(run_every=3)` for live-updating panels (inbox, approval queue, agent log).

**Volunteer view**
- Profile: skills (multiselect), bio, can_drive, availability editor (simple table). On save, re-embed the bio.
- "Recommended for you": open shifts ranked by `$vectorSearch` of the bio against shift descriptions, filtered by availability.
- Browse open shifts with a Sign up button.
- My shifts: upcoming confirmed shifts with a Cancel button; completed hours total.
- Inbox: agent-originated requests (approved by the coordinator) with Accept and Decline.

**Coordinator view**
- Top metrics: open slots in the next 7 days, fill rate, pending approvals, agent runs today.
- **Approval queue** (the hero): one card per pending approval showing the summary, the trigger, and each candidate with rank, reasons, hours_28d, an editable draft, and a checkbox. Buttons: Approve selected, Reject, and a "Why?" expander showing that run's `agent_log`.
- Natural-language request box and a "Run coverage scan" button.
- Shift board for the next 14 days (table with status chips).
- Agent activity feed (latest 30 log entries).

Visual tone: clean, friendly, minimal. Use `st.container(border=True)` cards and emoji status chips. Don't over-style.

## 9. Seed data (`scripts/seed.py`)

Fictional organization: **"Valley Community Pantry"** (do not use real organizations' names).
- 40 volunteers: diverse fictional names; skills drawn from [driving, heavy lifting, food handling, spanish, data entry, event setup, first aid, kids activities, social media, photography]; about 30% can drive; 1–3 availability blocks each; a 1–2 sentence bio that mentions their skills naturally.
- 14 shifts over the next 14 days (pantry sorting, delivery runs, community dinner, kids reading hour, etc.), required_count 2–6, local times 9:00–20:00.
- About 120 signups: past shifts as `completed` (for hours history, with skewed workloads so fairness matters); upcoming shifts partially filled.
- **Plant one demo shift**: "Saturday Delivery Run" that is exactly full and includes a volunteer named "Alex Rivera," so cancelling Alex demonstrates the vacancy flow instantly.
- Deterministic: `random.seed(42)`. Compute embeddings in batch.

## 10. Global rules for Claude Code

- Work **phase by phase**. Only touch the files a phase allows. Stop at the end of each phase and report: what was done, how it was verified, and any blockers.
- Run the code you write. Verify each acceptance check yourself before reporting.
- Never print, log, or commit secrets. `.env` stays in `.gitignore`.
- Keep functions small and typed. No premature abstraction.
- If something is ambiguous, choose the simplest option that keeps the demo flow working, and note it in the report.
- If an external dependency fails (vector index, change streams, tool calling), use the fallback in this spec instead of stalling.
