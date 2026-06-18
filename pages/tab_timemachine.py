"""Tab 6 — Time Machine."""
import streamlit as st
import pandas as pd
from datetime import date, timedelta

from utils.logger import get_logger
from utils.data import fetch_ticker
from utils.calculations import safe_float
from utils.constants import NIFTY50

log = get_logger(__name__)


def render():
    from utils.app_helpers import hero, divider
    hero("Time Machine", "What if you had bought on a specific date?")

    symbols = [s["symbol"] for s in NIFTY50]
    names   = [s["name"]   for s in NIFTY50]
    options = [f"{sym} — {nm}" for sym, nm in zip(symbols, names)]

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        sel = st.selectbox("Stock", options, key="tm_sym")
    with c2:
        buy_date = st.date_input("Buy Date", value=date.today() - timedelta(days=365), key="tm_date")
    with c3:
        qty = st.number_input("Quantity", min_value=1, value=10, step=1, key="tm_qty")

    sym  = symbols[options.index(sel)]
    name = names[options.index(sel)]

    if st.button("Calculate", key="tm_calc"):
        try:
            period = "5y"
            df = fetch_ticker(sym, period)
        except Exception as exc:
            log.error("tab_timemachine: fetch error for %s: %s", sym, exc, exc_info=True)
            st.error("Could not fetch data.")
            return

        if df.empty or "Close" not in df.columns:
            st.warning("No data available.")
            return

        df.index = pd.to_datetime(df.index)
        buy_ts = pd.Timestamp(buy_date)

        # Find closest trading day on or after buy_date
        future = df[df.index >= buy_ts]
        if future.empty:
            st.warning("No trading data on or after the selected date.")
            return

        actual_buy = future.index[0]
        buy_price  = safe_float(future["Close"].iloc[0])
        curr_price = safe_float(df["Close"].iloc[-1])

        invested  = buy_price  * qty
        curr_val  = curr_price * qty
        pl        = curr_val - invested
        pl_pct    = pl / invested * 100 if invested else 0
        hold_days = (date.today() - actual_buy.date()).days

        divider()
        st.success(f"Purchased **{qty} × {name}** on **{actual_buy.date()}** at **Rs.{buy_price:,.2f}**")

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Buy Price",    f"Rs.{buy_price:,.2f}")
        m2.metric("Current Price",f"Rs.{curr_price:,.2f}")
        m3.metric("Invested",     f"Rs.{invested:,.2f}")
        m4.metric("Current Value",f"Rs.{curr_val:,.2f}")
        color = "🟢" if pl >= 0 else "🔴"
        m5.metric(f"{color} Net P&L", f"Rs.{pl:+,.2f}", delta=f"{pl_pct:+.2f}%")
        st.caption(f"Holding period: {hold_days} days")
