"""Email notifications: provider adapters, message rendering, and signed response links.

Delivery is never triggered by the agent. core.actions.approve() queues an email
on each message it creates (outbox), and notifier.py delivers the queue.

Configuration (all optional; defaults are safe for local dev):
  EMAIL_PROVIDER       console | smtp | resend      (default: console = log only, send nothing)
  EMAIL_FROM           sender, e.g. "NextUp <noreply@yourdomain.org>"
  EMAIL_REDIRECT_TO    if set, every email goes to this address instead of the volunteer
                       (use for demos/staging; the intended recipient is shown in the subject)
  APP_URL              base URL for response links (default http://localhost:8501)
  RESPONSE_LINK_SECRET HMAC key for response links (required for real providers)
  RESPONSE_LINK_TTL_HOURS  link lifetime (default 168 = 7 days)
  SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD, SMTP_STARTTLS (true)
  RESEND_API_KEY
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import smtplib
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from email.message import EmailMessage
from html import escape

from bson import ObjectId

from core import config  # noqa: F401  (loads .env)
from core.repo import to_local

DEV_SECRET = "dev-only-insecure-secret"


@dataclass
class Email:
    to: str
    subject: str
    text: str
    html: str


class DeliveryError(Exception):
    """Provider rejected or failed to send. `permanent` errors are not retried."""

    def __init__(self, message: str, permanent: bool = False):
        super().__init__(message)
        self.permanent = permanent


# ---------- settings ----------

def provider() -> str:
    return os.getenv("EMAIL_PROVIDER", "console").strip().lower() or "console"


def app_url() -> str:
    return os.getenv("APP_URL", "http://localhost:8501").rstrip("/")


def _secret() -> bytes:
    secret = os.getenv("RESPONSE_LINK_SECRET", "").strip()
    if not secret:
        if provider() != "console":
            raise DeliveryError("RESPONSE_LINK_SECRET must be set for real email providers",
                                permanent=True)
        secret = DEV_SECRET
    return secret.encode()


# ---------- signed response links ----------

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_token(message_id: ObjectId | str, ttl_hours: float | None = None) -> str:
    ttl = ttl_hours if ttl_hours is not None else float(os.getenv("RESPONSE_LINK_TTL_HOURS", "168"))
    payload = f"{message_id}.{int(time.time() + ttl * 3600)}".encode()
    sig = hmac.new(_secret(), payload, hashlib.sha256).digest()[:16]
    return f"{_b64(payload)}.{_b64(sig)}"


def verify_token(token: str) -> ObjectId:
    """Return the message id, or raise ValueError if the link is invalid or expired."""
    try:
        payload_b64, sig_b64 = token.split(".")
        payload = _unb64(payload_b64)
        expected = hmac.new(_secret(), payload, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(expected, _unb64(sig_b64)):
            raise ValueError("bad signature")
        message_id, expires = payload.decode().split(".")
        if time.time() > int(expires):
            raise ValueError("expired")
        return ObjectId(message_id)
    except ValueError:
        raise
    except Exception as e:  # noqa: BLE001 - any malformed token is just invalid
        raise ValueError("malformed") from e


def response_link(message_id: ObjectId | str) -> str:
    return f"{app_url()}/?respond={make_token(message_id)}"


# ---------- rendering ----------

def render(message: dict, volunteer: dict, shift: dict, org: str) -> Email:
    """Any coordinator-approved message -> email."""
    if message.get("kind") == "notice":
        return render_notice(message, volunteer, shift, org)
    return render_request(message, volunteer, shift, org)


def _address(volunteer: dict, subject: str) -> tuple[str, str]:
    to = volunteer["email"]
    redirect = os.getenv("EMAIL_REDIRECT_TO", "").strip()
    if redirect:
        return redirect, f"[to {volunteer['name']} <{to}>] {subject}"
    return to, subject


def _shift_card(shift: dict, when: str) -> str:
    return f"""<div style="border:1px solid #e4e7f2;border-radius:12px;padding:16px;margin:20px 0">
    <div style="font-weight:700;font-size:17px">{escape(shift['title'])}</div>
    <div style="color:#5b6080;margin-top:4px">{escape(when)}</div>
    <div style="color:#5b6080">{escape(shift['location'])}</div>
  </div>"""


def _when(shift: dict) -> str:
    start, end = to_local(shift["start"]), to_local(shift["end"])
    return f"{start:%A, %B %-d} · {start:%-I:%M %p}–{end:%-I:%M %p}"


def render_notice(message: dict, volunteer: dict, shift: dict, org: str) -> Email:
    """Coordinator-approved update for a confirmed crew (e.g. weather plan). No response needed."""
    when = _when(shift)
    to, subject = _address(volunteer, f"Update: {shift['title']}, {to_local(shift['start']):%a %b %-d}")
    footer = f"Sent by the {org} volunteer coordinator. Reply to this email with any questions."
    text = f"{message['body']}\n\n{shift['title']}\n{when}\n{shift['location']}\n\n{footer}"
    html = f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:auto;color:#1f2547">
  <p style="font-size:16px;line-height:1.5">{escape(message['body'])}</p>
  {_shift_card(shift, when)}
  <p style="color:#8a8fa8;font-size:12px;margin-top:24px">{escape(footer)}</p>
</div>"""
    return Email(to=to, subject=subject, text=text, html=html)


