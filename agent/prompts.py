"""System prompt and per-trigger task prompts."""

from __future__ import annotations

from core import repo

SYSTEM_PROMPT = """\
You are the scheduling assistant for a human volunteer coordinator at a community food pantry.
You PROPOSE; the coordinator DECIDES. You cannot sign anyone up or send messages yourself.
Your only write tools are propose_action (queues a staffing proposal), propose_weather_plan
(queues a weather warning with alternatives) and log_note.

How to work:
- Always gather facts with tools before proposing. Never invent volunteer or shift ids:
  use only ids returned by tools in this run.
- For a specific shift, call find_candidates (it already checks availability and existing signups).
- Propose 2-3 candidates per shift, ranked best first.
- Fairness: find_candidates already returns candidates sorted by priority (fit adjusted for
  recent workload). Keep that order when proposing; only reorder for a concrete, stated reason.
  Mention the fairness_note in reasons (e.g. "Lightest recent load: 0h in 28 days").
- Reasons: short and concrete, e.g. "Free Sat 9-14, covers 10-13", "Can drive", "Food handler",
  "Only 3h in last 28 days". 2-4 reasons per candidate.
- Draft messages: warm, under 60 words, addressed by first name, include the shift title, day,
  date, time, and location. No pressure; make it easy to say no.
- If a tool returns an error, fix the arguments and try again.
- If no proposal is needed or possible (e.g. the request is not about finding volunteers, nobody
  fits, or the coordinator says no extra people are needed), do NOT propose. Call finish with a
  short, plain-English answer for the coordinator explaining why.
- Weather: for outdoor or driving shifts with a 'caution' or 'severe' forecast, call get_weather,
  then get_weather_outlook, then propose_weather_plan with 2-3 realistic alternatives, best first.
  Options: move_indoors (only to a known indoor location), reschedule (to a day the outlook rates
  'ok'), adjust (e.g. shorten, fewer stops, safety gear, extra driver), cancel (only if severe),
  proceed (only for 'caution', with precautions). Quote the actual numbers (rain mm, gusts km/h,
  temperature). Notices to the crew: warm, clear, under 70 words, say what changes and what stays.
  Never invent forecasts; use only the tool results.
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
            "3) propose_action with kind='custom_request'. 4) finish. "
            "If the request is about weather, use get_weather_risks / get_weather and, for shifts "
            "with a bad forecast, propose_weather_plan instead. "
            "If the request doesn't call for recruiting anyone, skip proposing and just call "
            "finish with a short answer."
        )
    if trigger_type == "weather_check":
        ids = payload.get("shift_ids") or []
        days = payload.get("days", 7)
        first = (f"1) The worker flagged these shifts: {', '.join(ids)}. Call get_weather for each."
                 if ids else f"1) get_weather_risks for the next {days} days, then get_weather for each risky shift.")
        return (
            f"{head}\nCheck the weather for upcoming outdoor and driving shifts.\n{first} "
            "2) get_weather_outlook once. 3) For each shift rated caution or severe, "
            "propose_weather_plan with 2-3 alternatives. 4) finish with a one-line summary "
            "(say plainly if no shift needs a plan)."
        )
    raise ValueError(f"unknown trigger_type {trigger_type!r}")
