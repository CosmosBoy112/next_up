"""Weather for shifts: Open-Meteo hourly forecasts (free, no API key, 16 days ahead), a
severity rating, which shifts are weather-sensitive, and a demo override that forces a
scenario (e.g. a thunderstorm) on one date so the feature can be shown on a sunny day.
The override only applies when NEXTUP_DEMO=1; otherwise the real forecast is always used.

Deterministic code fetches and rates the weather; the agent only explains it and proposes
alternatives (agent/tools.py)."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from functools import lru_cache

from core import config, db, repo
from core.config import LOCAL_TZ

API_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY = "temperature_2m,precipitation_probability,precipitation,weather_code,wind_gusts_10m"
CACHE_SECONDS = 30 * 60
DAYTIME = range(8, 20)  # hours used for the daily outlook

# The pantry's location. Default: Hudson Valley, NY (matches the America/New_York timezone).
LAT = float(os.getenv("WEATHER_LAT", "41.7004"))
LON = float(os.getenv("WEATHER_LON", "-73.9210"))
PLACE = os.getenv("WEATHER_PLACE", "Hudson Valley, NY")

# Shifts are weather-sensitive when they're outdoors or on the road. A shift document can
# override this with an explicit boolean "weather_sensitive" field.
SENSITIVE_WORDS = ("deliver", "driv", "park", "pavilion", "farm", "glean", "outdoor",
                   "loading dock", "pop-up", "truck")

WMO = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 56: "freezing drizzle",
    57: "freezing drizzle", 61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain",
    67: "freezing rain", 71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "rain showers", 81: "heavy showers", 82: "violent showers", 85: "snow showers",
    86: "heavy snow showers", 95: "thunderstorm", 96: "thunderstorm with hail",
    99: "thunderstorm with hail",
}
THUNDER = {95, 96, 99}
SNOW = {71, 73, 75, 77, 85, 86}
FREEZING = {56, 57, 66, 67, 48}

# Demo scenarios: what the forecast looks like on the chosen date.
SCENARIOS = {
    "thunderstorm": {"code": 95, "pop": 90, "precip_mm": 18.0, "gust_kmh": 72, "temp": (21, 25)},
    "heavy_rain": {"code": 65, "pop": 95, "precip_mm": 24.0, "gust_kmh": 45, "temp": (12, 15)},
    "snow": {"code": 75, "pop": 90, "precip_mm": 14.0, "gust_kmh": 50, "temp": (-4, -1)},
    "heat": {"code": 0, "pop": 5, "precip_mm": 0.0, "gust_kmh": 15, "temp": (31, 37)},
}
SEVERITY_ORDER = {"ok": 0, "caution": 1, "severe": 2}


class WeatherUnavailable(RuntimeError):
    pass


# ---------- forecast ----------

@lru_cache(maxsize=2)
def _fetch(bucket: int) -> list[dict]:  # bucket = cache window; a new one refetches
    query = urllib.parse.urlencode({"latitude": LAT, "longitude": LON, "hourly": HOURLY,
                                    "timezone": LOCAL_TZ, "forecast_days": 16})
    try:
        with urllib.request.urlopen(f"{API_URL}?{query}", timeout=10) as r:
            data = json.load(r)["hourly"]
    except Exception as e:  # noqa: BLE001 - network/JSON problems are all "unavailable"
        raise WeatherUnavailable(f"forecast unavailable: {type(e).__name__}: {e}") from e
    tz = repo.TZ
    return [{
        "time": datetime.fromisoformat(t).replace(tzinfo=tz),
        "temp": data["temperature_2m"][i], "pop": data["precipitation_probability"][i] or 0,
        "precip": data["precipitation"][i] or 0.0, "code": data["weather_code"][i] or 0,
        "gust": data["wind_gusts_10m"][i] or 0.0,
    } for i, t in enumerate(data["time"])]


def _hourly() -> list[dict]:
    return _fetch(int(time.time() // CACHE_SECONDS))


def _summarize(hours: list[dict]) -> dict | None:
    if not hours:
        return None
    worst = max(hours, key=lambda h: _code_rank(h["code"]))
    return {
        "condition": WMO.get(worst["code"], f"code {worst['code']}"), "code": worst["code"],
        "rain_chance_pct": max(h["pop"] for h in hours),
        "precip_mm": round(sum(h["precip"] for h in hours), 1),
        "gust_kmh": round(max(h["gust"] for h in hours)),
        "temp_c": (round(min(h["temp"] for h in hours)), round(max(h["temp"] for h in hours))),
        "source": "open-meteo",
    }


def _code_rank(code: int) -> int:
    if code in THUNDER:
        return 6
    if code in SNOW or code in FREEZING:
        return 5
    if code in (65, 82, 81):
        return 4
    if code >= 51:
        return 3
    if code in (45,):
        return 2
    return 1 if code else 0


def _scenario(d: date) -> dict | None:
    if not config.demo_mode():
        return None
    demo = get_demo()
    if not demo.get("enabled") or demo.get("date") != d.isoformat():
        return None
    s = SCENARIOS[demo.get("scenario", "thunderstorm")]
    return {"condition": WMO[s["code"]], "code": s["code"], "rain_chance_pct": s["pop"],
            "precip_mm": s["precip_mm"], "gust_kmh": s["gust_kmh"], "temp_c": s["temp"],
            "source": "demo"}


def forecast(start: datetime, end: datetime) -> dict | None:
    """Weather over [start, end). None if beyond the forecast horizon."""
    local_start = repo.to_local(start)
    if demo := _scenario(local_start.date()):
        return demo
    lo, hi = repo.to_local(start).replace(minute=0, second=0, microsecond=0), repo.to_local(end)
    return _summarize([h for h in _hourly() if lo <= h["time"] < hi])


def assess(f: dict | None) -> tuple[str, list[str]]:
    """("ok" | "caution" | "severe", reasons)."""
    if f is None:
        return "ok", ["No forecast yet (more than 16 days out)."]
    severe, caution = [], []
    code, rain, mm, gust = f["code"], f["rain_chance_pct"], f["precip_mm"], f["gust_kmh"]
    tmin, tmax = f["temp_c"]
    if code in THUNDER:
        severe.append(f"Thunderstorms likely ({rain}% chance of rain)")
    if code in SNOW or code in FREEZING:
        (severe if mm >= 2 or code in FREEZING else caution).append(f"{f['condition'].capitalize()} expected")
    wet = "snow (water equivalent)" if code in SNOW else "rain"
    if mm >= 10:
        severe.append(f"Heavy {wet}: about {mm} mm")
    elif rain >= 60 and mm >= 2:
        caution.append(f"{wet.capitalize()} likely: {rain}% chance, about {mm} mm")
    if gust >= 70:
        severe.append(f"Damaging wind gusts up to {gust} km/h")
    elif gust >= 50:
        caution.append(f"Strong wind gusts up to {gust} km/h")
    if tmax >= 35:
        severe.append(f"Extreme heat: up to {tmax}°C")
    elif tmax >= 32:
        caution.append(f"Hot: up to {tmax}°C")
    if tmin <= -10:
        severe.append(f"Extreme cold: down to {tmin}°C")
    elif tmin <= -3:
        caution.append(f"Freezing: down to {tmin}°C")
    if severe:
        return "severe", severe + caution
    if caution:
        return "caution", caution
    return "ok", [f"{f['condition'].capitalize()}, {tmin}-{tmax}°C"]


def weather_sensitive(shift: dict) -> bool:
    if isinstance(shift.get("weather_sensitive"), bool):
        return shift["weather_sensitive"]
    text = f"{shift['title']} {shift['location']} {shift.get('description', '')}".lower()
    return any(w in text for w in SENSITIVE_WORDS)


def shift_weather(shift: dict) -> dict:
    f = forecast(shift["start"], shift["end"])
    severity, reasons = assess(f)
    return {"forecast": f, "severity": severity, "reasons": reasons,
            "weather_sensitive": weather_sensitive(shift), "place": PLACE}


def risky_shifts(days: int = 7) -> list[tuple[dict, dict]]:
    """Upcoming weather-sensitive shifts whose forecast is caution or worse, soonest first."""
    out = []
    for s in repo.list_upcoming_shifts(days):
        if not weather_sensitive(s):
            continue
        w = shift_weather(s)
        if w["severity"] != "ok":
            out.append((s, w))
    return out


def outlook(days: int = 7) -> list[dict]:
    """Daytime (8:00-20:00) summary per day, to find better days for rescheduling."""
    today = repo.to_local(repo.now_utc()).date()
    hours = _hourly()
    out = []
    for i in range(days):
        d = today + timedelta(days=i)
        f = _scenario(d) or _summarize([h for h in hours if h["time"].date() == d and h["time"].hour in DAYTIME])
        severity, reasons = assess(f)
        out.append({"date": f"{d:%a %Y-%m-%d}", "severity": severity, "summary": reasons[0],
                    "forecast": f})
    return out


# ---------- demo override (stored in Mongo so the UI and the worker agree) ----------

def get_demo() -> dict:
    """The stored demo setting; treated as off unless NEXTUP_DEMO=1."""
    if not config.demo_mode():
        return {"enabled": False}
    return db.col("settings").find_one({"_id": "weather_demo"}) or {"enabled": False}


def set_demo(enabled: bool, day: date | None = None, scenario: str = "thunderstorm") -> None:
    db.col("settings").update_one(
        {"_id": "weather_demo"},
        {"$set": {"enabled": enabled, "date": day.isoformat() if day else None, "scenario": scenario,
                  "updated_at": repo.now_utc()}},
        upsert=True)
