"""
utils/notifications.py

Provides two functions used by the Alerts page:
  send_email(to_addr, subject, body)  — via SMTP (Gmail or any SMTP)
  send_sms(to_number, body)           — via Twilio REST API

Credentials are read from Streamlit secrets:
  [smtp]   host, port, user, password, from
  [twilio] sid, token, from

Both functions return (success: bool, error_message: str).
"""
from __future__ import annotations

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Tuple

import streamlit as st


def send_email(
    to_addr: str,
    subject: str,
    body: str,
) -> Tuple[bool, str]:
    """
    Send a plain-text email via SMTP.
    Reads config from st.secrets['smtp'].
    Returns (True, "") on success, (False, error_str) on failure.
    """
    try:
        cfg = st.secrets["smtp"]
        host     = cfg["host"]
        port     = int(cfg["port"])
        user     = cfg["user"]
        password = cfg["password"]
        from_addr = cfg.get("from", user)
    except (KeyError, Exception) as e:
        return False, f"SMTP secrets not configured: {e}"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = from_addr
        msg["To"]      = to_addr
        msg.attach(MIMEText(body, "plain", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(user, password)
            server.sendmail(from_addr, to_addr, msg.as_string())
        return True, ""
    except Exception as e:
        return False, str(e)


def send_sms(
    to_number: str,
    body: str,
) -> Tuple[bool, str]:
    """
    Send an SMS via Twilio REST API.
    Reads config from st.secrets['twilio'].
    Returns (True, "") on success, (False, error_str) on failure.

    Uses requests directly to avoid requiring the full twilio SDK
    (reduces cold-start time on Streamlit Cloud).
    """
    import requests  # stdlib-like, already in requirements

    try:
        cfg       = st.secrets["twilio"]
        sid       = cfg["sid"]
        token     = cfg["token"]
        from_num  = cfg["from"]
    except (KeyError, Exception) as e:
        return False, f"Twilio secrets not configured: {e}"

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    try:
        resp = requests.post(
            url,
            auth=(sid, token),
            data={"From": from_num, "To": to_number, "Body": body},
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return True, ""
        data = resp.json()
        return False, data.get("message", resp.text)
    except Exception as e:
        return False, str(e)
