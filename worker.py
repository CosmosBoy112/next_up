"""Event-driven agent trigger. Usage: python worker.py

Watches (one change stream over the database):
  - signups updates where status -> "cancelled"   => vacancy run
  - agent_triggers inserts (e.g. all candidates declined) => vacancy run
  - agent_triggers inserts of type "weather_scan" (e.g. demo storm switched on) => weather scan
Every WEATHER_SCAN_MINUTES it also checks the forecast for outdoor/driving shifts and runs
the agent for newly risky ones.
The resume token is stored in worker_state, and each event is claimed by a unique
key before running, so a restart neither misses nor double-processes events.
Falls back to polling every 3 s if change streams are unavailable.
"""

from __future__ import annotations

import time
import traceback
from datetime import timedelta

from pymongo.errors import DuplicateKeyError, OperationFailure, PyMongoError

from agent.harness import get_run_approvals, run_agent
from core import db, repo, weather

STATE_ID = "worker"
POLL_SECONDS = 3
WEATHER_SCAN_MINUTES = 30

PIPELINE = [{"$match": {"$or": [
    {"ns.coll": "signups", "operationType": "update",
     "updateDescription.updatedFields.status": "cancelled"},
    {"ns.coll": "agent_triggers", "operationType": "insert"},
]}}]


def log(msg: str) -> None:
    print(f"{repo.to_local(repo.now_utc()):%H:%M:%S} {msg}", flush=True)


# ---------- event handling ----------

def claim(event_key: str) -> bool:
    """Insert a marker with a unique _id; False if this event was already handled."""
    try:
        db.worker_state().insert_one({"_id": f"evt:{event_key}", "ts": repo.now_utc()})
        return True
    except DuplicateKeyError:
        return False


def handle_cancellation(signup: dict) -> None:
    if not claim(f"cancel:{signup['_id']}"):
        return
    shift = repo.get_shift(signup["shift_id"])
    volunteer = repo.get_volunteer(signup["volunteer_id"])
    who = volunteer["name"] if volunteer else signup["volunteer_id"]
    if shift is None or shift["start"] <= repo.now_utc():
        log(f"[event] cancellation by {who} on a past/missing shift, skipped")
        return
    log(f"[event] cancellation shift={shift['title']!r} volunteer={who}")
    _run({"shift_id": str(shift["_id"]), "cancelled_volunteer_id": str(signup["volunteer_id"]),
          "signup_id": str(signup["_id"])})


def handle_trigger(trigger: dict) -> None:
    if not claim(f"trigger:{trigger['_id']}"):
        return
    if trigger.get("type") == "weather_scan":
        weather_scan("requested")
        return
    shift = repo.get_shift(trigger["shift_id"])
    if shift is None:
        return
    log(f"[event] retry shift={shift['title']!r} (all candidates declined)")
    _run({"shift_id": str(shift["_id"]), "reason": "previous candidates declined"})


def _run(payload: dict) -> None:
    t0 = time.time()
    run_id = run_agent("vacancy", payload)
    approvals = [str(a["_id"]) for a in get_run_approvals(run_id)]
    log(f"   -> agent run {run_id} -> approval {approvals or 'none'} ({time.time() - t0:.1f}s)")


