"""Tab 4 — P&L Calculator."""
import streamlit as st

from utils.logger import get_logger
from utils.constants import NIFTY50
from utils.data import fetch_ticker, get_beta
from utils.calculations import safe_float, calc_pl, calc_beta_impact

log = get_logger(__name__)


def render(market_open: bool, market_status: str, last_close_label: str) -> None:
    from utils.app_helpers import hero, divider, sec, closed_banner, show_pl_result
    hero("P&L Calculator", "Calculate profit / loss")
    closed_banner(market_open, market_status, last_close_label)

    c1, c2, c3 = st.columns(3)
    with c1:
        sel_name = st.selectbox("Stock", [s["name"] for s in NIFTY50], key="pl_s")

    sel_s = next(s for s in NIFTY50 if s["name"] == sel_name)

    lp = 0.0
    try:
        sc_data = fetch_ticker(sel_s["symbol"], "5d")
        if not sc_data.empty and "Close" in sc_data.columns:
            lp = safe_float(sc_data["Close"].iloc[-1])
        else:
            log.warning("tab_pl: empty data for symbol '%s'", sel_s["symbol"])
    except OSError as exc:
        log.error("tab_pl: network error fetching '%s': %s", sel_s["symbol"], exc, exc_info=True)
        st.warning("Network error — using default price of Rs.\ 100.")
    except Exception as exc:  # noqa: BLE001
        log.error("tab_pl: unexpected error fetching '%s': %s", sel_s["symbol"], exc, exc_info=True)

    with c2:
        buy_p = st.number_input(
            "Buy Price (Rs.)",
            min_value=0.01,
            value=round(lp, 2) if lp > 0 else 100.0,
            step=0.5,
            key="pl_bp",
        )
    with c3:
        qty = st.number_input("Quantity", min_value=1, value=10, step=1, key="pl_q")

    sell_p = st.number_input(
        "Sell / Current Price (Rs.)" if market_open else "Sell Price (Rs.)",
        min_value=0.01,
        value=round(lp, 2) if lp > 0 else 100.0,
        step=0.5,
        key="pl_sp",
    )

    if buy_p <= 0 or sell_p <= 0 or qty <= 0:
        st.error("Buy price, sell price, and quantity must all be positive.")
        return

    pl, inv, ret = calc_pl(buy_p, sell_p, qty)
    divider()

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Investment", "Rs." + format(inv, ",.2f"))
    mc2.metric("P&L", "Rs." + format(pl, "+,.2f"))
    mc3.metric("Return", format(ret, "+.2f") + "%")
    show_pl_result(pl)
    divider()

    sec("Beta-Adjusted Impact")
    ni_col, bv_col = st.columns(2)
    with ni_col:
        nifty_move = st.slider("Nifty Move (%)", -20.0, 20.0, 0.0, 0.5, key="pl_nm")
    with bv_col:
        # Prefer dynamic beta; fall back to static in constants
        default_beta = float(get_beta(sel_s["symbol"]))
        beta_val = st.number_input(
            "Beta", 0.1, 3.0, value=default_beta, step=0.05, key="pl_bv"
        )

    if nifty_move != 0:
        try:
            spct, pchg, nsp, _ov, _nv, pl_beta = calc_beta_impact(nifty_move, buy_p, qty, beta_val)
            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Stock Move", format(spct, "+.2f") + "%")
            b2.metric("Price Change", "Rs." + format(pchg, "+.2f"))
            b3.metric("New Price", "Rs." + format(nsp, ".2f"))
            b4.metric("P&L Impact", "Rs." + format(pl_beta, "+,.2f"))
        except (ArithmeticError, ValueError) as exc:
            log.error("tab_pl: beta impact calculation error: %s", exc, exc_info=True)
            st.error("Beta impact calculation failed — check inputs.")
        except Exception as exc:  # noqa: BLE001
            log.error("tab_pl: beta impact unexpected: %s", exc, exc_info=True)
