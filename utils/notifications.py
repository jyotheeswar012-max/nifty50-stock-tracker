"""
utils/notifications.py  —  SMTP email + Twilio SMS helpers.

Secret key layout expected in .streamlit/secrets.toml:

    [smtp]
    host     = "smtp.gmail.com"
    port     = 587
    user     = "nifty50alerts@gmail.com"
    password = "xxxx xxxx xxxx xxxx"   # Gmail App Password
    from     = "Nifty50 Tracker <nifty50alerts@gmail.com>"

    [twilio]
    sid   = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    token = "your_auth_token"
    from  = "+1415XXXXXXX"

All secrets are read with .get() so missing config never crashes.
"""
from __future__ import annotations
import streamlit as st


def _ascii_safe(text: str) -> str:
    """Replace non-breaking spaces and any non-ASCII chars with ASCII equivalents.

    \\xa0 (non-breaking space) → regular space
    Rs. rupee symbol variants  → Rs.
    Any remaining non-ASCII    → replaced with '?'
    This prevents 'ascii codec can't encode' errors in smtplib.
    """
    text = text.replace("\xa0", " ")          # non-breaking space → space
    text = text.replace("\u20b9", "Rs.")       # ₹ → Rs.
    text = text.replace("\u20a8", "Rs.")       # ₨ → Rs.
    text = text.encode("ascii", errors="replace").decode("ascii")
    return text


# ---------------------------------------------------------------------------
# Config checks
# ---------------------------------------------------------------------------

def smtp_configured() -> bool:
    try:
        s = st.secrets.get("smtp", {})
        return bool(s.get("host") and s.get("user") and s.get("password"))
    except Exception:
        return False


def twilio_configured() -> bool:
    try:
        t = st.secrets.get("twilio", {})
        return bool(t.get("sid") and t.get("token") and t.get("from"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Send helpers
# ---------------------------------------------------------------------------

def send_email(to: str, subject: str, body: str) -> tuple[bool, str]:
    """Send a plain-text email via Gmail SMTP (or any STARTTLS host).

    Sanitises subject and body through _ascii_safe() before sending so that
    non-breaking spaces (\\xa0) or rupee symbols (\u20b9) never cause the
    'ascii codec can't encode' error that smtplib raises on some Python builds.
    """
    if not smtp_configured():
        return False, "SMTP not configured — add [smtp] to secrets.toml"
    try:
        import smtplib
        from email.message import EmailMessage

        # Sanitise — strip any non-ASCII that would crash the legacy SMTP path
        subject = _ascii_safe(subject)
        body    = _ascii_safe(body)

        s        = st.secrets["smtp"]
        port     = int(s.get("port", 587))
        from_hdr = _ascii_safe(s.get("from", s["user"]))

        msg = EmailMessage()
        msg["From"]    = from_hdr
        msg["To"]      = to
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(s["host"], port, timeout=12) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(s["user"], s["password"])
            srv.send_message(msg)

        return True, ""
    except Exception as exc:
        return False, str(exc)


def send_sms(to: str, body: str) -> tuple[bool, str]:
    """Send an SMS via Twilio."""
    if not twilio_configured():
        return False, "Twilio not configured — add [twilio] to secrets.toml"
    try:
        from twilio.rest import Client
        t   = st.secrets["twilio"]
        cli = Client(t["sid"], t["token"])
        cli.messages.create(body=_ascii_safe(body), from_=t["from"], to=to)
        return True, ""
    except Exception as exc:
        return False, str(exc)
