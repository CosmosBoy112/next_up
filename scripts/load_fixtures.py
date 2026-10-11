"""Hand-crafted, deterministic fixture for verifying agent behavior (md/06_TEST_FIXTURES.md).

Every volunteer exists to test one rule. Loads into a SEPARATE database
(default: volunteerops_scenarios) so the demo data is never touched.

Usage: python scripts/load_fixtures.py [--db NAME]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `python scripts/x.py`

DEFAULT_DB = "volunteerops_scenarios"
# Always target the scenario DB (set before core.config loads .env, which never overrides).
os.environ["DB_NAME"] = (sys.argv[sys.argv.index("--db") + 1] if "--db" in sys.argv
                         else os.environ.get("SCENARIO_DB", DEFAULT_DB))

import time  # noqa: E402
from datetime import date, datetime, time as dtime, timedelta, timezone  # noqa: E402

from bson import ObjectId  # noqa: E402

from core import db, repo  # noqa: E402
from core.embeddings import embed_many  # noqa: E402
from core.repo import TZ  # noqa: E402

ORG = "Valley Community Pantry"
FIXTURE_TODAY = date(2026, 10, 11)

VOLUNTEERS = [
    ("alex", "Alex Rivera", True, ["driving", "heavy lifting"], [("Sat", "09:00", "14:00")],
     "I drive my pickup for pantry deliveries and can lift heavy boxes."),
    ("jordan", "Jordan Kim", True, ["driving", "heavy lifting"], [("Sat", "08:00", "15:00")],
     "Weekend driver with a minivan, happy to load and unload deliveries."),
    ("priya", "Priya Nair", True, ["driving", "food handling"], [("Sat", "09:00", "14:00")],
     "I've been doing delivery runs most weekends this month."),
    ("marcus", "Marcus Chen", False, ["heavy lifting", "event setup"], [("Sat", "09:00", "14:00")],
     "Strong back, no car. Great at moving tables and boxes."),
    ("ethan", "Ethan Brooks", True, ["driving"], [("Sun", "08:00", "13:00")],
     "I can drive deliveries on Sunday mornings."),
    ("liam", "Liam O'Connor", True, ["driving", "heavy lifting"], [("Sat", "11:00", "14:00")],
     "Driver available late Saturday mornings."),
    ("grace", "Grace Okafor", True, ["driving"], [("Sat", "09:00", "14:00")],
     "Regular Saturday delivery driver."),
    ("sofia", "Sofia Alvarez", False, ["spanish", "food handling"], [("Thu", "16:00", "20:00")],
     "Bilingual English/Spanish, I love serving at community dinners."),
    ("hannah", "Hannah Lee", False, ["first aid", "event setup"], [("Thu", "15:00", "21:00")],
     "New volunteer, certified in first aid, can help set up events."),
    ("daniel", "Daniel Park", False, ["food handling", "heavy lifting"], [("Thu", "16:00", "20:00")],
     "Kitchen helper for dinners, I also do heavy lifting."),
    ("maya", "Maya Patel", False, ["kids activities"], [("Tue", "15:00", "18:00")],
     "Elementary education major who loves reading stories to kids."),
    ("noah", "Noah Williams", False, ["data entry", "social media"], [("Tue", "10:00", "17:00")],
     "I help with spreadsheets and posting updates on social media."),
]

# key, title, date, start, end, required, skills, location, description, confirmed
SHIFTS = [
    ("S1", "Saturday Delivery Run", date(2026, 10, 17), "10:00", "13:00", 2,
     ["driving", "heavy lifting"], "Pantry Warehouse, Dock B",
     "Drive food boxes to 12 homebound families; loading heavy boxes required.", ["alex", "grace"]),
    ("S2", "Community Dinner", date(2026, 10, 15), "17:00", "19:30", 4,
     ["food handling", "spanish"], "Fellowship Hall",
     "Serve a hot dinner; many guests are Spanish-speaking families.", ["daniel"]),
    ("S3", "Kids Reading Hour", date(2026, 10, 13), "15:30", "17:00", 2,
     ["kids activities"], "Pantry Family Room",
     "Read picture books with children while parents shop.", []),
    ("S4", "Pantry Sorting", date(2026, 10, 18), "09:00", "12:00", 3,
     ["food handling"], "Pantry Warehouse",
     "Sort and shelve donated canned goods.", []),
]

PAST_HOURS = {"priya": 18, "daniel": 25, "jordan": 2, "marcus": 3, "sofia": 4,
              "grace": 6, "alex": 5, "hannah": 0}
PAST_FIRST_DAY = date(2026, 9, 14)  # past shifts span 2026-09-14 .. 2026-10-10


def at(d: date, hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime.combine(d, dtime(h, m), tzinfo=TZ).astimezone(timezone.utc)


def build() -> dict:
    now = datetime.now(timezone.utc)
    ids = {key: ObjectId() for key, *_ in VOLUNTEERS}
    vols = [{
        "_id": ids[key], "key": key, "name": name, "email": f"{key}@example.org", "org": ORG,
        "skills": skills, "bio": bio, "can_drive": drive,
        "availability": [{"day": d, "start": s, "end": e} for d, s, e in avail], "created_at": now,
    } for key, name, drive, skills, avail, bio in VOLUNTEERS]

    shifts, signups, shift_ids = [], [], {}
    for key, title, d, s, e, req, skills, loc, desc, confirmed in SHIFTS:
        sid = shift_ids[key] = ObjectId()
        shifts.append({"_id": sid, "key": key, "title": title, "org": ORG, "location": loc,
                       "start": at(d, s), "end": at(d, e), "required_count": req,
                       "required_skills": skills, "description": desc,
                       "status": "filled" if len(confirmed) >= req else "open", "created_at": now})
        signups += [{"_id": ObjectId(), "shift_id": sid, "volunteer_id": ids[v], "status": "confirmed",
                     "source": "self", "created_at": now, "updated_at": now} for v in confirmed]

    # Past history: chunks of <=5h, one single-person past shift per chunk.
    day = 0
    for key, total in PAST_HOURS.items():
        left = total
        while left > 0:
            hours = min(5, left)
            d = PAST_FIRST_DAY + timedelta(days=day % 27)
            day += 1
            sid = ObjectId()
            shifts.append({"_id": sid, "key": f"past-{key}-{day}", "title": "Pantry Sorting (past)",
                           "org": ORG, "location": "Pantry Warehouse", "start": at(d, "09:00"),
                           "end": at(d, f"{9 + hours:02d}:00"), "required_count": 1,
                           "required_skills": ["food handling"],
                           "description": "Sort and shelve donated canned goods.",
                           "status": "filled", "created_at": now})
            signups.append({"_id": ObjectId(), "shift_id": sid, "volunteer_id": ids[key],
                            "status": "completed", "source": "self", "created_at": now,
                            "updated_at": now})
            left -= hours
    return {"volunteers": vols, "shifts": shifts, "signups": signups}


def load(wait_for_index: bool = True) -> dict:
    """Wipe the scenario DB, insert the fixture, and wait until vector search sees it."""
    database = db.get_db()
    if not any(tag in database.name for tag in ("scenario", "test", "fixture")):
        raise SystemExit(f"Refusing to wipe '{database.name}': fixture DB names must contain "
                         "'scenario', 'test' or 'fixture'.")
    for name in ("volunteers", "shifts", "signups", "approvals", "messages",
                 "agent_log", "agent_triggers", "worker_state"):
        database[name].delete_many({})
    data = build()
    for v, vec in zip(data["volunteers"], embed_many([v["bio"] for v in data["volunteers"]])):
        v["bio_embedding"] = vec
    texts = [repo.shift_embed_text(s["title"], s["description"]) for s in data["shifts"]]
    for s, vec in zip(data["shifts"], embed_many(texts)):
        s["description_embedding"] = vec
    for name in ("volunteers", "shifts", "signups"):
        db.col(name).insert_many(data[name])
    warnings = db.ensure_indexes()
    if warnings:  # e.g. M0 search-index quota: queries use the in-Python cosine fallback
        repo.LAST_SEARCH_BACKEND = "python-cosine"
    elif wait_for_index:
        wait_for_vector_sync(len(data["volunteers"]))
    return {"warnings": warnings}


def wait_for_vector_sync(n_volunteers: int, timeout: float = 120) -> str:
    """Block until $vectorSearch returns every volunteer (index READY and synced)."""
    probe = embed_many(["volunteer"])[0]
    t0 = time.time()
    while time.time() - t0 < timeout:
        found = repo.vector_search_volunteers(probe, None, limit=50)
        if repo.LAST_SEARCH_BACKEND == "vectorSearch" and len(found) == n_volunteers:
            return "vectorSearch"
        time.sleep(2)
    return repo.LAST_SEARCH_BACKEND or "python-cosine"


# ---------- lookups used by run_scenarios ----------

def vid(key: str) -> ObjectId:
    return db.volunteers().find_one({"key": key}, {"_id": 1})["_id"]


def sid(key: str) -> ObjectId:
    return db.shifts().find_one({"key": key}, {"_id": 1})["_id"]


def key_of(volunteer_id) -> str:
    v = db.volunteers().find_one({"_id": volunteer_id}, {"key": 1})
    return v["key"] if v else f"UNKNOWN({volunteer_id})"


def main() -> None:
    t0 = time.time()
    info = load()
    for w in info["warnings"]:
        print("⚠️ ", w)
    print(f"Loaded fixture into db={db.get_db().name} in {time.time() - t0:.1f}s: "
          f"{db.volunteers().count_documents({})} volunteers, "
          f"{db.shifts().count_documents({'key': {'$regex': '^S'}})} shifts "
          f"(+{db.shifts().count_documents({'key': {'$regex': '^past'}})} past), "
          f"{db.signups().count_documents({})} signups | search={repo.LAST_SEARCH_BACKEND}")
    hours = repo.hours_28d([vid(k) for k in PAST_HOURS])
    print("hours_28d:", {k: hours[str(vid(k))] for k in PAST_HOURS})


if __name__ == "__main__":
    main()
