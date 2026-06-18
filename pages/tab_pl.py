"""Tab 4 — P&L Calculator."""
import streamlit as st

from utils.logger import get_logger
from utils.data import fetch_ticker
from utils.calculations import safe_float
from utils.constants import NIFTY50

log = get_logger(__name__)


def render(market_open, market_status, last_close_label):
    from utils.app_helpers import hero, closed_banner
    hero("P&L Calculator", "Profit & Loss estimator")
    closed_banner(market_open, market_status, last_close_label)

    symbols = [s["symbol"] for s in NIFTY50]
    names   = [s["name"]   for s in NIFTY50]
    options = [f"{sym} — {nm}" for sym, nm in zip(symbols, names)]

    sel = st.selectbox("Stock", options, key="pl_sym")
    sym = symbols[options.index(sel)]

    c1, c2, c3 = st.columns(3)
    with c1:
        buy_price = st.number_input("Buy Price (Rs.)", min_value=0.01, value=1000.0, step=0.5, key="pl_buy")
    with c2:
        qty = st.number_input("Quantity", min_value=1, value=10, step=1, key="pl_qty")
    with c3:
        brokerage = st.number_input("Brokerage (%)", min_value=0.0, max_value=5.0, value=0.1, step=0.01, key="pl_brok")

    try:
        df = fetch_ticker(sym, "5d")
        curr = safe_float(df["Close"].iloc[-1]) if not df.empty and "Close" in df.columns else buy_price
    except Exception as exc:
        log.warning("tab_pl: could not fetch current price for %s: %s", sym, exc)
        curr = buy_price

    sell_price = st.number_input("Sell Price (Rs.)", min_value=0.01,
                                  value=round(curr, 2), step=0.5, key="pl_sell")

    invest   = buy_price  * qty
    proceeds = sell_price * qty
    brok_amt = (brokerage / 100) * (invest + proceeds)
    pl_net   = proceeds - invest - brok_amt
    pl_pct   = pl_net / invest * 100 if invest else 0

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Invested",    f"Rs.{invest:,.2f}")
    m2.metric("Proceeds",    f"Rs.{proceeds:,.2f}")
    m3.metric("Brokerage",   f"Rs.{brok_amt:,.2f}")
    color = "🟢" if pl_net >= 0 else "🔴"
    m4.metric(f"{color} Net P&L", f"Rs.{pl_net:+,.2f}", delta=f"{pl_pct:+.2f}%")
