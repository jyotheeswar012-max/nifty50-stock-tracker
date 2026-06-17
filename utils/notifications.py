"""
utils/notifications.py  —  SMTP email helpers.
"""
from __future__ import annotations
import streamlit as st

# _CACHE_BUST = 4   # increment to force .pyc regeneration

def _scrub(text: str) -> str:
    s = str(text)
    # Kill every known non-ASCII offender explicitly
    s = s.replace("\xa0", " ")      # non-breaking space
    s = s.replace("\u00a0", " ")    # same, via unicode name
    s = s.replace("\u20b9", "Rs.")  # rupee
    s = s.replace("\u20a8", "Rs.")  # rupee legacy
    s = s.replace("\u2013", "-")    # en-dash
    s = s.replace("\u2014", "-")    # em-dash
    # Nuclear option: drop anything still non-ASCII
    return s.encode("ascii", errors="ignore").decode("ascii")


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


def send_email(to: str, subject: str, body: str) -> tuple[bool, str]:
    if not smtp_configured():
        return False, "SMTP not configured"
    try:
        import smtplib
        s         = st.secrets["smtp"]
        port      = int(s.get("port", 587))
        from_addr = _scrub(str(s.get("from", s["user"])))
        subject   = _scrub(str(subject))
        body      = _scrub(str(body))
        to        = _scrub(str(to))

        # Build raw bytes — bypasses smtplib's ASCII codec entirely
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
            srv.sendmail(from_addr, [to], raw)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def send_sms(to: str, body: str) -> tuple[bool, str]:
    if not twilio_configured():
        return False, "Twilio not configured"
    try:
        from twilio.rest import Client
        t = st.secrets["twilio"]
        Client(t["sid"], t["token"]).messages.create(
            body=_scrub(body), from_=t["from"], to=to
        )
        return True, ""
    except Exception as exc:
        return False, str(exc)
