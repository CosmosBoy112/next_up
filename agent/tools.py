"""Agent tools: JSON schemas + implementations. Results are compact JSON strings.

The agent's only write tools are propose_action and log_note. Every other tool
is a read over core.repo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable

from bson import ObjectId
from bson.errors import InvalidId

from core import db, repo
from core.embeddings import embed

MAX_CANDIDATES = 3
MAX_DRAFT_WORDS = 60
FAIRNESS_PER_HOUR = 0.004  # 25h of recent work costs about 0.1 of match score
HIGH_LOAD_HOURS = 15
APPROVAL_KINDS = ("fill_vacancy", "coverage_invite", "custom_request")


@dataclass
class RunCtx:
    run_id: str
    trigger_type: str
    payload: dict
    seen_volunteer_ids: set[str] = field(default_factory=set)
    priorities: dict[str, float] = field(default_factory=dict)  # from find_candidates
    exclude_volunteer_ids: set[str] = field(default_factory=set)
    proposed_shift_ids: set[str] = field(default_factory=set)
    approval_ids: list[str] = field(default_factory=list)
    finished: bool = False
    finish_summary: str = ""


class ToolError(Exception):
    """Expected, model-facing error (bad id, failed validation...)."""


# ---------- serialization ----------

def fmt_dt(dt: datetime) -> str:
    return repo.to_local(dt).strftime("%a %Y-%m-%d %H:%M %Z")


def _default(o: Any) -> Any:
    if isinstance(o, ObjectId):
        return str(o)
    if isinstance(o, datetime):
        return fmt_dt(o)
    raise TypeError(f"not serializable: {type(o)}")


def to_json(obj: Any) -> str:
    return json.dumps(obj, default=_default, ensure_ascii=False, separators=(",", ":"))


def _oid(value: str, what: str) -> ObjectId:
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        raise ToolError(f"invalid {what} '{value}' (expected a 24-char hex id)")


def _load_shift(shift_id: str) -> dict:
    shift = repo.get_shift(_oid(shift_id, "shift_id"))
    if shift is None:
        raise ToolError(f"shift {shift_id} not found")
    return shift


def _excluded_for_shift(ctx: RunCtx, shift_id: ObjectId) -> set[str]:
    """Run-level exclusions + anyone who cancelled this shift or declined a request for it."""
    cancelled = db.signups().distinct("volunteer_id", {"shift_id": shift_id, "status": "cancelled"})
    declined = db.messages().distinct("to_volunteer_id", {"shift_id": shift_id, "status": "declined"})
    return ctx.exclude_volunteer_ids | {str(v) for v in cancelled + declined}


def _shift_brief(shift: dict) -> dict:
    return {"shift_id": shift["_id"], "title": shift["title"], "location": shift["location"],
            "start": shift["start"], "end": repo.to_local(shift["end"]).strftime("%H:%M"),
            "required_skills": shift.get("required_skills", []), "status": shift["status"]}


def _volunteer_brief(v: dict, hours: dict[str, float]) -> dict:
    return {"volunteer_id": v["_id"], "name": v["name"], "skills": v.get("skills", []),
            "can_drive": v.get("can_drive", False), "bio": v.get("bio", ""),
            "hours_28d": hours.get(str(v["_id"]), 0.0),
            "match_score": round(v.get("score", 0.0), 3)}


# ---------- implementations ----------

def get_shift(ctx: RunCtx, shift_id: str) -> str:
    shift = _load_shift(shift_id)
    confirmed = list(db.signups().find({"shift_id": shift["_id"], "status": "confirmed"}))
    names = [v["name"] for v in db.volunteers().find(
        {"_id": {"$in": [s["volunteer_id"] for s in confirmed]}}, {"name": 1})]
    out = _shift_brief(shift) | {
        "description": shift["description"], "required_count": shift["required_count"],
        "confirmed_count": len(confirmed), "open_slots": max(0, shift["required_count"] - len(confirmed)),
        "confirmed_volunteers": names,
    }
    return to_json(out)


def get_coverage_gaps(ctx: RunCtx, days: int = 7) -> str:
    gaps = repo.coverage_gaps(int(days))
    return to_json([_shift_brief(g) | {"required_count": g["required_count"],
                                       "confirmed_count": g["confirmed_count"],
                                       "open_slots": g["open_slots"]} for g in gaps])


def find_candidates(ctx: RunCtx, shift_id: str, need_text: str | None = None,
                    require_driver: bool = False, limit: int = 8) -> str:
    shift = _load_shift(shift_id)
    query = need_text or repo.shift_embed_text(shift["title"], shift["description"])
    vfilter: dict[str, Any] = {"org": shift["org"]}
    if require_driver:
        vfilter["can_drive"] = True
    ranked = repo.vector_search_volunteers(embed(query), vfilter, limit=100)
    taken = {str(s["volunteer_id"]) for s in db.signups().find(
        {"shift_id": shift["_id"], "status": "confirmed"}, {"volunteer_id": 1})}
    excluded = _excluded_for_shift(ctx, shift["_id"])
    eligible = [v for v in ranked
                if str(v["_id"]) not in taken
                and str(v["_id"]) not in excluded
                and repo.is_available(v, shift)]
    # Fairness: rank by fit minus a recent-workload penalty, then cut to `limit`,
    # so a lightly-used volunteer with slightly lower fit isn't dropped or buried.
    hours = repo.hours_28d([v["_id"] for v in eligible])
    for v in eligible:
        v["priority"] = v.get("score", 0.0) - FAIRNESS_PER_HOUR * hours[str(v["_id"])]
    eligible.sort(key=lambda v: v["priority"], reverse=True)
    pool = eligible[: max(1, min(int(limit), 15))]
    ctx.seen_volunteer_ids.update(str(v["_id"]) for v in pool)
    ctx.priorities.update({str(v["_id"]): v["priority"] for v in pool})
    min_hours = min((hours[str(v["_id"])] for v in pool), default=0.0)
    return to_json({
        "shift": _shift_brief(shift),
        "note": ("All candidates are available for the full shift window and not signed up. "
                 "Already sorted best-first by priority = match_score - "
                 f"{FAIRNESS_PER_HOUR} * hours_28d (fit, adjusted for recent workload)."),
        "candidates": [_volunteer_brief(v, hours) | {
            "priority": round(v["priority"], 3),
            "fairness_note": _fairness_note(hours[str(v["_id"])], min_hours),
        } for v in pool],
    })


def _fairness_note(h: float, min_hours: float) -> str:
    if h == min_hours:
        return f"lightest recent load among candidates ({h:g}h in 28 days)"
    if h >= HIGH_LOAD_HOURS:
        return f"high recent load ({h:g}h in 28 days); prefer others if fit is similar"
    return f"{h:g}h in 28 days"


def search_volunteers(ctx: RunCtx, query: str, require_driver: bool = False, limit: int = 8) -> str:
    vfilter = {"can_drive": True} if require_driver else None
    found = repo.vector_search_volunteers(embed(query), vfilter, limit=max(1, min(int(limit), 15)))
    hours = repo.hours_28d([v["_id"] for v in found])
    ctx.seen_volunteer_ids.update(str(v["_id"]) for v in found)
    return to_json({"note": "Availability NOT checked; use find_candidates for a specific shift.",
                    "volunteers": [_volunteer_brief(v, hours) for v in found]})


def search_shifts(ctx: RunCtx, query: str, days: int = 14) -> str:
    now = repo.now_utc()
    found = repo.vector_search_shifts(embed(query), {"status": {"$in": ["open", "filled"]}},
                                      limit=50)
    found = [s for s in found if now <= s["start"] < now + timedelta(days=int(days))]
    out = []
    for s in found[:6]:
        n = repo.confirmed_count(s["_id"])
        out.append(_shift_brief(s) | {"open_slots": max(0, s["required_count"] - n),
                                      "required_count": s["required_count"],
                                      "match_score": round(s.get("score", 0), 3)})
    return to_json(out)


def volunteer_history(ctx: RunCtx, volunteer_id: str) -> str:
    vid = _oid(volunteer_id, "volunteer_id")
    v = repo.get_volunteer(vid)
    if v is None:
        raise ToolError(f"volunteer {volunteer_id} not found")
    signups = list(db.signups().find({"volunteer_id": vid}).sort("created_at", -1).limit(5))
    shifts = {s["_id"]: s for s in db.shifts().find(
        {"_id": {"$in": [s["shift_id"] for s in signups]}}, {"title": 1, "start": 1})}
    ctx.seen_volunteer_ids.add(str(vid))
    return to_json({
        "volunteer_id": vid, "name": v["name"], "hours_28d": repo.hours_28d([vid])[str(vid)],
        "availability": v.get("availability", []),
        "recent_signups": [{"shift": shifts.get(s["shift_id"], {}).get("title"),
                            "start": shifts.get(s["shift_id"], {}).get("start"),
                            "status": s["status"]} for s in signups],
    })


def propose_action(ctx: RunCtx, kind: str, shift_id: str, summary: str,
                   candidates: list[dict]) -> str:
    if kind not in APPROVAL_KINDS:
        raise ToolError(f"kind must be one of {APPROVAL_KINDS}")
    shift = _load_shift(shift_id)
    sid = str(shift["_id"])
    if sid in ctx.proposed_shift_ids:
        raise ToolError("you already proposed for this shift in this run; call finish if done")
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= MAX_CANDIDATES:
        raise ToolError(f"candidates must be a list of 1-{MAX_CANDIDATES} items")

    taken = {str(s["volunteer_id"]) for s in db.signups().find(
        {"shift_id": shift["_id"], "status": "confirmed"}, {"volunteer_id": 1})}
    excluded = _excluded_for_shift(ctx, shift["_id"])
    ids: list[str] = []
    for c in candidates:
        vid = str(c.get("volunteer_id", ""))
        if vid not in ctx.seen_volunteer_ids:
            raise ToolError(f"volunteer_id {vid} was not returned by a search tool in this run; "
                            f"only propose volunteers from find_candidates/search results")
        if vid in taken:
            raise ToolError(f"volunteer {vid} is already confirmed for this shift")
        if vid in excluded:
            raise ToolError(f"volunteer {vid} must be excluded (cancelled or declined this shift)")
        if vid in ids:
            raise ToolError(f"duplicate volunteer {vid}")
        draft = str(c.get("draft_message", "")).strip()
        if not draft:
            raise ToolError(f"draft_message missing for {vid}")
        if len(draft.split()) > MAX_DRAFT_WORDS:
            raise ToolError(f"draft for {vid} has {len(draft.split())} words; keep it under "
                            f"{MAX_DRAFT_WORDS}")
        ids.append(vid)

    # Final order is deterministic: the LLM picks who and explains why; the
    # fairness-adjusted priority from find_candidates decides the ranking.
    picked = list(zip(ids, candidates))
    if all(vid in ctx.priorities for vid in ids):
        picked.sort(key=lambda p: ctx.priorities[p[0]], reverse=True)
    reordered = [vid for vid, _ in picked] != ids
    ids, candidates = [vid for vid, _ in picked], [c for _, c in picked]

    hours = repo.hours_28d(ids)
    trigger = {"type": ctx.trigger_type,
               "ref_id": str(ctx.payload.get("signup_id") or ctx.payload.get("shift_id") or sid)}
    if "text" in ctx.payload:
        trigger["text"] = ctx.payload["text"]
    doc = {
        "kind": kind, "shift_id": shift["_id"], "trigger": trigger, "agent_run_id": ctx.run_id,
        "summary": str(summary)[:500],
        "candidates": [{
            "volunteer_id": ObjectId(vid), "rank": i + 1,
            "reasons": [str(r) for r in (c.get("reasons") or [])][:5],
            "hours_28d": hours.get(vid, 0.0),
            "draft_message": str(c["draft_message"]).strip(),
            "selected": i < 2,
        } for i, (vid, c) in enumerate(zip(ids, candidates))],
        "status": "pending", "coordinator_note": "", "created_at": repo.now_utc(), "decided_at": None,
    }
    approval_id = str(db.approvals().insert_one(doc).inserted_id)
    ctx.proposed_shift_ids.add(sid)
    ctx.approval_ids.append(approval_id)
    note = "Queued for coordinator review. Nothing was sent."
    if reordered:
        note += " Candidate order was adjusted to the fairness-weighted priority."
    return to_json({"ok": True, "approval_id": approval_id, "note": note})


def log_note(ctx: RunCtx, text: str) -> str:
    return "ok"  # the harness already records the call (and its text) in agent_log


def finish(ctx: RunCtx, summary: str) -> str:
    ctx.finished = True
    ctx.finish_summary = str(summary)
    return "ok"


# ---------- schemas ----------

def _fn(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required,
                       "additionalProperties": False}}}


_ID = {"type": "string", "description": "24-char hex id"}
TOOL_SCHEMAS: list[dict] = [
    _fn("get_shift", "Get a shift with confirmed count, open slots, and who is confirmed.",
        {"shift_id": _ID}, ["shift_id"]),
    _fn("get_coverage_gaps", "List upcoming shifts with open slots, soonest first.",
        {"days": {"type": "integer", "description": "look-ahead window, default 7"}}, []),
    _fn("find_candidates",
        "Volunteers available for the whole shift window, not already signed up, ranked by "
        "semantic fit, with hours_28d (recent workload). Use this before proposing for a shift.",
        {"shift_id": _ID,
         "need_text": {"type": "string", "description": "optional: what is needed, e.g. 'driver who can lift boxes'"},
         "require_driver": {"type": "boolean", "description": "only volunteers who can drive"},
         "limit": {"type": "integer", "description": "default 8"}},
        ["shift_id"]),
    _fn("search_volunteers", "Free semantic search over volunteer bios (availability not checked).",
        {"query": {"type": "string"}, "require_driver": {"type": "boolean"},
         "limit": {"type": "integer"}}, ["query"]),
    _fn("search_shifts", "Semantic search over upcoming shifts (to resolve e.g. 'Saturday's delivery').",
        {"query": {"type": "string"}, "days": {"type": "integer", "description": "default 14"}},
        ["query"]),
    _fn("volunteer_history", "A volunteer's last 5 signups, availability, and hours_28d.",
        {"volunteer_id": _ID}, ["volunteer_id"]),
    _fn("propose_action",
        "Queue a proposal for the coordinator to approve. Nothing is sent until they approve. "
        "Candidates must come from find_candidates/search results in this run, ranked best first.",
        {"kind": {"type": "string", "enum": list(APPROVAL_KINDS)},
         "shift_id": _ID,
         "summary": {"type": "string", "description": "1-2 sentences for the coordinator"},
         "candidates": {"type": "array", "maxItems": MAX_CANDIDATES, "items": {
             "type": "object", "additionalProperties": False,
             "required": ["volunteer_id", "reasons", "draft_message"],
             "properties": {
                 "volunteer_id": _ID,
                 "reasons": {"type": "array", "items": {"type": "string"},
                             "description": "short concrete reasons"},
                 "draft_message": {"type": "string", "description": "under 60 words"}}}}},
        ["kind", "shift_id", "summary", "candidates"]),
    _fn("log_note", "Record a short note in the audit log.", {"text": {"type": "string"}}, ["text"]),
    _fn("finish", "End the run with a one-line summary.", {"summary": {"type": "string"}}, ["summary"]),
]

TOOLS: dict[str, Callable[..., str]] = {
    "get_shift": get_shift, "get_coverage_gaps": get_coverage_gaps,
    "find_candidates": find_candidates, "search_volunteers": search_volunteers,
    "search_shifts": search_shifts, "volunteer_history": volunteer_history,
    "propose_action": propose_action, "log_note": log_note, "finish": finish,
}


def dispatch(name: str, args_json: str, ctx: RunCtx) -> str:
    """Run a tool. Never raises: every problem becomes an 'error: ...' string."""
    fn = TOOLS.get(name)
    if fn is None:
        return f"error: unknown tool '{name}'. Available: {', '.join(TOOLS)}"
    try:
        args = json.loads(args_json) if args_json and args_json.strip() else {}
    except json.JSONDecodeError as e:
        return f"error: arguments are not valid JSON ({e.msg}). Send a JSON object."
    if not isinstance(args, dict):
        return "error: arguments must be a JSON object"
    try:
        return fn(ctx, **args)
    except TypeError as e:
        return f"error: bad arguments for {name}: {e}"
    except ToolError as e:
        return f"error: {e}"
    except Exception as e:  # noqa: BLE001 - keep the run alive
        return f"error: {name} failed: {type(e).__name__}: {str(e)[:200]}"
