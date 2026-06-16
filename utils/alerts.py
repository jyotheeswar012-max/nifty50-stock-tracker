"""
utils/alerts.py  —  Price alert storage + dispatch.

Each alert is a dict:
    {
        "id":        str,          # unique key
        "stock":     str,          # e.g. "Reliance Industries"
        "symbol":    str,          # e.g. "RELIANCE.NS"
        "direction": "above"|"below",
        "threshold": float,        # target price in Rs.
        "email":     str,          # user's email (may be empty)
        "phone":     str,          # user's E.164 phone (may be empty)
        "triggered": bool,         # True once fired
        "created":   str,          # ISO timestamp
    }

Alerts are stored in st.session_state["_alerts"] so they persist
for the session.  fire_alerts() is called on every auto-refresh.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import pytz
import streamlit as st

from utils.notifications import send_email, send_sms, smtp_configured, twilio_configured

IST = pytz.timezone("Asia/Kolkata")
_KEY = "_alerts"
_LOG = "_alert_log"


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def get_alerts() -> list[dict]:
    return st.session_state.get(_KEY, [])


def add_alert(stock: str, symbol: str, direction: str, threshold: float,
              email: str, phone: str) -> None:
    alerts = st.session_state.setdefault(_KEY, [])
    alerts.append({
        "id":        str(uuid.uuid4())[:8],
        "stock":     stock,
        "symbol":    symbol,
        "direction": direction,
        "threshold": threshold,
        "email":     email.strip(),
        "phone":     phone.strip(),
        "triggered": False,
        "created":   datetime.now(IST).strftime("%H:%M:%S"),
    })


def remove_alert(alert_id: str) -> None:
    st.session_state[_KEY] = [
        a for a in st.session_state.get(_KEY, []) if a["id"] != alert_id
    ]


def _append_log(msg: str) -> None:
    log = st.session_state.setdefault(_LOG, [])
    ts  = datetime.now(IST).strftime("%H:%M:%S")
    log.insert(0, f"[{ts}] {msg}")
    if len(log) > 50:
        log.pop()


# ---------------------------------------------------------------------------
# Alert firing
# ---------------------------------------------------------------------------

def fire_alerts(live_prices: dict[str, float]) -> int:
    """
    Check all active alerts against current prices.
    live_prices = {symbol: current_price}  e.g. {"RELIANCE.NS": 2950.5}

    Fires email and/or SMS for each triggered alert.
    Returns count of alerts fired this call.
    """
    alerts = st.session_state.get(_KEY, [])
    fired  = 0

    for alert in alerts:
        if alert["triggered"]:
            continue
        price = live_prices.get(alert["symbol"])
        if price is None:
            continue

        hit = (
            (alert["direction"] == "above" and price >= alert["threshold"]) or
            (alert["direction"] == "below" and price <= alert["threshold"])
        )
        if not hit:
            continue

        alert["triggered"] = True
        fired += 1

        direction_word = "crossed above" if alert["direction"] == "above" else "dropped below"
        subject = f"🔔 Nifty50 Alert: {alert['stock']} {direction_word} ₹{alert['threshold']:,.2f}"
        body = (
            f"Your price alert has been triggered!\n\n"
            f"Stock     : {alert['stock']} ({alert['symbol']})\n"
            f"Condition : Price {direction_word} ₹{alert['threshold']:,.2f}\n"
            f"Current   : ₹{price:,.2f}\n"
            f"Time      : {datetime.now(IST).strftime('%d %b %Y %I:%M:%S %p IST')}\n\n"
            f"— NSE & Nifty 50 Tracker"
        )
        sms_body = (
            f"Nifty50 Alert: {alert['stock']} {direction_word} "
            f"Rs.{alert['threshold']:,.0f}. Now Rs.{price:,.0f}."
        )

        log_parts = [f"Alert #{alert['id']} fired — {alert['stock']} @ ₹{price:,.2f}"]

        if alert["email"]:
            ok, err = send_email(alert["email"], subject, body)
            log_parts.append(f"Email {'✅' if ok else '❌ ' + err}")

        if alert["phone"]:
            ok, err = send_sms(alert["phone"], sms_body)
            log_parts.append(f"SMS {'✅' if ok else '❌ ' + err}")

        if not alert["email"] and not alert["phone"]:
            log_parts.append("(no contact — in-app only)")

        _append_log(" | ".join(log_parts))

    return fired
