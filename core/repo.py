"""Read/write helpers shared by the agent and the UI. All DB access goes here."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from bson import ObjectId
from pymongo.errors import OperationFailure

from core import db
from core.config import LOCAL_TZ
from core.embeddings import embed

TZ = ZoneInfo(LOCAL_TZ)
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# "vectorSearch" or "python-cosine"; set by the last vector search call (for reporting/UI)
LAST_SEARCH_BACKEND = ""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def oid(value: str | ObjectId) -> ObjectId:
    return value if isinstance(value, ObjectId) else ObjectId(str(value))


def shift_embed_text(title: str, description: str) -> str:
    return f"{title}. {description}"


# ---------- volunteers ----------

def get_volunteer(volunteer_id: str | ObjectId) -> dict | None:
    return db.volunteers().find_one({"_id": oid(volunteer_id)}, {"bio_embedding": 0})


def list_volunteers() -> list[dict]:
    return list(db.volunteers().find({}, {"bio_embedding": 0}).sort("name", 1))


def update_volunteer_profile(
    volunteer_id: str | ObjectId,
    *,
    skills: list[str],
    bio: str,
    can_drive: bool,
    availability: list[dict],
) -> None:
    db.volunteers().update_one(
        {"_id": oid(volunteer_id)},
        {"$set": {
            "skills": skills,
            "bio": bio,
            "bio_embedding": embed(bio),
            "can_drive": can_drive,
            "availability": availability,
        }},
    )


# ---------- shifts ----------

def get_shift(shift_id: str | ObjectId) -> dict | None:
    return db.shifts().find_one({"_id": oid(shift_id)}, {"description_embedding": 0})


def list_upcoming_shifts(days: int = 14) -> list[dict]:
    now = now_utc()
    return list(
        db.shifts()
        .find(
            {"start": {"$gte": now, "$lt": now + timedelta(days=days)},
             "status": {"$ne": "cancelled"}},
            {"description_embedding": 0},
        )
        .sort("start", 1)
    )


def confirmed_count(shift_id: str | ObjectId) -> int:
    return db.signups().count_documents({"shift_id": oid(shift_id), "status": "confirmed"})


def refresh_shift_status(shift_id: str | ObjectId) -> str:
    shift = db.shifts().find_one({"_id": oid(shift_id)}, {"required_count": 1, "status": 1})
    if shift is None or shift["status"] == "cancelled":
        return shift["status"] if shift else "missing"
    status = "filled" if confirmed_count(shift_id) >= shift["required_count"] else "open"
    db.shifts().update_one({"_id": shift["_id"]}, {"$set": {"status": status}})
    return status


# ---------- signups ----------

def signup(volunteer_id: str | ObjectId, shift_id: str | ObjectId, source: str = "self") -> ObjectId:
    """Create a confirmed signup. Raises ValueError if already signed up or full."""
    vid, sid = oid(volunteer_id), oid(shift_id)
    shift = db.shifts().find_one({"_id": sid}, {"required_count": 1, "status": 1})
    if shift is None or shift["status"] == "cancelled":
        raise ValueError("Shift not found or cancelled")
    if db.signups().find_one({"shift_id": sid, "volunteer_id": vid, "status": "confirmed"}):
        raise ValueError("Already signed up for this shift")
    if confirmed_count(sid) >= shift["required_count"]:
        raise ValueError("Shift is already full")
    now = now_utc()
    result = db.signups().insert_one({
        "shift_id": sid, "volunteer_id": vid, "status": "confirmed",
        "source": source, "created_at": now, "updated_at": now,
    })
    refresh_shift_status(sid)
    return result.inserted_id


def cancel_signup(signup_id: str | ObjectId) -> None:
    s = db.signups().find_one_and_update(
        {"_id": oid(signup_id), "status": "confirmed"},
        {"$set": {"status": "cancelled", "updated_at": now_utc()}},
    )
    if s is None:
        raise ValueError("Signup not found or not confirmed")
    refresh_shift_status(s["shift_id"])


def list_volunteer_signups(volunteer_id: str | ObjectId, status: str | None = None) -> list[dict]:
    query: dict[str, Any] = {"volunteer_id": oid(volunteer_id)}
    if status:
        query["status"] = status
    return list(db.signups().find(query).sort("created_at", -1))


# ---------- aggregations ----------

def hours_28d(volunteer_ids: list[str | ObjectId]) -> dict[str, float]:
    """Completed hours per volunteer over the last 28 days (fairness score)."""
    ids = [oid(v) for v in volunteer_ids]
    now = now_utc()
    pipeline = [
        {"$match": {"volunteer_id": {"$in": ids}, "status": "completed"}},
        {"$lookup": {"from": "shifts", "localField": "shift_id",
                     "foreignField": "_id", "as": "shift"}},
        {"$unwind": "$shift"},
        {"$match": {"shift.start": {"$gte": now - timedelta(days=28), "$lte": now}}},
        {"$group": {
            "_id": "$volunteer_id",
            "hours": {"$sum": {"$divide": [
                {"$subtract": ["$shift.end", "$shift.start"]}, 3_600_000]}},
        }},
    ]
    out = {str(i): 0.0 for i in ids}
    for row in db.signups().aggregate(pipeline):
        out[str(row["_id"])] = round(row["hours"], 1)
    return out


def coverage_gaps(days: int = 7) -> list[dict]:
    """Upcoming non-cancelled shifts with open slots, sorted by start."""
    now = now_utc()
    pipeline = [
        {"$match": {"start": {"$gte": now, "$lt": now + timedelta(days=days)},
                    "status": {"$ne": "cancelled"}}},
        {"$lookup": {
            "from": "signups",
            "let": {"sid": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$shift_id", "$$sid"]}, "status": "confirmed"}},
                {"$count": "n"},
            ],
            "as": "confirmed",
        }},
        {"$addFields": {"confirmed_count": {"$ifNull": [{"$first": "$confirmed.n"}, 0]}}},
        {"$addFields": {"open_slots": {"$subtract": ["$required_count", "$confirmed_count"]}}},
        {"$match": {"open_slots": {"$gt": 0}}},
        {"$sort": {"start": 1}},
        {"$project": {"description_embedding": 0, "confirmed": 0}},
    ]
    return list(db.shifts().aggregate(pipeline))


# ---------- availability ----------

def to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ)


def is_available(volunteer: dict, shift: dict) -> bool:
    """True if one availability block is on the shift's local weekday and covers it."""
    start, end = to_local(shift["start"]), to_local(shift["end"])
    if start.date() != end.date():
        return False
    day = WEEKDAYS[start.weekday()]
    s, e = start.strftime("%H:%M"), end.strftime("%H:%M")
    return any(
        b["day"] == day and b["start"] <= s and b["end"] >= e
        for b in volunteer.get("availability", [])
    )


