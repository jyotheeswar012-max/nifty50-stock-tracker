"""
utils/notifications.py  —  safe SMTP + Twilio helpers.
All secrets are read with .get() so missing config never crashes the app.
"""
from __future__ import annotations
import streamlit as st


def smtp_configured() -> bool:
    try:
        s = st.secrets.get("smtp", {})
        return bool(s.get("host") and s.get("user") and s.get("password"))
    except Exception:
        return False


def twilio_configured() -> bool:
    try:
        t = st.secrets.get("twilio", {})
        return bool(t.get("account_sid") and t.get("auth_token") and t.get("from_number"))
    except Exception:
        return False


def send_email(to: str, subject: str, body: str) -> tuple[bool, str]:
    if not smtp_configured():
        return False, "SMTP not configured"
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        s   = st.secrets["smtp"]
        msg = MIMEMultipart()
        msg["From"]    = s["user"]
        msg["To"]      = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        port = int(s.get("port", 587))
        with smtplib.SMTP(s["host"], port, timeout=10) as srv:
            srv.starttls()
            srv.login(s["user"], s["password"])
            srv.sendmail(s["user"], to, msg.as_string())
        return True, ""
    except Exception as e:
        return False, str(e)


def send_sms(to: str, body: str) -> tuple[bool, str]:
    if not twilio_configured():
        return False, "Twilio not configured"
    try:
        from twilio.rest import Client
        t   = st.secrets["twilio"]
        cli = Client(t["account_sid"], t["auth_token"])
        cli.messages.create(body=body, from_=t["from_number"], to=to)
        return True, ""
    except Exception as e:
        return False, str(e)
