"""
utils/notifications.py
Email (SMTP) and SMS (Twilio) notification helpers.
All functions fail gracefully when secrets are missing.
"""
from __future__ import annotations
import streamlit as st


def smtp_configured() -> bool:
    """Return True only when all required SMTP secrets exist."""
    try:
        s = st.secrets["smtp"]
        return bool(s.get("host") and s.get("user") and s.get("password"))
    except Exception:
        return False


def twilio_configured() -> bool:
    """Return True only when all required Twilio secrets exist."""
    try:
        t = st.secrets["twilio"]
        return bool(t.get("account_sid") and t.get("auth_token") and t.get("from_number"))
    except Exception:
        return False


def send_email(to: str, subject: str, body: str) -> tuple[bool, str]:
    """Send an email via SMTP. Returns (ok, message)."""
    if not smtp_configured():
        return False, "SMTP not configured — add [smtp] secrets."
    try:
        import smtplib
        from email.mime.text import MIMEText
        cfg  = st.secrets["smtp"]
        host = str(cfg["host"])
        port = int(cfg.get("port", 587))
        user = str(cfg["user"])
        pwd  = str(cfg["password"])
        msg  = MIMEText(body)
        msg["Subject"] = subject
        msg["From"]    = user
        msg["To"]      = to
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.starttls()
            s.login(user, pwd)
            s.sendmail(user, [to], msg.as_string())
        return True, "Email sent."
    except Exception as e:
        return False, str(e)


def send_sms(to: str, body: str) -> tuple[bool, str]:
    """Send SMS via Twilio. Returns (ok, message)."""
    if not twilio_configured():
        return False, "Twilio not configured — add [twilio] secrets."
    try:
        from twilio.rest import Client
        cfg  = st.secrets["twilio"]
        cl   = Client(str(cfg["account_sid"]), str(cfg["auth_token"]))
        cl.messages.create(body=body, from_=str(cfg["from_number"]), to=to)
        return True, "SMS sent."
    except Exception as e:
        return False, str(e)