# ---------- vector search (with in-Python fallback) ----------

def vector_search_volunteers(
    query_vec: list[float], filter: dict | None = None, limit: int = 8
) -> list[dict]:
    return _vector_search(db.volunteers(), db.VOLUNTEER_VS_INDEX, "bio_embedding",
                          query_vec, filter, limit)


def vector_search_shifts(
    query_vec: list[float], filter: dict | None = None, limit: int = 8
) -> list[dict]:
    return _vector_search(db.shifts(), db.SHIFT_VS_INDEX, "description_embedding",
                          query_vec, filter, limit)


def _vector_search(coll, index: str, path: str, query_vec: list[float],
                   filter: dict | None, limit: int) -> list[dict]:
    global LAST_SEARCH_BACKEND
    stage: dict[str, Any] = {
        "index": index, "path": path, "queryVector": query_vec,
        "numCandidates": max(100, limit * 20), "limit": limit,
    }
    if filter:
        stage["filter"] = filter
    try:
        results = list(coll.aggregate([
            {"$vectorSearch": stage},
            {"$project": {path: 0, "score": {"$meta": "vectorSearchScore"}}},
        ]))
        # An index that is still building returns nothing instead of erroring.
        if results or coll.count_documents(filter or {}, limit=1) == 0:
            LAST_SEARCH_BACKEND = "vectorSearch"
            return results
    except OperationFailure:
        pass
    LAST_SEARCH_BACKEND = "python-cosine"
    return _cosine_fallback(coll, path, query_vec, filter, limit)


