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
"""
from __future__ import annotations
import streamlit as st


def _scrub(text: str) -> str:
    """Replace every non-ASCII byte with a plain-ASCII equivalent."""
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
    """Send a plain-text email via Gmail SMTP.

    Builds the MIME message manually as a UTF-8 encoded bytes object so
    smtplib NEVER touches the subject/body through its ASCII codec path.
    srv.sendmail() receives raw bytes — no encoding happens inside smtplib.
    """
    if not smtp_configured():
        return False, "SMTP not configured — add [smtp] to secrets.toml"
    try:
        import smtplib

        s        = st.secrets["smtp"]
        port     = int(s.get("port", 587))
        from_addr = _scrub(str(s.get("from", s["user"])))

        # Scrub all user-supplied strings
        subject   = _scrub(str(subject))
        body      = _scrub(str(body))

        # Build raw RFC-2822 message as bytes — UTF-8 throughout.
        # We never call msg.as_string() which triggers the ASCII codec.
        raw = (
            f"From: {from_addr}\r\n"
            f"To: {to}\r\n"
            f"Subject: {subject}\r\n"
            f"MIME-Version: 1.0\r\n"
            f"Content-Type: text/plain; charset=utf-8\r\n"
            f"Content-Transfer-Encoding: 8bit\r\n"
            f"\r\n"
            f"{body}\r\n"
        ).encode("utf-8")

        with smtplib.SMTP(s["host"], port, timeout=12) as srv:
            srv.ehlo()
            srv.starttls()
            srv.ehlo()
            srv.login(s["user"], s["password"])
            # sendmail() with bytes skips all internal encoding in smtplib
            srv.sendmail(from_addr, [to], raw)

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
