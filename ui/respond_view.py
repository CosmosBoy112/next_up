"""Landing page for the signed link in request emails: /?respond=<token>.

Opening the link only shows the request; accepting or declining takes an explicit
click, so mail scanners that prefetch links can't respond on someone's behalf.
"""

from __future__ import annotations

import streamlit as st

from core import actions, db, notify, repo
from ui.common import STATUS_CHIPS, when


def render(token: str) -> None:
    try:
        message_id = notify.verify_token(token)
    except ValueError:
        st.error("This link is invalid or has expired. Open NextUp to see your requests.")
        return
    message = db.messages().find_one({"_id": message_id})
    shift = repo.get_shift(message["shift_id"]) if message else None
    volunteer = repo.get_volunteer(message["to_volunteer_id"]) if message else None
    if not (message and shift and volunteer):
        st.error("We couldn't find this request.")
        return

    st.title(f"Hi {volunteer['name'].split()[0]}")
    with st.container(border=True):
        st.markdown(f"#### {shift['title']}")
        st.caption(f"{when(shift['start'], shift['end'])} · {shift['location']}")
        st.write(message["body"])

    if message.get("kind") == "notice":
        return  # updates need no response
    if message["status"] != "sent":
        st.info(f"This request is already {STATUS_CHIPS.get(message['status'], message['status'])}.")
        return
    left, right, _ = st.columns([1, 1, 3])
    if left.button("Accept", type="primary", width="stretch"):
        result = actions.accept_message(message_id)
        (st.success if result.ok else st.info)(result.message)
    if right.button("Decline", width="stretch"):
        st.info(actions.decline_message(message_id).message)
