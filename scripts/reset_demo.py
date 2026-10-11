"""Wipe all demo collections and reseed. Usage: python -m scripts.reset_demo"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `python scripts/x.py`

from core import db
from core.repo import coverage_gaps
from scripts.seed import add_embeddings, build_seed, summarize, write_seed

COLLECTIONS = ["volunteers", "shifts", "signups", "approvals", "messages",
               "agent_log", "agent_triggers", "worker_state"]


def main() -> None:
    database = db.get_db()
    existing = set(database.list_collection_names())
    for name in COLLECTIONS:
        if name in existing:
            # delete_many (not drop) so Atlas Vector Search indexes survive resets.
            database[name].delete_many({})
    print("Wiped:", ", ".join(n for n in COLLECTIONS if n in existing) or "(nothing)")

    data = build_seed()
    add_embeddings(data)
    write_seed(data)

    for warning in db.ensure_indexes():
        print("⚠️ ", warning)
    print("Vector indexes:", db.vector_index_status())

    print("Seeded:", summarize(data))
    print(f"Coverage gaps (next 7 days): {len(coverage_gaps(7))}")
    run = db.shifts().find_one({"title": "Saturday Delivery Run"})
    names = [db.volunteers().find_one({"_id": s["volunteer_id"]})["name"]
             for s in db.signups().find({"shift_id": run["_id"], "status": "confirmed"})]
    print(f"Saturday Delivery Run: status={run['status']} crew={names}")


if __name__ == "__main__":
    main()
