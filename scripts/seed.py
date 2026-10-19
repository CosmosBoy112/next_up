"""Deterministic demo data for the fictional "Valley Community Pantry".

build_seed() is pure (no DB) so it can be inspected offline; write_seed() inserts it.
Run directly: python -m scripts.seed  (inserts into an empty DB; use reset_demo to wipe first)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `python scripts/x.py`

import random
from datetime import date, datetime, time, timedelta, timezone

from bson import ObjectId

from core.embeddings import embed_many
from core.repo import TZ, WEEKDAYS, is_available, shift_embed_text

ORG = "Valley Community Pantry"
SKILLS = ["driving", "heavy lifting", "food handling", "spanish", "data entry",
          "event setup", "first aid", "kids activities", "social media", "photography"]

NAMES = [
    "Michael Brooks", "Priya Natarajan", "Marcus Johnson", "Sofia Delgado", "Wei Chen",
    "Fatima Al-Sayed", "Liam O'Connor", "Aisha Mensah", "Diego Morales", "Hannah Kim",
    "Tomasz Nowak", "Grace Okafor", "Ethan Brooks", "Mei Lin Tan", "Omar Haddad",
    "Isabella Rossi", "Jamal Carter", "Yuki Tanaka", "Nadia Petrova", "Carlos Mendez",
    "Emily Watson", "Kwame Asante", "Lucia Fernandez", "Ravi Patel", "Zoe Martin",
    "Samuel Levi", "Amara Diallo", "Noah Fischer", "Leila Karimi", "Benjamin Park",
    "Chloe Dubois", "Mateo Silva", "Ingrid Larsen", "Tariq Rahman", "Olivia Bennett",
    "Hiroshi Sato", "Valentina Cruz", "Daniel Ortiz", "Maya Goldberg", "Kofi Boateng",
]

SKILL_PHRASES = {
    "driving": ["I have a minivan and happily do delivery runs",
                "I drive a pickup and can haul donations around town"],
    "heavy lifting": ["I'm comfortable lifting heavy boxes and unloading trucks",
                      "I like the physical work of moving pallets and crates"],
    "food handling": ["I have a food handler certificate and enjoy sorting produce",
                      "I'm careful with food safety and like packing meal kits"],
    "spanish": ["I speak Spanish fluently and can help families at intake",
                "I'm a native Spanish speaker who enjoys translating for guests"],
    "data entry": ["I'm fast at data entry and keeping client records tidy",
                   "I like spreadsheets and logging inventory accurately"],
    "event setup": ["I enjoy setting up tables, tents, and signage for events",
                    "I'm handy with event setup and teardown"],
    "first aid": ["I'm CPR and first aid certified",
                  "I work as an EMT and can handle first aid on site"],
    "kids activities": ["I love running crafts and games with kids",
                        "I volunteer with children and enjoy reading stories to kids"],
    "social media": ["I can post updates and run our social media",
                     "I enjoy writing posts and promoting events on social media"],
    "photography": ["I take photos at events for newsletters",
                    "photography is my hobby and I document our community events"],
}

OPENERS = ["Retired teacher here.", "College student at the nearby campus.",
           "Neighbor of the pantry for ten years.", "Working parent who helps on weekends.",
           "Nurse who likes giving back.", "Software engineer looking to help locally.",
           "Recent grad new to the valley.", "Small business owner in town."]

# (title, location, description, required_skills, required_count, local_hour, hours)
UPCOMING_SHIFTS = [
    ("Pantry Sorting", "Pantry Warehouse, 12 Mill St",
     "Sort donated canned goods and fresh produce, check expiry dates, and stock shelves.",
     ["food handling"], 5, 9, 3),
    ("Kids Reading Hour", "Valley Public Library, Room B",
     "Read picture books aloud and lead a simple craft with children while parents shop the pantry.",
     ["kids activities"], 3, 16, 2),
    ("Community Dinner", "Grace Hall, 40 Oak Ave",
     "Set up tables, serve a hot meal, and clean up at our monthly community dinner.",
     ["food handling", "event setup"], 6, 17, 3),
    ("Client Intake Desk", "Pantry Front Office",
     "Greet families, register new clients, and help Spanish-speaking guests fill out forms.",
     ["spanish", "data entry"], 2, 10, 3),
    ("Truck Unloading", "Pantry Loading Dock",
     "Unload the regional food bank truck and move pallets into cold storage.",
     ["heavy lifting"], 4, 13, 2),
    ("Mobile Pantry Pop-up", "Riverside Park Pavilion",
     "Set up tents and hand out groceries at a pop-up distribution in the park.",
     ["event setup", "food handling"], 5, 11, 3),
    ("Senior Grocery Delivery", "Departs Pantry Warehouse",
     "Drive pre-packed grocery boxes to homebound seniors and check in with them briefly.",
     ["driving"], 3, 14, 3),
    ("Inventory Data Entry", "Pantry Front Office",
     "Log incoming donations and update stock counts in the inventory spreadsheet.",
     ["data entry"], 2, 18, 2),
    ("Health Fair Booth", "Valley Community Center",
     "Staff a booth with healthy recipes, help with first aid station, and share pantry info.",
     ["first aid", "spanish"], 3, 12, 3),
    ("Kids Snack Packing", "Pantry Warehouse, 12 Mill St",
     "Pack weekend snack bags for local school kids; a fun, family-friendly shift.",
     ["food handling", "kids activities"], 4, 15, 2),
    ("Fundraiser Photo & Social", "Valley Community Center",
     "Photograph the fall fundraiser and post live updates on social media.",
     ["photography", "social media"], 2, 18, 2),
    ("Produce Gleaning", "Hillside Farm, Route 9",
     "Harvest leftover produce from a partner farm and load crates for the pantry.",
     ["heavy lifting", "food handling"], 4, 9, 3),
    ("Evening Restock", "Pantry Warehouse, 12 Mill St",
     "Restock shelves and break down cardboard after the busy evening distribution.",
     ["heavy lifting"], 3, 18, 2),
]
DELIVERY_RUN = ("Saturday Delivery Run", "Departs Pantry Warehouse, 12 Mill St",
                "Drive the pantry van to deliver grocery boxes to families across the valley; "
                "lift boxes up to 40 lbs.", ["driving", "heavy lifting"], 3, 10, 3)

PAST_SHIFT_TITLES = ["Pantry Sorting", "Truck Unloading", "Community Dinner",
                     "Senior Grocery Delivery", "Mobile Pantry Pop-up", "Evening Restock"]

N_DRIVERS = 12           # ~30% of 40
N_SAT_DRIVERS = 7        # drivers guaranteed to cover the Saturday Delivery Run window
N_PAST_SHIFTS = 23


def local_dt(d: date, hour: int) -> datetime:
    return datetime.combine(d, time(hour), tzinfo=TZ).astimezone(timezone.utc)


def next_saturday(today: date) -> date:
    return today + timedelta(days=(5 - today.weekday()) % 7 or 7)


# Typical availability windows: morning, midday, afternoon/evening, evening, all day.
BLOCK_WINDOWS = [("08:00", "14:00"), ("10:00", "16:00"), ("13:00", "20:00"),
                 ("16:00", "21:00"), ("08:00", "21:00")]


def _random_block(rng: random.Random) -> dict:
    start, end = rng.choice(BLOCK_WINDOWS)
    return {"day": rng.choice(WEEKDAYS), "start": start, "end": end}


def _bio(rng: random.Random, skills: list[str]) -> str:
    phrases = [rng.choice(SKILL_PHRASES[s]) for s in skills]
    body = ", and ".join(phrases) + "."
    body = body[0].upper() + body[1:]
    return f"{rng.choice(OPENERS)} {body}"


def build_volunteers(rng: random.Random, now: datetime) -> list[dict]:
    vols = []
    non_drive_skills = [s for s in SKILLS if s != "driving"]
    for i, name in enumerate(NAMES):
        can_drive = i < N_DRIVERS
        if name == "Priya Natarajan":
            skills = ["kids activities", "spanish"]
        else:
            skills = rng.sample(non_drive_skills, rng.randint(1, 2))
            if can_drive:
                skills = ["driving"] + skills[:1] if i % 2 else ["driving", "heavy lifting"]
        availability = [_random_block(rng) for _ in range(rng.randint(1, 3))]
        if i < N_SAT_DRIVERS:
            availability[0] = {"day": "Sat", "start": rng.choice(["08:00", "09:00"]),
                               "end": rng.choice(["14:00", "16:00"])}
        if name == "Priya Natarajan":
            availability = [{"day": d, "start": "14:00", "end": "20:00"} for d in WEEKDAYS]
        first, last = name.split(" ", 1)
        vols.append({
            "_id": ObjectId(), "name": name,
            "email": f"{first.lower()}.{last.lower().replace(' ', '').replace(chr(39), '')}@example.org",
            "org": ORG, "skills": skills, "bio": _bio(rng, skills), "can_drive": can_drive,
            "availability": availability, "created_at": now,
        })
    return vols


def _shift_doc(spec: tuple, day: date, now: datetime) -> dict:
    title, location, description, skills, required, hour, hours = spec
    return {
        "_id": ObjectId(), "title": title, "org": ORG, "location": location,
        "start": local_dt(day, hour), "end": local_dt(day, hour + hours),
        "required_count": required, "required_skills": skills, "description": description,
        "status": "open", "created_at": now,
    }


def _signup_doc(vol: dict, shift: dict, status: str, now: datetime) -> dict:
    return {"_id": ObjectId(), "shift_id": shift["_id"], "volunteer_id": vol["_id"],
            "status": status, "source": "self", "created_at": now, "updated_at": now}


def build_seed(now: datetime | None = None) -> dict[str, list[dict]]:
    rng = random.Random(42)
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(TZ).date()
    vols = build_volunteers(rng, now)
    by_name = {v["name"]: v for v in vols}

    # Upcoming: the planted delivery run on next Saturday + 13 others spread over days 1..14.
    upcoming = [_shift_doc(DELIVERY_RUN, next_saturday(today), now)]
    for k, spec in enumerate(UPCOMING_SHIFTS):
        upcoming.append(_shift_doc(spec, today + timedelta(days=1 + k), now))

    # Past shifts (history for hours_28d), last 27 days.
    specs = {s[0]: s for s in UPCOMING_SHIFTS}
    past = []
    for k in range(N_PAST_SHIFTS):
        spec = specs[PAST_SHIFT_TITLES[k % len(PAST_SHIFT_TITLES)]]
        past.append(_shift_doc(spec, today - timedelta(days=1 + (k * 26) // N_PAST_SHIFTS), now))

    signups = []
    # Skewed workloads: a few "regulars" do most of the past work.
    weights = [8 if i % 5 == 1 else 1 for i in range(len(vols))]
    for shift in past:
        chosen: set[int] = set()
        while len(chosen) < shift["required_count"]:
            chosen.add(rng.choices(range(len(vols)), weights=weights)[0])
        signups += [_signup_doc(vols[i], shift, "completed", now) for i in sorted(chosen)]
        shift["status"] = "filled"

    # Planted demo: delivery run exactly full, including Michael Brooks.
    run = upcoming[0]
    crew = [by_name["Michael Brooks"]] + [v for v in vols[1:N_SAT_DRIVERS] if is_available(v, run)][:2]
    assert len(crew) == run["required_count"], "seed: not enough Saturday drivers"
    signups += [_signup_doc(v, run, "confirmed", now) for v in crew]
    run["status"] = "filled"

    # Other upcoming shifts: partially filled with available volunteers (leaves gaps).
    for shift in upcoming[1:]:
        pool = [v for v in vols if is_available(v, shift)] or vols
        n = rng.randint(1, shift["required_count"] - 1)
        for v in rng.sample(pool, min(n, len(pool))):
            signups.append(_signup_doc(v, shift, "confirmed", now))

    return {"volunteers": vols, "shifts": upcoming + past, "signups": signups}


def add_embeddings(data: dict[str, list[dict]]) -> None:
    vols, shifts = data["volunteers"], data["shifts"]
    for v, vec in zip(vols, embed_many([v["bio"] for v in vols])):
        v["bio_embedding"] = vec
    texts = [shift_embed_text(s["title"], s["description"]) for s in shifts]
    for s, vec in zip(shifts, embed_many(texts)):
        s["description_embedding"] = vec


def write_seed(data: dict[str, list[dict]]) -> None:
    from core import db

    for name in ("volunteers", "shifts", "signups"):
        db.col(name).insert_many(data[name])


def summarize(data: dict[str, list[dict]]) -> str:
    now = datetime.now(timezone.utc)
    up = sum(1 for s in data["shifts"] if s["start"] >= now)
    return (f"volunteers={len(data['volunteers'])}  "
            f"shifts={up} upcoming (+{len(data['shifts']) - up} past for history)  "
            f"signups={len(data['signups'])}")


def main() -> None:
    data = build_seed()
    add_embeddings(data)
    write_seed(data)
    print("Seeded:", summarize(data))


if __name__ == "__main__":
    main()