def render_request(message: dict, volunteer: dict, shift: dict, org: str) -> Email:
    """Coordinator-approved request -> email. Body is the (possibly edited) draft."""
    when = _when(shift)
    link = response_link(message["_id"])
    to, subject = _address(volunteer, f"Can you help? {shift['title']}, "
                                      f"{to_local(shift['start']):%a %b %-d}")
    text = (f"{message['body']}\n\n{shift['title']}\n{when}\n{shift['location']}\n\n"
            f"Accept or decline: {link}\n\n"
            f"Sent by the {org} volunteer coordinator. Reply to this email with any questions.")
    html = f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:auto;color:#1f2547">
  <p style="font-size:16px;line-height:1.5">{escape(message['body'])}</p>
  {_shift_card(shift, when)}
  <a href="{escape(link)}" style="display:inline-block;background:#5b5ff0;color:#fff;
     text-decoration:none;padding:12px 22px;border-radius:10px;font-weight:700">Respond</a>
  <p style="color:#8a8fa8;font-size:12px;margin-top:24px">
    Sent by the {escape(org)} volunteer coordinator. Reply to this email with any questions.</p>
</div>"""
    return Email(to=to, subject=subject, text=text, html=html)


# ---------- providers ----------

def send(email: Email) -> str:
    """Send via the configured provider. Returns a provider message id (or a note)."""
    sender = os.getenv("EMAIL_FROM", "NextUp <noreply@example.org>")
    name = provider()
    if name == "console":
        print(f"[email:console] to={email.to} subject={email.subject!r}", flush=True)
        return "console"
    if name == "smtp":
        return _send_smtp(email, sender)
    if name == "resend":
        return _send_resend(email, sender)
    raise DeliveryError(f"unknown EMAIL_PROVIDER '{name}'", permanent=True)


def _send_smtp(email: Email, sender: str) -> str:
    host = os.getenv("SMTP_HOST", "")
    if not host:
        raise DeliveryError("SMTP_HOST is not set", permanent=True)
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = sender, email.to, email.subject
    msg.set_content(email.text)
    msg.add_alternative(email.html, subtype="html")
    try:
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=20) as smtp:
            if os.getenv("SMTP_STARTTLS", "true").lower() != "false":
                smtp.starttls()
            if os.getenv("SMTP_USER"):
                smtp.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", ""))
            smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise DeliveryError(f"SMTP auth failed ({e.smtp_code})", permanent=True) from e
    except smtplib.SMTPRecipientsRefused as e:
        raise DeliveryError("recipient refused", permanent=True) from e
    except (smtplib.SMTPException, OSError) as e:
        raise DeliveryError(f"SMTP error: {type(e).__name__}: {e}") from e
    return msg.get("Message-ID", "smtp")


def _send_resend(email: Email, sender: str) -> str:
    key = os.getenv("RESEND_API_KEY", "")
    if not key:
        raise DeliveryError("RESEND_API_KEY is not set", permanent=True)
    body = json.dumps({"from": sender, "to": [email.to], "subject": email.subject,
                       "text": email.text, "html": email.html}).encode()
    req = urllib.request.Request("https://api.resend.com/emails", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read() or b"{}").get("id", "resend")
    except urllib.error.HTTPError as e:
        detail = e.read()[:200].decode(errors="replace")
        # 4xx (except rate limit) won't succeed on retry
        raise DeliveryError(f"Resend HTTP {e.code}: {detail}",
                            permanent=400 <= e.code < 500 and e.code != 429) from e
    except (urllib.error.URLError, OSError) as e:
        raise DeliveryError(f"Resend network error: {e}") from e
