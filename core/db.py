"""Mongo client singleton, collection handles, and idempotent index setup."""

from __future__ import annotations

import json
from functools import lru_cache

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import OperationFailure
from pymongo.operations import SearchIndexModel

from core import config
from core.config import EMBED_DIM

VOLUNTEER_VS_INDEX = "volunteer_bio_vs"
SHIFT_VS_INDEX = "shift_desc_vs"

VECTOR_INDEXES: dict[str, tuple[str, dict]] = {
    # index name -> (collection, definition)
    VOLUNTEER_VS_INDEX: (
        "volunteers",
        {
            "fields": [
                {"type": "vector", "path": "bio_embedding",
                 "numDimensions": EMBED_DIM, "similarity": "cosine"},
                {"type": "filter", "path": "can_drive"},
                {"type": "filter", "path": "skills"},
                {"type": "filter", "path": "org"},
            ]
        },
    ),
    SHIFT_VS_INDEX: (
        "shifts",
        {
            "fields": [
                {"type": "vector", "path": "description_embedding",
                 "numDimensions": EMBED_DIM, "similarity": "cosine"},
                {"type": "filter", "path": "status"},
            ]
        },
    ),
}


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    return MongoClient(config.mongodb_uri(), tz_aware=True, serverSelectionTimeoutMS=10_000)


def get_db() -> Database:
    return get_client()[config.db_name()]


def col(name: str) -> Collection:
    return get_db()[name]


def volunteers() -> Collection:
    return col("volunteers")


def shifts() -> Collection:
    return col("shifts")


def signups() -> Collection:
    return col("signups")


def approvals() -> Collection:
    return col("approvals")


def messages() -> Collection:
    return col("messages")


def agent_log() -> Collection:
    return col("agent_log")


def agent_triggers() -> Collection:
    return col("agent_triggers")


def worker_state() -> Collection:
    return col("worker_state")


def ensure_indexes() -> list[str]:
    """Create all regular + vector indexes. Returns warnings (empty if all ok)."""
    shifts().create_index([("start", ASCENDING)])
    shifts().create_index([("status", ASCENDING)])
    signups().create_index([("shift_id", ASCENDING), ("status", ASCENDING)])
    signups().create_index([("volunteer_id", ASCENDING), ("status", ASCENDING)])
    approvals().create_index([("status", ASCENDING), ("created_at", ASCENDING)])
    messages().create_index([("to_volunteer_id", ASCENDING), ("status", ASCENDING)])
    agent_log().create_index([("run_id", ASCENDING), ("step", ASCENDING)])
    agent_log().create_index([("ts", ASCENDING)])
    agent_triggers().create_index([("created_at", ASCENDING)])
    signups().create_index([("status", ASCENDING), ("updated_at", ASCENDING)])
    messages().create_index([("approval_id", ASCENDING), ("status", ASCENDING)])

    warnings = []
    for name, (coll_name, definition) in VECTOR_INDEXES.items():
        warning = _ensure_vector_index(coll_name, name, definition)
        if warning:
            warnings.append(warning)
    return warnings


def _ensure_vector_index(coll_name: str, name: str, definition: dict) -> str | None:
    db = get_db()
    if coll_name not in db.list_collection_names():
        db.create_collection(coll_name)
    coll = db[coll_name]
    try:
        existing = {ix["name"] for ix in coll.list_search_indexes()}
        if name in existing:
            return None
        coll.create_search_index(
            SearchIndexModel(definition=definition, name=name, type="vectorSearch")
        )
        return None
    except OperationFailure as e:
        payload = {"name": name, "type": "vectorSearch", "definition": definition}
        reason = (e.details or {}).get("errmsg", str(e))
        return (
            f"Could not create vector index '{name}' on '{coll_name}' ({e.code}: {reason})\n"
            f"Paste this into Atlas UI -> Atlas Search -> Create Index -> JSON editor:\n"
            f"{json.dumps(payload, indent=2)}"
        )


def vector_index_status() -> dict[str, str]:
    """index name -> status string (READY / BUILDING / missing / error)."""
    out = {}
    for name, (coll_name, _) in VECTOR_INDEXES.items():
        try:
            found = list(col(coll_name).list_search_indexes(name))
            out[name] = found[0].get("status", "unknown") if found else "missing"
        except OperationFailure as e:
            out[name] = f"error: {e.code}"
    return out
