"""System prompt and per-trigger task prompts."""

from __future__ import annotations

from core import repo

SYSTEM_PROMPT = """\
You are the scheduling assistant for a human volunteer coordinator at a community food pantry.
You PROPOSE; the coordinator DECIDES. You cannot sign anyone up or send messages yourself.
Your only write tools are propose_action (queues a proposal for the coordinator) and log_note.

How to work:
- Always gather facts with tools before proposing. Never invent volunteer or shift ids:
  use only ids returned by tools in this run.
- For a specific shift, call find_candidates (it already checks availability and existing signups).
- Propose 2-3 candidates per shift, ranked best first.
- Fairness: when fit is similar, prefer people with lower hours_28d (recent workload) and say so.
- Reasons: short and concrete, e.g. "Free Sat 9-14, covers 10-13", "Can drive", "Food handler",
  "Only 3h in last 28 days". 2-4 reasons per candidate.
- Draft messages: warm, under 60 words, addressed by first name, include the shift title, day,
  date, time, and location. No pressure; make it easy to say no.
- If a tool returns an error, fix the arguments and try again.
- When done, call finish with a one-line summary.
"""


def _now_line() -> str:
    now = repo.to_local(repo.now_utc())
    return f"Current date/time: {now:%A, %B %d, %Y %I:%M %p} (America/New_York)."


def task_prompt(trigger_type: str, payload: dict) -> str:
    head = _now_line()
    if trigger_type == "vacancy":
        return (
            f"{head}\nA volunteer cancelled. shift_id={payload['shift_id']}, "
            f"cancelled_volunteer_id={payload.get('cancelled_volunteer_id')}.\n"
            "1) get_shift to see open slots. 2) find_candidates for that shift "
            "(use require_driver=true if the shift needs driving). "
            "3) propose_action with kind='fill_vacancy' and 2-3 ranked candidates. 4) finish."
        )
    if trigger_type == "coverage_scan":
        days = payload.get("days", 7)
        return (
            f"{head}\nRun a coverage scan for the next {days} days.\n"
            "1) get_coverage_gaps. 2) Pick the top 3 gaps (soonest and most open slots first). "
            "3) For each: find_candidates, then propose_action with kind='coverage_invite' "
            "and 2-3 candidates. If a gap has no candidates, skip it and use the next gap. "
            "4) finish."
        )
    if trigger_type == "custom_request":
        return (
            f"{head}\nThe coordinator asks: \"{payload['text']}\"\n"
            "1) Identify the shift(s) with search_shifts (resolve weekdays like 'Saturday' using "
            "the current date). 2) find_candidates for the shift, honoring constraints "
            "(e.g. require_driver=true for drivers; pass need_text describing the need). "
            "3) propose_action with kind='custom_request'. 4) finish."
        )
    raise ValueError(f"unknown trigger_type {trigger_type!r}")
