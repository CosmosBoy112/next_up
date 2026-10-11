# Test Fixtures & Scenarios (hand-crafted, deterministic)

> Claude Code: create `scripts/load_fixtures.py`. It wipes the DB and loads the fixture below; embed the bios and shift descriptions with `core/embeddings.py`.
> Use it **alongside** the random seed: the seed is for a realistic-looking demo, and this fixture is for **verifying agent behavior** (every person exists to test one rule).
> Then create `scripts/run_scenarios.py`, which runs T1–T10 below and prints PASS/FAIL for each.
> Do not edit `00_SPEC.md`. Fictional organization and people only.

All times are America/New_York. Store datetimes in UTC (for example, 10:00 ET on Oct 17 = 14:00Z).
Today in the fixture is **Sunday 2026-10-11**.

## Volunteers (12)

Each person is designed to trigger exactly one rule.

```json
[
  {"key":"alex",   "name":"Alex Rivera",   "can_drive":true,  "skills":["driving","heavy lifting"],
   "availability":[{"day":"Sat","start":"09:00","end":"14:00"}],
   "bio":"I drive my pickup for pantry deliveries and can lift heavy boxes.",
   "role_in_tests":"Confirmed on S1, then cancels -> triggers vacancy"},
  {"key":"jordan", "name":"Jordan Kim",    "can_drive":true,  "skills":["driving","heavy lifting"],
   "availability":[{"day":"Sat","start":"08:00","end":"15:00"}],
   "bio":"Weekend driver with a minivan, happy to load and unload deliveries.",
   "role_in_tests":"IDEAL replacement: available, driver, low hours (2h)"},
  {"key":"priya",  "name":"Priya Nair",    "can_drive":true,  "skills":["driving","food handling"],
   "availability":[{"day":"Sat","start":"09:00","end":"14:00"}],
   "bio":"I've been doing delivery runs most weekends this month.",
   "role_in_tests":"Good fit but OVERWORKED (18h in 28d) -> must rank below Jordan, reason mentions fairness"},
  {"key":"marcus", "name":"Marcus Chen",   "can_drive":false, "skills":["heavy lifting","event setup"],
   "availability":[{"day":"Sat","start":"09:00","end":"14:00"}],
   "bio":"Strong back, no car. Great at moving tables and boxes.",
   "role_in_tests":"Available but NOT a driver -> allowed for vacancy, excluded when driver required"},
  {"key":"ethan",  "name":"Ethan Brooks",  "can_drive":true,  "skills":["driving"],
   "availability":[{"day":"Sun","start":"08:00","end":"13:00"}],
   "bio":"I can drive deliveries on Sunday mornings.",
   "role_in_tests":"AVAILABILITY TRAP: perfect skills but Sunday only -> never proposed for Saturday"},
  {"key":"liam",   "name":"Liam O'Connor", "can_drive":true,  "skills":["driving","heavy lifting"],
   "availability":[{"day":"Sat","start":"11:00","end":"14:00"}],
   "bio":"Driver available late Saturday mornings.",
   "role_in_tests":"PARTIAL OVERLAP: S1 starts at 10:00 -> must be excluded"},
  {"key":"grace",  "name":"Grace Okafor",  "can_drive":true,  "skills":["driving"],
   "availability":[{"day":"Sat","start":"09:00","end":"14:00"}],
   "bio":"Regular Saturday delivery driver.",
   "role_in_tests":"ALREADY CONFIRMED on S1 -> must be excluded"},
  {"key":"sofia",  "name":"Sofia Alvarez", "can_drive":false, "skills":["spanish","food handling"],
   "availability":[{"day":"Thu","start":"16:00","end":"20:00"}],
   "bio":"Bilingual English/Spanish, I love serving at community dinners.",
   "role_in_tests":"Spanish speaker for S2"},
  {"key":"hannah", "name":"Hannah Lee",    "can_drive":false, "skills":["first aid","event setup"],
   "availability":[{"day":"Thu","start":"15:00","end":"21:00"}],
   "bio":"New volunteer, certified in first aid, can help set up events.",
   "role_in_tests":"Brand new (0h) -> fairness favors her for S2"},
  {"key":"daniel", "name":"Daniel Park",   "can_drive":false, "skills":["food handling","heavy lifting"],
   "availability":[{"day":"Thu","start":"16:00","end":"20:00"}],
   "bio":"Kitchen helper for dinners, I also do heavy lifting.",
   "role_in_tests":"Most overworked (25h); already confirmed on S2"},
  {"key":"maya",   "name":"Maya Patel",    "can_drive":false, "skills":["kids activities"],
   "availability":[{"day":"Tue","start":"15:00","end":"18:00"}],
   "bio":"Elementary education major who loves reading stories to kids.",
   "role_in_tests":"Recommended-for-you test -> Kids Reading Hour should rank #1"},
  {"key":"noah",   "name":"Noah Williams", "can_drive":false, "skills":["data entry","social media"],
   "availability":[{"day":"Tue","start":"10:00","end":"17:00"}],
   "bio":"I help with spreadsheets and posting updates on social media.",
   "role_in_tests":"Distractor: available Tuesday but a poor semantic fit for kids reading"}
]
```

