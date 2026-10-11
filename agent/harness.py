"""Hand-written ReAct loop. Every step is logged to agent_log.

CLI:
  python -m agent.harness vacancy <shift_id> <cancelled_volunteer_id>
  python -m agent.harness scan
  python -m agent.harness ask "<text>"
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `python agent/harness.py`

from bson import ObjectId

from agent.llm import LLM
from agent.prompts import SYSTEM_PROMPT, task_prompt
from agent.tools import TOOL_SCHEMAS, RunCtx, dispatch
from core import db, repo

MAX_STEPS = 12
LOG_CHARS = 1000
NUDGE = ("Your last reply was empty. Call finish with a one-line answer for the coordinator "
         "(or propose_action if a proposal is actually needed).")

_llm: LLM | None = None


def get_llm() -> LLM:
    global _llm
    if _llm is None:
        _llm = LLM()  # module-level so a JSON-mode switch sticks across runs
    return _llm


class RunLogger:
    def __init__(self, run_id: str, trigger_type: str):
        self.run_id, self.trigger, self.step = run_id, trigger_type, 0

    def log(self, kind: str, content: str, **extra) -> None:
        self.step += 1
        db.agent_log().insert_one({
            "run_id": self.run_id, "trigger": self.trigger, "step": self.step, "kind": kind,
            "content": (content or "")[:LOG_CHARS], "ts": repo.now_utc(), **extra,
        })


def run_agent(trigger_type: str, payload: dict, llm: LLM | None = None) -> str:
    run_id = str(ObjectId())
    log = RunLogger(run_id, trigger_type)
    exclude = {str(x) for x in payload.get("exclude_volunteer_ids", [])}
    if payload.get("cancelled_volunteer_id"):
        exclude.add(str(payload["cancelled_volunteer_id"]))
    ctx = RunCtx(run_id=run_id, trigger_type=trigger_type, payload=payload,
                 exclude_volunteer_ids=exclude)
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": task_prompt(trigger_type, payload)}]
        llm = llm or get_llm()
    except Exception as e:  # noqa: BLE001 - bad payload or missing config
        log.log("error", f"run could not start: {type(e).__name__}: {e}")
        return run_id
    log.log("thought", f"Run started ({trigger_type}): {json.dumps(payload, default=str)}")

    nudged = False
    for _ in range(MAX_STEPS):
        try:
            turn = llm.chat(messages, TOOL_SCHEMAS)
        except Exception as e:  # noqa: BLE001 - LLM outage must not crash callers
            log.log("error", f"LLM call failed: {type(e).__name__}: {str(e)[:300]}")
            return run_id
        if not turn.tool_calls:
            if not turn.text.strip() and not nudged:
                # Thinking models sometimes stop with an empty reply; ask once for an answer.
                nudged = True
                messages.append(turn.as_message())
                messages.append({"role": "user", "content": NUDGE})
                continue
            log.log("final", turn.text.strip() or "No proposal was needed for this request.")
            return run_id
        if turn.text.strip():
            log.log("thought", turn.text.strip())

        messages.append(turn.as_message())
        for tc in turn.tool_calls:
            log.log("tool_call", tc.args_json, tool=tc.name, args=_safe_args(tc.args_json),
                    call_id=tc.id)
            result = dispatch(tc.name, tc.args_json, ctx)
            log.log("tool_result", result, tool=tc.name, call_id=tc.id)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        if ctx.finished:
            log.log("final", ctx.finish_summary)
            return run_id

    log.log("error", f"stopped after max_steps={MAX_STEPS}")
    return run_id


def _safe_args(args_json: str) -> dict | str:
    try:
        args = json.loads(args_json or "{}")
        return args if isinstance(args, dict) else str(args)
    except json.JSONDecodeError:
        return args_json[:LOG_CHARS]


def get_run_log(run_id: str) -> list[dict]:
    return list(db.agent_log().find({"run_id": run_id}, {"_id": 0}).sort("step", 1))


def get_run_approvals(run_id: str) -> list[dict]:
    return list(db.approvals().find({"agent_run_id": run_id}).sort("created_at", 1))


# ---------- CLI ----------

def _print_run(run_id: str, seconds: float) -> None:
    for e in get_run_log(run_id):
        label = f"{e['kind']}" + (f" {e['tool']}" if e.get("tool") else "")
        print(f"  [{e['step']:>2}] {label:<28} {e['content'][:160]}")
    approvals = get_run_approvals(run_id)
    print(f"\nrun_id={run_id}  {seconds:.1f}s  approvals={[str(a['_id']) for a in approvals]}")
    for a in approvals:
        shift = repo.get_shift(a["shift_id"])
        print(f"\n== {a['kind']} | {shift['title']} | {a['summary']}")
        for c in a["candidates"]:
            v = repo.get_volunteer(c["volunteer_id"])
            print(f"  #{c['rank']} {v['name']} (drive={v['can_drive']}, {c['hours_28d']}h)")
            for r in c["reasons"]:
                print(f"     - {r}")
            print(f"     draft ({len(c['draft_message'].split())}w): {c['draft_message']}")


def main(argv: list[str]) -> None:
    usage = ("usage: python -m agent.harness vacancy <shift_id> <cancelled_volunteer_id> | "
             "scan | ask \"<text>\"")
    if not argv:
        sys.exit(usage)
    cmd = argv[0]
    if cmd == "vacancy" and len(argv) == 3:
        trigger, payload = "vacancy", {"shift_id": argv[1], "cancelled_volunteer_id": argv[2]}
    elif cmd == "scan":
        trigger, payload = "coverage_scan", {"days": 7}
    elif cmd == "ask" and len(argv) == 2:
        trigger, payload = "custom_request", {"text": argv[1]}
    else:
        sys.exit(usage)
    t0 = time.time()
    run_id = run_agent(trigger, payload)
    _print_run(run_id, time.time() - t0)
    mode = _llm.mode if _llm else "n/a"
    print(f"\nLLM mode: {mode}  |  search backend: {repo.LAST_SEARCH_BACKEND or 'n/a'}")


if __name__ == "__main__":
    main(sys.argv[1:])
