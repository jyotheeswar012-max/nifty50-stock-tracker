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

    Uses UTF-8 throughout so non-ASCII characters (₹, emoji, etc.)
    never trigger the 'ascii codec can't encode' error.
    """
    if not smtp_configured():
        return False, "SMTP not configured — add [smtp] to secrets.toml"
    try:
        import smtplib
        from email.headerregistry import Address
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.header import Header

        s        = st.secrets["smtp"]
        from_hdr = s.get("from", s["user"])
        port     = int(s.get("port", 587))

        msg          = MIMEMultipart()
        msg["From"]  = from_hdr
        msg["To"]    = to
        # Encode subject as UTF-8 quoted-printable so ₹ / emoji survive
        msg["Subject"] = Header(subject, charset="utf-8")
        # _charset="utf-8" ensures the body is encoded as UTF-8, not ASCII
        msg.attach(MIMEText(body, "plain", _charset="utf-8"))

        with smtplib.SMTP(s["host"], port, timeout=12) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(s["user"], s["password"])
            # as_bytes() uses the charset declared in each MIME part (UTF-8)
            srv.sendmail(s["user"], to, msg.as_bytes().decode("utf-8", errors="replace"))
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
        cli.messages.create(body=body, from_=t["from"], to=to)
        return True, ""
    except Exception as exc:
        return False, str(exc)