def _cosine_fallback(coll, path: str, query_vec: list[float],
                     filter: dict | None, limit: int) -> list[dict]:
    scored = []
    for doc in coll.find(filter or {}):
        vec = doc.pop(path, None)
        if not vec:
            continue
        # Embeddings are normalized, so dot product == cosine. Map to Atlas' (1+cos)/2.
        cos = sum(a * b for a, b in zip(query_vec, vec))
        doc["score"] = (1 + cos) / 2
        scored.append(doc)
    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored[:limit]


# ---------- UI read helpers ----------

def get_signup(signup_id: str | ObjectId) -> dict | None:
    return db.signups().find_one({"_id": oid(signup_id)})


def shift_board(days: int = 14) -> list[dict]:
    """Upcoming shifts with confirmed_count/open_slots (aggregation), sorted by start."""
    now = now_utc()
    pipeline = [
        {"$match": {"start": {"$gte": now, "$lt": now + timedelta(days=days)}}},
        {"$lookup": {"from": "signups", "localField": "_id", "foreignField": "shift_id",
                     "pipeline": [{"$match": {"status": "confirmed"}}], "as": "confirmed"}},
        {"$addFields": {"confirmed_count": {"$size": "$confirmed"}}},
        {"$addFields": {"open_slots": {"$max": [0, {"$subtract": ["$required_count",
                                                                 "$confirmed_count"]}]}}},
        {"$sort": {"start": 1}},
        {"$project": {"description_embedding": 0, "confirmed": 0}},
    ]
    return list(db.shifts().aggregate(pipeline))


def shift_crews(shift_ids: list[ObjectId]) -> dict[ObjectId, list[str]]:
    """shift_id -> names of confirmed volunteers."""
    pipeline = [
        {"$match": {"shift_id": {"$in": shift_ids}, "status": "confirmed"}},
        {"$lookup": {"from": "volunteers", "localField": "volunteer_id", "foreignField": "_id",
                     "pipeline": [{"$project": {"name": 1}}], "as": "v"}},
        {"$unwind": "$v"},
        {"$sort": {"v.name": 1}},
        {"$group": {"_id": "$shift_id", "names": {"$push": "$v.name"}}},
    ]
    return {r["_id"]: r["names"] for r in db.signups().aggregate(pipeline)}


def shift_roster(shift_id: str | ObjectId) -> list[dict]:
    """Confirmed signups for a shift, each with its volunteer attached (sorted by name)."""
    rows = list(db.signups().aggregate([
        {"$match": {"shift_id": oid(shift_id), "status": "confirmed"}},
        {"$lookup": {"from": "volunteers", "localField": "volunteer_id", "foreignField": "_id",
                     "pipeline": [{"$project": {"bio_embedding": 0, "availability": 0}}],
                     "as": "volunteer"}},
        {"$unwind": "$volunteer"},
    ]))
    return sorted(rows, key=lambda r: r["volunteer"]["name"])


def shift_requests(shift_id: str | ObjectId) -> list[dict]:
    """Requests sent for a shift (newest first), each with the recipient's name."""
    msgs = list(db.messages().find({"shift_id": oid(shift_id), "kind": {"$ne": "notice"}})
                .sort("sent_at", -1))
    names = volunteer_names([m["to_volunteer_id"] for m in msgs])
    return [m | {"name": names.get(m["to_volunteer_id"], "Unknown")} for m in msgs]