def weather_scan(reason: str = "scheduled") -> None:
    """Deterministic pre-filter, then one agent run for the shifts that newly need a plan."""
    try:
        risky = weather.risky_shifts(7)
    except weather.WeatherUnavailable as e:
        log(f"[weather] {e}")
        return
    demo = weather.get_demo()
    if not demo.get("enabled"):  # plans made from a simulated forecast no longer apply
        stale = db.approvals().update_many(
            {"kind": "weather_alert", "status": "pending", "weather.forecast.source": "demo"},
            {"$set": {"status": "rejected", "decided_at": repo.now_utc(),
                      "coordinator_note": "Simulated weather turned off; replaced by the live forecast."}})
        if stale.modified_count:
            log(f"[weather] cleared {stale.modified_count} simulated alert(s)")
    stamp = demo["updated_at"].isoformat() if demo.get("enabled") and demo.get("updated_at") else "live"
    today = f"{repo.to_local(repo.now_utc()):%Y-%m-%d}"
    fresh = []
    for s, w in risky:
        if db.approvals().find_one({"shift_id": s["_id"], "kind": "weather_alert", "status": "pending"}):
            continue
        plan = s.get("weather_plan")
        if plan and weather.SEVERITY_ORDER[plan["severity"]] >= weather.SEVERITY_ORDER[w["severity"]]:
            continue  # the coordinator already chose a plan for this level of risk
        # Once per shift, severity and day (or demo setting), even if no plan comes out of it.
        if claim(f"weather:{s['_id']}:{w['severity']}:{today}:{stamp}"):
            fresh.append(s)
    log(f"[weather] {reason} scan: {len(risky)} risky, {len(fresh)} new")
    if fresh:
        t0 = time.time()
        run_id = run_agent("weather_check", {"shift_ids": [str(s["_id"]) for s in fresh]})
        approvals = [str(a["_id"]) for a in get_run_approvals(run_id)]
        log(f"   -> agent run {run_id} -> weather plan(s) {approvals or 'none'} ({time.time() - t0:.1f}s)")


def handle_change(change: dict) -> None:
    coll = change["ns"]["coll"]
    doc = change.get("fullDocument")
    if doc is None:
        return
    if coll == "signups" and doc.get("status") == "cancelled":
        handle_cancellation(doc)
    elif coll == "agent_triggers":
        handle_trigger(doc)


def safe(fn, *args) -> None:
    try:
        fn(*args)
    except Exception:  # noqa: BLE001 - the worker must never die
        log("[error] handler failed:\n" + traceback.format_exc())


# ---------- change stream ----------

def watch_forever() -> None:
    state = db.worker_state().find_one({"_id": STATE_ID}) or {}
    token = state.get("resume_token")
    log(f"[worker] watching change stream ({'resuming' if token else 'fresh start'})")
    next_scan = time.time()  # scan the weather right away, then on a timer
    with db.get_db().watch(PIPELINE, full_document="updateLookup", resume_after=token,
                           max_await_time_ms=2000) as stream:
        while stream.alive:
            change = stream.try_next()
            if change is not None:
                safe(handle_change, change)
                db.worker_state().update_one(
                    {"_id": STATE_ID},
                    {"$set": {"resume_token": stream.resume_token, "updated_at": repo.now_utc()}},
                    upsert=True)
            if time.time() >= next_scan:
                safe(weather_scan)
                next_scan = time.time() + WEATHER_SCAN_MINUTES * 60


# ---------- polling fallback ----------

def poll_forever() -> None:
    log(f"[worker] WARNING: change streams unavailable; polling every {POLL_SECONDS}s")
    since = repo.now_utc() - timedelta(minutes=5)
    next_scan = time.time()
    while True:
        now = repo.now_utc()
        if time.time() >= next_scan:
            safe(weather_scan)
            next_scan = time.time() + WEATHER_SCAN_MINUTES * 60
        for s in db.signups().find({"status": "cancelled", "updated_at": {"$gte": since}}):
            safe(handle_cancellation, s)
        for t in db.agent_triggers().find({"created_at": {"$gte": since}}):
            safe(handle_trigger, t)
        since = now - timedelta(seconds=1)  # small overlap; claim() dedupes
        time.sleep(POLL_SECONDS)


def main() -> None:
    db.ensure_indexes()
    while True:
        try:
            watch_forever()
        except OperationFailure as e:
            if e.code in (40573, 136, 286):  # not a replica set / changeStream unsupported / history lost
                if e.code == 286:
                    log("[worker] resume token expired; starting fresh")
                    db.worker_state().update_one({"_id": STATE_ID}, {"$unset": {"resume_token": 1}})
                    continue
                poll_forever()
            log(f"[worker] change stream error {e.code}: {e}; retrying in 3s")
            time.sleep(3)
        except PyMongoError as e:
            log(f"[worker] mongo error: {e}; retrying in 3s")
            time.sleep(3)
        except KeyboardInterrupt:
            log("[worker] bye")
            return


if __name__ == "__main__":
    main()
