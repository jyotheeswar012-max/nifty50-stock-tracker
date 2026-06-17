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
import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header


def _scrub(text: str) -> str:
    """Replace every non-ASCII byte with a plain-ASCII equivalent.

    Covers the most common culprits from Indian-locale environments:
      \\xa0  non-breaking space     -> regular space
      \u20b9 rupee sign             -> Rs.
      \u20a8 rupee sign (legacy)    -> Rs.
    Everything else that still isn't ASCII is dropped (errors='ignore').
    """
    return (
        text
        .replace("\xa0",  " ")
        .replace("\u20b9", "Rs.")
        .replace("\u20a8", "Rs.")
        .encode("ascii", errors="ignore")
        .decode("ascii")
    )


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

    Uses MIMEText with explicit utf-8 charset so the body can carry any
    Unicode safely, AND scrubs subject + body through _scrub() first so
    that \\xa0 / rupee symbols never reach the smtplib ASCII envelope.

    Subject is encoded with RFC-2047 Header() so even if a stray non-ASCII
    byte somehow survives _scrub(), Python handles it gracefully instead of
    raising UnicodeEncodeError.
    """
    if not smtp_configured():
        return False, "SMTP not configured — add [smtp] to secrets.toml"
    try:
        s        = st.secrets["smtp"]
        port     = int(s.get("port", 587))
        from_hdr = _scrub(str(s.get("from", s["user"])))

        # Scrub both fields — belt AND suspenders
        subject = _scrub(str(subject))
        body    = _scrub(str(body))

        msg = MIMEMultipart()
        msg["From"]    = from_hdr
        msg["To"]      = to
        # Header() handles any residual non-ASCII via RFC-2047 encoding
        msg["Subject"] = Header(subject, "utf-8")
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(s["host"], port, timeout=12) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(s["user"], s["password"])
            srv.sendmail(from_hdr, to, msg.as_string())

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
        cli.messages.create(body=_scrub(body), from_=t["from"], to=to)
        return True, ""
    except Exception as exc:
        return False, str(exc)
