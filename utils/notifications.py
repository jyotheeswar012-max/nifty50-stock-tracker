"""
utils/notifications.py  —  SMTP email and Twilio SMS helpers.

Both send_email() and send_sms() are guarded by process-wide sliding-window
rate limiters (utils.rate_limit) so runaway alert loops cannot exhaust SMTP
quotas or Twilio free-tier SMS budgets.
"""
from __future__ import annotations
import streamlit as st

from utils.rate_limit import smtp_limiter, twilio_limiter
from utils.logger import get_logger

log = get_logger(__name__)


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
    """Send an email alert.

    Returns (True, "") on success, (False, reason) on any failure.
    Guarded by smtp_limiter: returns (False, 'rate limit') without
    hitting the SMTP server when the 5-minute window is full.
    """
    if not smtp_configured():
        return False, "SMTP not configured"

    # --- Rate-limit guard ---
    ok, wait = smtp_limiter.check()
    if not ok:
        log.warning(
            "send_email: smtp_limiter cap hit (to=%s wait=%.1fs) — suppressed",
            to, wait,
        )
        return False, f"rate limit: too many emails sent, retry in {wait:.0f}s"

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
        log.info("send_email: sent to %s subject=%r", to, subject)
        return True, ""
    except Exception as exc:
        log.error("send_email failed: to=%s error=%s", to, exc, exc_info=True)
        return False, str(exc)


def send_sms(to: str, body: str) -> tuple[bool, str]:
    """Send an SMS alert via Twilio.

    Returns (True, "") on success, (False, reason) on any failure.
    Guarded by twilio_limiter: returns (False, 'rate limit') without
    hitting the Twilio API when the 5-minute window is full.
    """
    if not twilio_configured():
        return False, "Twilio not configured"

    # --- Rate-limit guard ---
    ok, wait = twilio_limiter.check()
    if not ok:
        log.warning(
            "send_sms: twilio_limiter cap hit (to=%s wait=%.1fs) — suppressed",
            to, wait,
        )
        return False, f"rate limit: too many SMS sent, retry in {wait:.0f}s"

    try:
        from twilio.rest import Client
        t = st.secrets["twilio"]
        Client(t["sid"], t["token"]).messages.create(
            body=_scrub(body), from_=t["from"], to=to
        )
        log.info("send_sms: sent to %s", to)
        return True, ""
    except Exception as exc:
        log.error("send_sms failed: to=%s error=%s", to, exc, exc_info=True)
        return False, str(exc)
