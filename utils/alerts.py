"""
utils/alerts.py  —  Price alert storage + dispatch.

Alerts are stored per signed-in email in st.session_state["_alerts_by_user"] so
simple email login can keep each user's alerts separate for the current app session.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import pytz
import streamlit as st

from utils.notifications import send_email

IST = pytz.timezone("Asia/Kolkata")
_KEY = "_alerts_by_user"
_LOG = "_alert_log"


def _fmt(value: float) -> str:
    """Format a price as a plain ASCII string with comma thousands separator.

    Python's f"{x:,.2f}" can emit a non-breaking space (\xa0) as the
    thousands separator when the process locale uses it (common on some
    Linux/cloud environments).  Building the string manually guarantees
    only ASCII characters, which keeps SMTP transport happy.
    """
    # Round to 2 dp, then split on decimal point
    integer_part, decimal_part = f"{value:.2f}".split(".")
    # Insert commas every 3 digits from the right (Indian-style not needed;
    # standard international format is fine for email)
    chars = list(integer_part)
    for i in range(len(chars) - 3, 0, -3):
        chars.insert(i, ",")
    return "".join(chars) + "." + decimal_part


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _all_alerts() -> dict[str, list[dict]]:
    return st.session_state.setdefault(_KEY, {})


def get_alerts(user_email: str) -> list[dict]:
    return list(_all_alerts().get(user_email, []))


def add_alert(stock: str, symbol: str, direction: str, threshold: float,
              email: str, phone: str = "") -> None:
    email = email.strip().lower()
    alerts_by_user = _all_alerts()
    alerts = alerts_by_user.setdefault(email, [])
    alerts.append({
        "id": str(uuid.uuid4())[:8],
        "stock": stock,
        "symbol": symbol,
        "direction": direction,
        "threshold": threshold,
        "email": email,
        "phone": phone.strip(),
        "triggered": False,
        "created": datetime.now(IST).strftime("%H:%M:%S"),
    })


def remove_alert(alert_id: str, user_email: str) -> None:
    user_email = user_email.strip().lower()
    alerts_by_user = _all_alerts()
    alerts_by_user[user_email] = [
        a for a in alerts_by_user.get(user_email, []) if a["id"] != alert_id
    ]


def _append_log(user_email: str, msg: str) -> None:
    log_map = st.session_state.setdefault(_LOG, {})
    user_log = log_map.setdefault(user_email, [])
    ts = datetime.now(IST).strftime("%H:%M:%S")
    user_log.insert(0, f"[{ts}] {msg}")
    if len(user_log) > 50:
        user_log.pop()


# ---------------------------------------------------------------------------
# Alert firing
# ---------------------------------------------------------------------------

def fire_alerts(live_prices: dict[str, float], user_email: str) -> int:
    alerts = _all_alerts().get(user_email, [])
    fired = 0

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

        # Use _fmt() to guarantee ASCII-only price strings (no \xa0 thousands sep)
        threshold_str = _fmt(alert["threshold"])
        price_str     = _fmt(price)

        subject = f"Nifty50 Alert: {alert['stock']} {direction_word} Rs.{threshold_str}"
        body = (
            f"Your price alert has been triggered!\n\n"
            f"Stock     : {alert['stock']} ({alert['symbol']})\n"
            f"Condition : Price {direction_word} Rs.{threshold_str}\n"
            f"Current   : Rs.{price_str}\n"
            f"Time      : {datetime.now(IST).strftime('%d %b %Y %I:%M:%S %p IST')}\n\n"
            f"-- NSE & Nifty 50 Tracker"
        )

        log_parts = [f"Alert #{alert['id']} fired -- {alert['stock']} @ Rs.{price_str}"]
        ok, err = send_email(alert["email"], subject, body)
        log_parts.append(f"Email {'OK' if ok else 'FAILED: ' + err}")
        _append_log(user_email, " | ".join(log_parts))

    return fired
