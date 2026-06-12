"""
utils/notifications.py  —  Option B: Shared sender

The app owner configures ONE Gmail + ONE Twilio number in Streamlit Secrets.
Any user who saves their email / phone in the Profile page receives alerts
from that shared sender — they never need to set up credentials themselves.

Secrets required in .streamlit/secrets.toml or Streamlit Cloud Secrets:

  [smtp]
  host     = "smtp.gmail.com"
  port     = 587
  user     = "your_app_gmail@gmail.com"
  password = "xxxx xxxx xxxx xxxx"   # 16-char Gmail App Password
  from     = "Nifty50 Tracker <your_app_gmail@gmail.com>"

  [twilio]
  sid   = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  token = "your_auth_token"
  from  = "+1415XXXXXXX"

Both functions return (success: bool, error_message: str).
"""
from __future__ import annotations

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Tuple

import requests
import streamlit as st


def _smtp_cfg() -> dict:
    """Read SMTP config from Streamlit secrets. Raises KeyError if missing."""
    return st.secrets["smtp"]


def _twilio_cfg() -> dict:
    """Read Twilio config from Streamlit secrets. Raises KeyError if missing."""
    return st.secrets["twilio"]


def smtp_configured() -> bool:
    """Returns True if SMTP secrets exist and are non-empty."""
    try:
        cfg = _smtp_cfg()
        return bool(cfg.get("host") and cfg.get("user") and cfg.get("password"))
    except Exception:
        return False


def twilio_configured() -> bool:
    """Returns True if Twilio secrets exist and are non-empty."""
    try:
        cfg = _twilio_cfg()
        return bool(cfg.get("sid") and cfg.get("token") and cfg.get("from"))
    except Exception:
        return False


def send_email(
    to_addr: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> Tuple[bool, str]:
    """
    Send an email FROM the shared app Gmail TO the user's address.
    Supports optional HTML body (falls back to plain text).
    """
    if not to_addr or "@" not in to_addr:
        return False, "Invalid recipient email address."

    try:
        cfg       = _smtp_cfg()
        host      = cfg["host"]
        port      = int(cfg["port"])
        user      = cfg["user"]
        password  = cfg["password"]
        from_addr = cfg.get("from", user)
    except (KeyError, Exception) as e:
        return False, f"SMTP not configured by app owner: {e}"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = from_addr
        msg["To"]      = to_addr
        msg.attach(MIMEText(body, "plain", "utf-8"))
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(user, password)
            server.sendmail(from_addr, to_addr, msg.as_string())
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed. Check Gmail App Password in secrets."
    except smtplib.SMTPRecipientsRefused:
        return False, f"Recipient refused: {to_addr}"
    except Exception as e:
        return False, str(e)


def send_sms(
    to_number: str,
    body: str,
) -> Tuple[bool, str]:
    """
    Send an SMS FROM the shared Twilio number TO the user's phone.
    Uses Twilio REST API directly (no SDK required).
    """
    if not to_number or not to_number.startswith("+"):
        return False, "Phone number must be in E.164 format (+91XXXXXXXXXX)."

    try:
        cfg      = _twilio_cfg()
        sid      = cfg["sid"]
        token    = cfg["token"]
        from_num = cfg["from"]
    except (KeyError, Exception) as e:
        return False, f"Twilio not configured by app owner: {e}"

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
        try:
            err_msg = resp.json().get("message", resp.text)
        except Exception:
            err_msg = resp.text
        return False, err_msg
    except requests.Timeout:
        return False, "Twilio request timed out."
    except Exception as e:
        return False, str(e)