## Shifts (4)

```json
[
  {"key":"S1", "title":"Saturday Delivery Run", "date":"2026-10-17", "start":"10:00", "end":"13:00",
   "required_count":2, "required_skills":["driving","heavy lifting"], "location":"Pantry Warehouse, Dock B",
   "description":"Drive food boxes to 12 homebound families; loading heavy boxes required.",
   "confirmed":["alex","grace"]},
  {"key":"S2", "title":"Community Dinner", "date":"2026-10-15", "start":"17:00", "end":"19:30",
   "required_count":4, "required_skills":["food handling","spanish"], "location":"Fellowship Hall",
   "description":"Serve a hot dinner; many guests are Spanish-speaking families.",
   "confirmed":["daniel"]},
  {"key":"S3", "title":"Kids Reading Hour", "date":"2026-10-13", "start":"15:30", "end":"17:00",
   "required_count":2, "required_skills":["kids activities"], "location":"Pantry Family Room",
   "description":"Read picture books with children while parents shop.",
   "confirmed":[]},
  {"key":"S4", "title":"Pantry Sorting", "date":"2026-10-18", "start":"09:00", "end":"12:00",
   "required_count":3, "required_skills":["food handling"], "location":"Pantry Warehouse",
   "description":"Sort and shelve donated canned goods.",
   "confirmed":[]}
]
```

## Past completed signups (for hours_28d)

Create past shifts between 2026-09-14 and 2026-10-10 as needed to reach these totals (`status: "completed"`):

```json
{"priya":18, "daniel":25, "jordan":2, "marcus":3, "sofia":4, "grace":6, "alex":5, "hannah":0}
```

## Scenarios (`scripts/run_scenarios.py`)

| ID | Setup / action | Expected (PASS criteria) |
|---|---|---|
| T1 | Cancel Alex on S1 → `run_agent("vacancy")` | 1 approval. **Jordan is rank 1.** Never includes Alex, Grace, Ethan, or Liam. If Priya appears, she ranks below Jordan and her reasons mention hours or fairness. |
| T2 | (after T1 reset) `custom_request`: "Need 2 more drivers for Saturday's delivery run" | Every candidate has `can_drive = true` and is available Sat 10–13. **Marcus, Ethan, and Liam are excluded.** |
| T3 | `coverage_scan` (7 days) with S1 full | Proposals cover S2, S3, and S4 (top 3 gaps); **S1 is not proposed.** |
| T4 | Approve T1 candidates, then every candidate declines | A re-trigger fires. The new approval **excludes the decliners**; if nobody fits, the summary says so and no IDs are invented. |
| T5 | S1 has 1 open slot, and two `sent` messages are accepted back-to-back | Exactly 1 new confirmed signup; the other message becomes `withdrawn`; S1 is `filled` (the transaction works). |
| T6 | Call `propose_action` directly with a random ObjectId | Returns an error string; no approval is created. |
| T7 | Check `is_available(liam, S1)` and `is_available(jordan, S1)` | `False` / `True` (timezone and partial-overlap logic). |
| T8 | `custom_request`: "Need a Spanish speaker for Thursday's dinner" | **Sofia is rank 1**; Daniel is excluded (already confirmed). |
| T9 | Recommended shifts for Maya | **S3 Kids Reading Hour is #1**; nothing on days she isn't available. |
| T10 | Dispatcher receives `'{"shift_id": '` (malformed JSON) | Recoverable error string, no exception. |

LLM-dependent scenarios (T1, T2, T3, T4, T8) are stochastic. Run each 3 times and report the pass rate. Deterministic ones (T5, T6, T7, T9, T10) must pass every time.
