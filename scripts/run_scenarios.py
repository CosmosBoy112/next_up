"""Scenario tests T1-T10 from md/06_TEST_FIXTURES.md against the real LLM.

Runs in the scenario DB (default volunteerops_scenarios), reloading the fixture
before every run. LLM scenarios run N times (default 3) and report a pass rate;
deterministic scenarios must pass every time.

Usage:
  python scripts/run_scenarios.py                # all, 3 runs per LLM scenario
  python scripts/run_scenarios.py --runs 1 --only T1,T5
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import load_fixtures as fx  # noqa: E402  (sets DB_NAME to the scenario DB)

from bson import ObjectId  # noqa: E402

import agent.harness as harness  # noqa: E402
from agent.llm import LLM  # noqa: E402
from agent.tools import RunCtx, dispatch  # noqa: E402
from core import actions, db, repo  # noqa: E402
from worker import handle_trigger  # noqa: E402

FAIRNESS_WORDS = re.compile(r"\bhours?\b|\d+\s*h\b|fair|load|workload|recent", re.I)


# ---------- measurement ----------

class CountingLLM(LLM):
    """Real LLM that counts calls (per scenario run)."""

    calls = 0

    def chat(self, messages, tools):
        CountingLLM.calls += 1
        return super().chat(messages, tools)


@dataclass
class RunResult:
    ok: bool
    why: str = ""
    seconds: float = 0.0
    llm_calls: int = 0
    tool_calls: int = 0
    tool_errors: int = 0


@dataclass
class Scenario:
    id: str
    title: str
    fn: Callable[[], tuple[bool, str, list[str]]]  # -> (ok, why, run_ids)
    llm: bool
    results: list[RunResult] = field(default_factory=list)


def measure(fn) -> RunResult:
    fx.load()
    CountingLLM.calls = 0
    t0 = time.time()
    try:
        ok, why, run_ids = fn()
    except Exception as e:  # noqa: BLE001 - a crash is a failure, keep going
        ok, why, run_ids = False, f"crashed: {type(e).__name__}: {e}", []
    seconds = time.time() - t0
    log = [e for r in run_ids for e in harness.get_run_log(r)]
    return RunResult(
        ok=ok, why=why, seconds=seconds, llm_calls=CountingLLM.calls,
        tool_calls=sum(e["kind"] == "tool_call" for e in log),
        tool_errors=sum(e["kind"] == "tool_result" and e["content"].startswith("error") for e in log),
    )


# ---------- helpers ----------

def cancel(volunteer_key: str, shift_key: str) -> dict:
    s = db.signups().find_one({"shift_id": fx.sid(shift_key), "volunteer_id": fx.vid(volunteer_key),
                               "status": "confirmed"})
    repo.cancel_signup(s["_id"])
    return s


def approvals_of(run_id: str) -> list[dict]:
    return harness.get_run_approvals(run_id)


def ranked_keys(approval: dict) -> list[str]:
    return [fx.key_of(c["volunteer_id"]) for c in sorted(approval["candidates"], key=lambda c: c["rank"])]


def fmt(approvals: list[dict]) -> str:
    return "; ".join(f"{fx.key_of_shift(a['shift_id'])}:{ranked_keys(a)}" for a in approvals) or "none"


def final_text(run_id: str) -> str:
    return next((e["content"] for e in reversed(harness.get_run_log(run_id)) if e["kind"] == "final"), "")


# ---------- LLM scenarios ----------

def t1() -> tuple[bool, str, list[str]]:
    s = cancel("alex", "S1")
    run = harness.run_agent("vacancy", {"shift_id": str(fx.sid("S1")),
                                        "cancelled_volunteer_id": str(fx.vid("alex")),
                                        "signup_id": str(s["_id"])})
    aps = approvals_of(run)
    if len(aps) != 1:
        return False, f"expected 1 approval, got {len(aps)}", [run]
    keys = ranked_keys(aps[0])
    bad = {"alex", "grace", "ethan", "liam"} & set(keys)
    if bad:
        return False, f"included {sorted(bad)}: {keys}", [run]
    if not keys or keys[0] != "jordan":
        return False, f"jordan not rank 1: {keys}", [run]
    if "priya" in keys:
        c = next(c for c in aps[0]["candidates"] if fx.key_of(c["volunteer_id"]) == "priya")
        if not any(FAIRNESS_WORDS.search(r) for r in c["reasons"]):
            return False, f"priya reasons lack fairness: {c['reasons']}", [run]
    return True, f"{keys}", [run]


def _drivers_ok(aps: list[dict], shift_key: str) -> tuple[bool, str]:
    shift = repo.get_shift(fx.sid(shift_key))
    for a in aps:
        for c in a["candidates"]:
            v = repo.get_volunteer(c["volunteer_id"])
            k = fx.key_of(c["volunteer_id"])
            if not v["can_drive"]:
                return False, f"non-driver {k}"
            if not repo.is_available(v, shift):
                return False, f"{k} not available"
            if k in {"marcus", "ethan", "liam"}:
                return False, f"excluded {k} proposed"
    return True, ""


def t2() -> tuple[bool, str, list[str]]:
    run = harness.run_agent("custom_request", {"text": "Need 2 more drivers for Saturday's delivery run"})
    aps = approvals_of(run)
    if not aps:
        return False, f"no proposal ({final_text(run)[:120]})", [run]
    ok, why = _drivers_ok(aps, "S1")
    return ok, why or fmt(aps), [run]


def t3() -> tuple[bool, str, list[str]]:
    run = harness.run_agent("coverage_scan", {"days": 7})
    aps = approvals_of(run)
    shifts = {fx.key_of_shift(a["shift_id"]) for a in aps}
    if "S1" in shifts:
        return False, f"proposed full S1: {sorted(shifts)}", [run]
    missing = {"S2", "S3", "S4"} - shifts
    if missing:
        return False, f"missing {sorted(missing)}; got {sorted(shifts)}", [run]
    return True, fmt(aps), [run]


def t4() -> tuple[bool, str, list[str]]:
    s = cancel("alex", "S1")
    run1 = harness.run_agent("vacancy", {"shift_id": str(fx.sid("S1")),
                                         "cancelled_volunteer_id": str(fx.vid("alex")),
                                         "signup_id": str(s["_id"])})
    aps = approvals_of(run1)
    if not aps:
        return False, "first run made no approval", [run1]
    a = aps[0]
    actions.approve(a["_id"], [str(c["volunteer_id"]) for c in a["candidates"]])
    decliners = set()
    for m in db.messages().find({"approval_id": a["_id"], "status": "sent"}):
        decliners.add(fx.key_of(m["to_volunteer_id"]))
        actions.decline_message(m["_id"])
    trig = db.agent_triggers().find_one({"approval_id": a["_id"]})
    if trig is None:
        return False, "no re-trigger inserted after all declined", [run1]
    before = {x["_id"] for x in db.approvals().find({}, {"_id": 1})}
    handle_trigger(trig)  # what worker.py does on the agent_triggers insert
    new = list(db.approvals().find({"_id": {"$nin": list(before)}}))
    run2 = new[0]["agent_run_id"] if new else _latest_run_id()
    known = {fx.key_of(v["_id"]) for v in db.volunteers().find({}, {"_id": 1})}
    for b in new:
        keys = ranked_keys(b)
        if set(keys) & decliners:
            return False, f"re-proposed decliners {sorted(set(keys) & decliners)}", [run1, run2]
        if not set(keys) <= known:
            return False, f"unknown ids {keys}", [run1, run2]
        if {"alex", "grace", "ethan", "liam"} & set(keys):
            return False, f"invalid candidate in {keys}", [run1, run2]
    if not new and not final_text(run2):
        return False, "no proposal and no explanation", [run1, run2]
    return True, (f"declined {sorted(decliners)} -> " + (fmt(new) if new else
                  f"no fit: {final_text(run2)[:80]}")), [run1, run2]


def _latest_run_id() -> str:
    e = db.agent_log().find_one({}, sort=[("ts", -1)])
    return e["run_id"] if e else ""


def t8() -> tuple[bool, str, list[str]]:
    run = harness.run_agent("custom_request", {"text": "Need a Spanish speaker for Thursday's dinner"})
    aps = approvals_of(run)
    if not aps:
        return False, f"no proposal ({final_text(run)[:120]})", [run]
    keys = ranked_keys(aps[0])
    if "daniel" in keys:
        return False, f"daniel (already confirmed) proposed: {keys}", [run]
    if keys[0] != "sofia":
        return False, f"sofia not rank 1: {keys}", [run]
    return True, fmt(aps), [run]


# ---------- deterministic scenarios ----------

def t5() -> tuple[bool, str, list[str]]:
    cancel("alex", "S1")  # S1 now has 1 open slot
    s1 = fx.sid("S1")
    approval = db.approvals().insert_one({
        "kind": "fill_vacancy", "shift_id": s1, "trigger": {"type": "vacancy", "ref_id": str(s1)},
        "agent_run_id": "scenario-t5", "summary": "t5", "status": "pending",
        "candidates": [{"volunteer_id": fx.vid(k), "rank": i + 1, "reasons": [], "hours_28d": 0,
                        "draft_message": "Hi!", "selected": True} for i, k in enumerate(["jordan", "priya"])],
        "coordinator_note": "", "created_at": repo.now_utc(), "decided_at": None,
    }).inserted_id
    actions.approve(approval, [str(fx.vid("jordan")), str(fx.vid("priya"))])
    msgs = [m["_id"] for m in db.messages().find({"approval_id": approval})]
    before = repo.confirmed_count(s1)
    results: list = []
    threads = [threading.Thread(target=lambda m=m: results.append(actions.accept_message(m))) for m in msgs]
    [t.start() for t in threads]
    [t.join() for t in threads]
    statuses = sorted(m["status"] for m in db.messages().find({"approval_id": approval}))
    added = repo.confirmed_count(s1) - before
    ok = (added == 1 and statuses == ["accepted", "withdrawn"]
          and repo.get_shift(s1)["status"] == "filled")
    return ok, f"+{added} confirmed, messages={statuses}, S1={repo.get_shift(s1)['status']}", []


def t6() -> tuple[bool, str, list[str]]:
    ctx = RunCtx(run_id="scenario-t6", trigger_type="vacancy", payload={})
    n = db.approvals().count_documents({})
    out = dispatch("propose_action", json.dumps({
        "kind": "fill_vacancy", "shift_id": str(fx.sid("S1")), "summary": "x",
        "candidates": [{"volunteer_id": str(ObjectId()), "reasons": ["x"], "draft_message": "hi"}],
    }), ctx)
    ok = out.startswith("error") and db.approvals().count_documents({}) == n
    return ok, out[:90], []


def t7() -> tuple[bool, str, list[str]]:
    shift = repo.get_shift(fx.sid("S1"))
    liam = repo.is_available(repo.get_volunteer(fx.vid("liam")), shift)
    jordan = repo.is_available(repo.get_volunteer(fx.vid("jordan")), shift)
    return (not liam and jordan), f"liam={liam} jordan={jordan}", []


def t9() -> tuple[bool, str, list[str]]:
    maya = repo.get_volunteer(fx.vid("maya"))
    recs = repo.recommended_shifts(fx.vid("maya"))
    keys = [fx.key_of_shift(s["_id"]) for s in recs]
    ok = bool(keys) and keys[0] == "S3" and all(repo.is_available(maya, s) for s in recs)
    return ok, f"{keys}", []


def t10() -> tuple[bool, str, list[str]]:
    ctx = RunCtx(run_id="scenario-t10", trigger_type="vacancy", payload={})
    try:
        out = dispatch("get_shift", '{"shift_id": ', ctx)
    except Exception as e:  # noqa: BLE001
        return False, f"raised {type(e).__name__}", []
    return out.startswith("error"), out[:80], []


SCENARIOS = [
    Scenario("T1", "vacancy: Jordan #1, exclusions, fairness", t1, llm=True),
    Scenario("T2", "custom: drivers only", t2, llm=True),
    Scenario("T3", "coverage scan: S2-S4, not S1", t3, llm=True),
    Scenario("T4", "all decline -> re-trigger excludes decliners", t4, llm=True),
    Scenario("T5", "transaction: 2 accepts, 1 slot", t5, llm=False),
    Scenario("T6", "hallucinated id blocked", t6, llm=False),
    Scenario("T7", "availability: partial overlap", t7, llm=False),
    Scenario("T8", "custom: Spanish speaker, Sofia #1", t8, llm=True),
    Scenario("T9", "recommendations: Kids Reading Hour #1", t9, llm=False),
    Scenario("T10", "malformed JSON -> error string", t10, llm=False),
]


def _key_of_shift(shift_id) -> str:
    s = db.shifts().find_one({"_id": shift_id}, {"key": 1})
    return s["key"] if s else f"UNKNOWN({shift_id})"


fx.key_of_shift = _key_of_shift


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3, help="runs per LLM scenario")
    ap.add_argument("--only", default="", help="comma-separated ids, e.g. T1,T5")
    ap.add_argument("--db", default=None, help="scenario DB name (default volunteerops_scenarios)")
    args = ap.parse_args()
    only = {s.strip().upper() for s in args.only.split(",") if s.strip()}

    harness._llm = CountingLLM()
    print(f"db={db.get_db().name}  model={harness._llm.model}")
    fx.load()
    print(f"search backend: {repo.LAST_SEARCH_BACKEND}\n")

    for sc in SCENARIOS:
        if only and sc.id not in only:
            continue
        for i in range(args.runs if sc.llm else 1):
            r = measure(sc.fn)
            sc.results.append(r)
            mark = "PASS" if r.ok else "FAIL"
            extra = (f"  {r.seconds:5.1f}s  llm={r.llm_calls} tools={r.tool_calls} "
                     f"tool_err={r.tool_errors}") if sc.llm else ""
            print(f"{sc.id:<4} run{i + 1} {mark}{extra}  {r.why}", flush=True)

    print("\n" + "=" * 78)
    det = llm = det_ok = llm_ok = 0
    for sc in SCENARIOS:
        if not sc.results:
            continue
        passed = sum(r.ok for r in sc.results)
        n = len(sc.results)
        if sc.llm:
            llm, llm_ok = llm + n, llm_ok + passed
            avg = lambda attr: sum(getattr(r, attr) for r in sc.results) / n  # noqa: E731
            stats = (f"avg {avg('seconds'):4.1f}s  llm {avg('llm_calls'):.1f}  "
                     f"tools {avg('tool_calls'):.1f}  tool_err {avg('tool_errors'):.1f}")
        else:
            det, det_ok = det + n, det_ok + passed
            stats = "deterministic"
        print(f"{sc.id:<4} {passed}/{n} {'PASS' if passed == n else 'FAIL'}  {sc.title:<45} {stats}")
    if det:
        print(f"\nDeterministic: {det_ok}/{det}" + ("" if det_ok == det else "  <-- must be 100%"))
    if llm:
        print(f"LLM scenarios: {llm_ok}/{llm} ({llm_ok / llm:.0%})")


if __name__ == "__main__":
    main()
