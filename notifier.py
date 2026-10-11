"""Outbox delivery worker: sends queued emails for coordinator-approved requests.

Usage: python notifier.py

- Wakes on inserts into `messages` via a change stream (no polling), and also sweeps
  every few seconds for due retries and anything queued while it was down.
- Each email is claimed atomically (queued -> sending), so running two notifiers
  never sends the same email twice.
- Transient failures retry with exponential backoff; permanent ones are marked failed.
- Provider is chosen by EMAIL_PROVIDER (see core/notify.py); default "console" sends nothing.
"""

from __future__ import annotations

import threading
import time
import traceback
from datetime import timedelta

from pymongo import ReturnDocument
from pymongo.errors import OperationFailure, PyMongoError

from core import db, notify, repo
from scripts.seed import ORG

MAX_ATTEMPTS = 5
SWEEP_SECONDS = 5
STALE_SENDING = timedelta(minutes=2)  # a crashed send gets retried after this

wake = threading.Event()


def log(msg: str) -> None:
    print(f"{repo.to_local(repo.now_utc()):%H:%M:%S} {msg}", flush=True)


def claim_next() -> dict | None:
    now = repo.now_utc()
    return db.messages().find_one_and_update(
        {"$or": [
            {"delivery.email.status": "queued", "delivery.email.next_attempt_at": {"$lte": now}},
            {"delivery.email.status": "sending", "delivery.email.claimed_at": {"$lt": now - STALE_SENDING}},
        ]},
        {"$set": {"delivery.email.status": "sending", "delivery.email.claimed_at": now},
         "$inc": {"delivery.email.attempts": 1}},
        sort=[("delivery.email.next_attempt_at", 1)],
        return_document=ReturnDocument.AFTER,
    )


def deliver(message: dict) -> None:
    state = message["delivery"]["email"]
    volunteer = repo.get_volunteer(message["to_volunteer_id"])
    shift = repo.get_shift(message["shift_id"])
    update: dict
    try:
        if volunteer is None or shift is None or not volunteer.get("email"):
            raise notify.DeliveryError("volunteer, shift, or email address missing", permanent=True)
        email = notify.render(message, volunteer, shift, ORG)
        provider_id = notify.send(email)
        update = {"delivery.email.status": "sent", "delivery.email.sent_at": repo.now_utc(),
                  "delivery.email.provider": notify.provider(),
                  "delivery.email.provider_id": provider_id, "delivery.email.to": email.to,
                  "delivery.email.error": None}
        log(f"[sent] {notify.provider()} -> {email.to} ({volunteer['name']}, {shift['title']})")
    except notify.DeliveryError as e:
        attempts = state.get("attempts", 1)
        final = e.permanent or attempts >= MAX_ATTEMPTS
        backoff = timedelta(seconds=30 * 2 ** (attempts - 1))
        update = {"delivery.email.status": "failed" if final else "queued",
                  "delivery.email.error": str(e)[:300],
                  "delivery.email.next_attempt_at": repo.now_utc() + backoff}
        log(f"[{'failed' if final else 'retry'}] message {message['_id']} attempt {attempts}: {e}")
    db.messages().update_one({"_id": message["_id"]}, {"$set": update})


def drain() -> int:
    n = 0
    while (message := claim_next()) is not None:
        try:
            deliver(message)
        except Exception:  # noqa: BLE001 - never die; leave it to the stale-claim retry
            log("[error] delivery crashed:\n" + traceback.format_exc())
        n += 1
    return n


def watch_inserts() -> None:
    """Change stream: wake the sender as soon as an approved request is inserted."""
    pipeline = [{"$match": {"operationType": "insert",
                            "fullDocument.delivery.email.status": "queued"}}]
    while True:
        try:
            with db.messages().watch(pipeline) as stream:
                log("[notifier] watching messages change stream")
                for _ in stream:
                    wake.set()
        except OperationFailure as e:
            log(f"[notifier] change stream unavailable ({e.code}); sweeping every {SWEEP_SECONDS}s")
            return
        except PyMongoError as e:
            log(f"[notifier] change stream error: {e}; reconnecting in 3s")
            time.sleep(3)


def main() -> None:
    db.messages().create_index([("delivery.email.status", 1), ("delivery.email.next_attempt_at", 1)])
    log(f"[notifier] provider={notify.provider()} app_url={notify.app_url()}")
    threading.Thread(target=watch_inserts, daemon=True).start()
    while True:
        try:
            drain()
        except PyMongoError as e:
            log(f"[notifier] mongo error: {e}")
        except KeyboardInterrupt:
            return
        wake.wait(SWEEP_SECONDS)
        wake.clear()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("[notifier] bye")
