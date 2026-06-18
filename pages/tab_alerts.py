"""Tab 7 — Price Alerts."""
import streamlit as st
from datetime import datetime

from utils.logger import get_logger
from utils.data import fetch_ticker
from utils.calculations import safe_float
from utils.constants import NIFTY50

log = get_logger(__name__)

_ALERT_KEY = "price_alerts"


def _get_alerts() -> list:
    return st.session_state.setdefault(_ALERT_KEY, [])


def _add_alert(symbol: str, name: str, condition: str, target: float) -> None:
    alerts = _get_alerts()
    alerts.append({
        "symbol": symbol,
        "name": name,
        "condition": condition,
        "target": target,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "triggered": False,
    })


def _check_alerts(alerts: list) -> list:
    triggered = []
    for a in alerts:
        if a["triggered"]:
            continue
        try:
            df = fetch_ticker(a["symbol"], "1d")
            if df.empty or "Close" not in df.columns:
                continue
            price = safe_float(df["Close"].iloc[-1])
            hit = (
                (a["condition"] == "above" and price >= a["target"]) or
                (a["condition"] == "below" and price <= a["target"])
            )
            if hit:
                a["triggered"] = True
                a["triggered_price"] = price
                triggered.append(a)
        except Exception as exc:
            log.warning("tab_alerts: check failed for %s: %s", a["symbol"], exc)
    return triggered


def render(build_stock_rows_cached):
    from utils.app_helpers import hero, divider
    hero("🔔 Price Alerts", "Set and monitor price threshold alerts")

    symbols = [s["symbol"] for s in NIFTY50]
    names   = [s["name"]   for s in NIFTY50]
    options = [f"{sym} — {nm}" for sym, nm in zip(symbols, names)]

    st.subheader("Add Alert")
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1:
        sel = st.selectbox("Stock", options, key="al_sym")
    with c2:
        condition = st.radio("Condition", ["above", "below"], key="al_cond")
    with c3:
        target = st.number_input("Target Price (Rs.)", min_value=0.01, value=1000.0, step=1.0, key="al_tgt")
    with c4:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        if st.button("Add Alert", key="al_add"):
            sym  = symbols[options.index(sel)]
            name = names[options.index(sel)]
            _add_alert(sym, name, condition, target)
            st.success(f"Alert added: {name} {condition} Rs.{target:,.2f}")

    divider()

    alerts = _get_alerts()
    if not alerts:
        st.info("No alerts set. Add one above.")
        return

    # Check current prices
    triggered = _check_alerts(alerts)
    for t in triggered:
        st.warning(
            f"🔔 ALERT TRIGGERED: **{t['name']}** hit Rs.{t.get('triggered_price', t['target']):,.2f} "
            f"({t['condition']} Rs.{t['target']:,.2f})"
        )

    st.subheader(f"Active Alerts ({len(alerts)})")
    for i, a in enumerate(alerts):
        cols = st.columns([3, 1, 1, 1, 1])
        status = "✅ Triggered" if a["triggered"] else "⏳ Watching"
        cols[0].write(f"**{a['name']}** ({a['symbol']})")
        cols[1].write(f"{a['condition']} Rs.{a['target']:,.2f}")
        cols[2].write(status)
        cols[3].caption(a["created"])
        if cols[4].button("Remove", key=f"al_rm_{i}"):
            alerts.pop(i)
            st.rerun()