def dashboard_metrics() -> dict:
    """Open slots / fill rate (next 7 days), pending approvals, agent runs today."""
    week = [s for s in shift_board(7) if s["status"] != "cancelled"]
    required = sum(s["required_count"] for s in week)
    confirmed = sum(min(s["confirmed_count"], s["required_count"]) for s in week)
    midnight = to_local(now_utc()).replace(hour=0, minute=0, second=0, microsecond=0)
    runs = list(db.agent_log().aggregate([
        {"$match": {"ts": {"$gte": midnight.astimezone(timezone.utc)}}},
        {"$group": {"_id": "$run_id"}},
        {"$count": "n"},
    ]))
    return {
        "open_slots_7d": required - confirmed,
        "fill_rate_7d": (confirmed / required) if required else 1.0,
        "pending_approvals": db.approvals().count_documents({"status": "pending"}),
        "agent_runs_today": runs[0]["n"] if runs else 0,
    }


def my_upcoming_shifts(volunteer_id: str | ObjectId) -> list[dict]:
    """[(signup, shift)] for confirmed upcoming shifts."""
    signups = list(db.signups().find({"volunteer_id": oid(volunteer_id), "status": "confirmed"}))
    shifts = {s["_id"]: s for s in db.shifts().find(
        {"_id": {"$in": [s["shift_id"] for s in signups]}, "start": {"$gte": now_utc()}},
        {"description_embedding": 0})}
    rows = [{"signup": s, "shift": shifts[s["shift_id"]]} for s in signups if s["shift_id"] in shifts]
    return sorted(rows, key=lambda r: r["shift"]["start"])


def completed_hours(volunteer_id: str | ObjectId) -> float:
    rows = list(db.signups().aggregate([
        {"$match": {"volunteer_id": oid(volunteer_id), "status": "completed"}},
        {"$lookup": {"from": "shifts", "localField": "shift_id", "foreignField": "_id",
                     "as": "shift"}},
        {"$unwind": "$shift"},
        {"$group": {"_id": None, "hours": {"$sum": {"$divide": [
            {"$subtract": ["$shift.end", "$shift.start"]}, 3_600_000]}}}},
    ]))
    return round(rows[0]["hours"], 1) if rows else 0.0


def recommended_shifts(volunteer_id: str | ObjectId, limit: int = 5) -> list[dict]:
    """Open upcoming shifts ranked by bio-vs-description similarity, filtered by availability."""
    v = db.volunteers().find_one({"_id": oid(volunteer_id)})
    if not v or not v.get("bio_embedding"):
        return []
    mine = {s["shift_id"] for s in db.signups().find(
        {"volunteer_id": v["_id"], "status": "confirmed"}, {"shift_id": 1})}
    now = now_utc()
    found = vector_search_shifts(v["bio_embedding"], {"status": "open"}, limit=50)
    return [s for s in found
            if s["start"] >= now and s["_id"] not in mine and is_available(v, s)][:limit]


def inbox(volunteer_id: str | ObjectId) -> list[dict]:
    """Messages for a volunteer (newest first) with their shift attached."""
    msgs = list(db.messages().find({"to_volunteer_id": oid(volunteer_id)}).sort("sent_at", -1))
    shifts = {s["_id"]: s for s in db.shifts().find(
        {"_id": {"$in": [m["shift_id"] for m in msgs]}}, {"description_embedding": 0})}
    return [m | {"shift": shifts.get(m["shift_id"])} for m in msgs]


def pending_approvals() -> list[dict]:
    return list(db.approvals().find({"status": "pending"}).sort("created_at", -1))


def volunteer_names(ids: list[ObjectId]) -> dict[ObjectId, str]:
    return {v["_id"]: v["name"] for v in db.volunteers().find({"_id": {"$in": ids}}, {"name": 1})}


def recent_agent_log(limit: int = 30) -> list[dict]:
    return list(db.agent_log().find({}, {"_id": 0}).sort("ts", -1).limit(limit))


def agent_log_since(trigger: str, since: datetime) -> list[dict]:
    return list(db.agent_log().find({"trigger": trigger, "ts": {"$gte": since}},
                                    {"_id": 0}).sort([("ts", 1), ("step", 1)]))
