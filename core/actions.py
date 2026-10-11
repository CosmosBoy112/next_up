"""Business logic behind coordinator/volunteer buttons. These perform the real writes;
the agent itself never calls them."""

from __future__ import annotations

from dataclasses import dataclass

from bson import ObjectId
from pymongo.client_session import ClientSession

from core import db, repo
from core.repo import now_utc, oid


@dataclass
class Result:
    ok: bool
    message: str


def approve(approval_id: str | ObjectId, selected_ids: list[str],
            edited_drafts: dict[str, str] | None = None, note: str = "") -> Result:
    """Send messages to the selected candidates and mark the approval approved."""
    edited_drafts = edited_drafts or {}
    selected = {str(v) for v in selected_ids}
    if not selected:
        return Result(False, "Select at least one candidate.")
    # Atomic pending -> approved flip: a double click can't send twice.
    approval = db.approvals().find_one_and_update(
        {"_id": oid(approval_id), "status": "pending"},
        {"$set": {"status": "approved", "decided_at": now_utc(), "coordinator_note": note}},
    )
    if approval is None:
        return Result(False, "This proposal was already decided.")

    now = now_utc()
    candidates, outgoing = [], []
    for c in approval["candidates"]:
        vid = str(c["volunteer_id"])
        draft = (edited_drafts.get(vid) or c["draft_message"]).strip()
        is_selected = vid in selected
        candidates.append(c | {"draft_message": draft, "selected": is_selected})
        if is_selected:
            outgoing.append({
                "approval_id": approval["_id"], "shift_id": approval["shift_id"],
                "to_volunteer_id": c["volunteer_id"], "body": draft,
                "status": "sent", "sent_at": now, "responded_at": None,
            })
    db.approvals().update_one({"_id": approval["_id"]}, {"$set": {"candidates": candidates}})
    if outgoing:
        db.messages().insert_many(outgoing)
    return Result(True, f"Sent {len(outgoing)} request(s).")


def reject(approval_id: str | ObjectId, note: str = "") -> Result:
    res = db.approvals().update_one(
        {"_id": oid(approval_id), "status": "pending"},
        {"$set": {"status": "rejected", "decided_at": now_utc(), "coordinator_note": note}},
    )
    return Result(bool(res.modified_count),
                  "Proposal rejected." if res.modified_count else "Already decided.")


def accept_message(message_id: str | ObjectId) -> Result:
    """Volunteer accepts a request. Runs in a transaction so concurrent accepts
    can't overfill a shift (both touch the shift doc -> write conflict -> retry)."""
    with db.get_client().start_session() as session:
        return session.with_transaction(lambda s: _accept_txn(s, oid(message_id)))


def _accept_txn(s: ClientSession, message_id: ObjectId) -> Result:
    now = now_utc()
    msg = db.messages().find_one({"_id": message_id}, session=s)
    if msg is None or msg["status"] != "sent":
        return Result(False, "This request is no longer open.")
    shift_id = msg["shift_id"]
    # Lock: every accept writes the shift doc first, so concurrent txns conflict.
    shift = db.shifts().find_one_and_update(
        {"_id": shift_id}, {"$inc": {"accept_version": 1}}, session=s)
    if shift is None or shift["status"] == "cancelled":
        _set_msg(s, message_id, "withdrawn", now)
        return Result(False, "Sorry, this shift was cancelled.")

    confirmed = db.signups().count_documents(
        {"shift_id": shift_id, "status": "confirmed"}, session=s)
    if confirmed >= shift["required_count"]:
        _set_msg(s, message_id, "withdrawn", now)
        return Result(False, "Thanks so much! This shift just got filled, so you're off the hook.")

    already = db.signups().find_one(
        {"shift_id": shift_id, "volunteer_id": msg["to_volunteer_id"], "status": "confirmed"},
        session=s)
    if already is None:
        db.signups().insert_one({
            "shift_id": shift_id, "volunteer_id": msg["to_volunteer_id"], "status": "confirmed",
            "source": "agent", "created_at": now, "updated_at": now,
        }, session=s)
        confirmed += 1
    _set_msg(s, message_id, "accepted", now)

    full = confirmed >= shift["required_count"]
    db.shifts().update_one({"_id": shift_id},
                           {"$set": {"status": "filled" if full else "open"}}, session=s)
    if full:
        db.messages().update_many(
            {"shift_id": shift_id, "status": "sent", "_id": {"$ne": message_id}},
            {"$set": {"status": "withdrawn", "responded_at": now}}, session=s)
    return Result(True, f"You're confirmed for {shift['title']}. Thank you!")


def _set_msg(s: ClientSession, message_id: ObjectId, status: str, now) -> None:
    db.messages().update_one({"_id": message_id},
                             {"$set": {"status": status, "responded_at": now}}, session=s)


def decline_message(message_id: str | ObjectId) -> Result:
    msg = db.messages().find_one_and_update(
        {"_id": oid(message_id), "status": "sent"},
        {"$set": {"status": "declined", "responded_at": now_utc()}},
    )
    if msg is None:
        return Result(False, "This request is no longer open.")
    still_waiting = db.messages().count_documents(
        {"approval_id": msg["approval_id"], "status": "sent"})
    shift = db.shifts().find_one({"_id": msg["shift_id"]}, {"required_count": 1, "status": 1})
    if (still_waiting == 0 and shift and shift["status"] != "cancelled"
            and repo.confirmed_count(shift["_id"]) < shift["required_count"]):
        # Event-driven re-trigger: worker.py watches inserts on agent_triggers.
        db.agent_triggers().insert_one({
            "type": "vacancy_retry", "shift_id": shift["_id"],
            "approval_id": msg["approval_id"], "created_at": now_utc(),
        })
    return Result(True, "No problem, thanks for letting us know.")
