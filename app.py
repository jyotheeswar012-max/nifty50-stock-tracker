"""NSE & Nifty 50 Tracker — main Streamlit entry point.

This file's only job is UI orchestration:
  - page config, auth, auto-refresh
  - render each tab by calling helpers from utils/
  - no raw data logic, no chart-building code
"""
import streamlit as st
import pandas as pd
import time
from datetime import datetime
import pytz
import warnings
warnings.filterwarnings("ignore")

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

# -- Page config (must be first Streamlit call) --
st.set_page_config(
    page_title="NSE & Nifty 50 Tracker",
    page_icon="chart_with_upwards_trend",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -- Optional theme / auth --
try:
    from utils.theme import inject, inject_topbar
    inject()
except Exception:
    pass

try:
    from utils.supabase_auth import get_current_user
except Exception:
    def get_current_user(): return None

user = get_current_user()
try:
    inject_topbar(user=user)
except Exception:
    pass

# -- Module imports --
from utils.constants import (
    REFRESH_MS, NIFTY50, NSE_INDICES, FAMOUS_DATES, PLT_LAYOUT,
)
from utils.data import (
    is_nse_open,
    fetch_ticker, fetch_intraday,
    fetch_indices, fetch_all_stocks_5d, fetch_all_history,
)
from utils.calculations import (
    safe_float, build_stock_rows, safe_sort,
    calc_pl, calc_beta_impact, build_time_machine_snapshot,
)
from utils.charts import (
    build_price_chart, build_pct_bar, build_closing_bar, build_trend_chart,
)

# ---------------------------------------------------------------------------
# Market state (computed once per run)
# ---------------------------------------------------------------------------
market_open, market_status, last_close_label = is_nse_open()

refresh_count = 0
if AUTOREFRESH_AVAILABLE and market_open:
    try:
        refresh_count = st_autorefresh(interval=REFRESH_MS, key="live_refresh")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Cached stock-row builder (depends on market_open, so lives in app.py)
# ---------------------------------------------------------------------------
from utils.constants import CACHE_TTL

@st.cache_data(ttl=CACHE_TTL)
def _build_stock_rows_cached():
    return build_stock_rows(
        fetch_all_stocks_5d(),
        market_open,
        fetch_intraday,
    )

# ---------------------------------------------------------------------------
# Shared UI helpers
# ---------------------------------------------------------------------------

def _hero(title, sub=""):
    try:
        st.subheader(title)
        if sub:
            st.caption(sub)
    except Exception:
        pass

def _sec(label):
    try:
        st.markdown("**" + label + "**")
    except Exception:
        st.caption(label)

def _divider():
    st.markdown("---")

def _status_banner():
    try:
        ist_now = datetime.now(pytz.timezone("Asia/Kolkata"))
        ist_str = ist_now.strftime("%I:%M:%S %p IST")
        from utils.constants import CACHE_TTL
        if market_open:
            pulse        = ["[LIVE]", "[ -- ]"][refresh_count % 2]
            next_data_in = CACHE_TTL - (int(time.time()) % CACHE_TTL)
            st.success(
                pulse + "  NSE LIVE  |  " + ist_str +
                "  |  Refreshing every 5s  |  New data in " + str(next_data_in) + "s  |  MARKET OPEN"
            )
        else:
            st.warning(
                "NSE CLOSED -- " + market_status +
                (" | " + last_close_label if last_close_label else "") +
                " | Showing last closing prices"
            )
    except Exception:
        st.info("NSE Tracker")

def _closed_banner():
    if not market_open:
        try:
            st.warning(
                "NSE CLOSED -- " + market_status +
                (" | " + last_close_label if last_close_label else "") +
                " | Showing last closing prices"
            )
        except Exception:
            pass

def _show_pl_result(pl):
    pl = safe_float(pl)
    if   pl > 0: st.success("GAIN  Rs." + format(pl, ",.2f"))
    elif pl < 0: st.error(  "LOSS  Rs." + format(abs(pl), ",.2f"))
    else:        st.info("No Change")

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
_status_banner()

tabs = st.tabs([
    "Market Overview",
    "Nifty 50 Index",
    "All 50 Companies",
    "Gainers & Losers",
    "P&L Calculator",
    "Stock Chart",
    "Time Machine",
])

# ── Tab 0: Market Overview ──────────────────────────────────────────────────
with tabs[0]:
    try:
        _hero("NSE Market Overview", "National Stock Exchange")
        _closed_banner()
        _sec("NSE Indices Snapshot")

        idx_data = fetch_indices()
        val_lbl  = "Value" if market_open else "Last Close"
        idx_rows = []
        for idx in NSE_INDICES:
            try:
                h = idx_data.get(idx["symbol"])
                if h is not None and not h.empty and "Close" in h.columns and len(h) >= 2:
                    c  = safe_float(h["Close"].iloc[-1])
                    p  = safe_float(h["Close"].iloc[-2], c)
                    ch = c - p
                    pt = round(ch / p * 100, 2) if p != 0 else 0.0
                    idx_rows.append({
                        "Index": idx["name"], val_lbl: "Rs." + format(c, ",.2f"),
                        "Change (pts)": format(ch, "+.2f"),
                        "Change (%)": format(pt, "+.2f") + "%",
                        "High": "Rs." + format(safe_float(h["High"].max()), ",.2f"),
                        "Low":  "Rs." + format(safe_float(h["Low"].min()),  ",.2f"),
                        "_pct": pt,
                    })
                else:
                    idx_rows.append({"Index": idx["name"], val_lbl: "N/A",
                        "Change (pts)": "N/A", "Change (%)": "N/A",
                        "High": "N/A", "Low": "N/A", "_pct": None})
            except Exception:
                idx_rows.append({"Index": idx["name"], val_lbl: "N/A",
                    "Change (pts)": "N/A", "Change (%)": "N/A",
                    "High": "N/A", "Low": "N/A", "_pct": None})

        idx_df = pd.DataFrame(idx_rows)
        st.dataframe(idx_df.drop(columns=["_pct"]), use_container_width=True, hide_index=True)

        valid_idx = idx_df[idx_df["_pct"].notna()].copy()
        if not valid_idx.empty:
            try:
                title = "Today's % Change by Index" if market_open else "Last Session % Change by Index"
                st.plotly_chart(
                    build_pct_bar(valid_idx, "Index", "_pct", title, text_col="Change (%)", height=300),
                    use_container_width=True,
                )
            except Exception:
                pass

        _divider()
        _sec("Trend Comparison")
        c_per, c_idx = st.columns([1, 3])
        with c_per:
            p_sel = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1, key="idx_p")
        with c_idx:
            sel_idx = st.multiselect(
                "Indices", [i["name"] for i in NSE_INDICES],
                default=["Nifty 50", "Nifty Bank", "Nifty IT"],
            )
        sym_map = {i["name"]: i for i in NSE_INDICES}
        if sel_idx:
            try:
                series = {}
                for ni in sel_idx:
                    meta = sym_map.get(ni)
                    if not meta:
                        continue
                    h = fetch_ticker(meta["symbol"], p_sel)
                    if not h.empty and "Close" in h.columns:
                        series[ni] = {"df": h, "color": meta["color"]}
                if series:
                    st.plotly_chart(
                        build_trend_chart(series, height=360),
                        use_container_width=True,
                    )
            except Exception:
                st.info("Could not render trend chart.")
    except Exception as e:
        st.error("Market Overview error: " + str(e))

# ── Tab 1: Nifty 50 Index ───────────────────────────────────────────────────
with tabs[1]:
    try:
        _hero("Nifty 50 Index", "^NSEI - NSE Flagship Index")
        _closed_banner()
        c1, c2 = st.columns([1, 3])
        with c1:
            n_period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2, key="nf_p")
        with c2:
            chart_type = st.radio("Chart", ["Line", "Candlestick", "Area"], horizontal=True, key="nf_ct")

        nifty = fetch_ticker("^NSEI", n_period)
        if nifty.empty or "Close" not in nifty.columns:
            st.warning("Could not fetch Nifty 50 data.")
        else:
            c  = safe_float(nifty["Close"].iloc[-1])
            p  = safe_float(nifty["Close"].iloc[-2]) if len(nifty) > 1 else c
            ch = c - p
            pt = ch / p * 100 if p else 0
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Price" if market_open else "Last Close", "Rs." + format(c, ",.2f"))
            m2.metric("Change", format(ch, "+.2f"), delta=format(pt, "+.2f") + "%")
            m3.metric("Period High", "Rs." + format(safe_float(nifty["High"].max()), ",.2f"))
            m4.metric("Period Low",  "Rs." + format(safe_float(nifty["Low"].min()),  ",.2f"))
            m5.metric("Avg Volume",  format(int(safe_float(nifty["Volume"].mean())), ","))
            _divider()
            try:
                st.plotly_chart(
                    build_price_chart(nifty, "Nifty 50", n_period, chart_type,
                                      y_title="Index Value", height=440),
                    use_container_width=True,
                )
            except Exception:
                st.info("Chart unavailable.")
    except Exception as e:
        st.error("Nifty 50 error: " + str(e))

# ── Tab 2: All 50 Companies ─────────────────────────────────────────────────
with tabs[2]:
    try:
        _hero("All 50 Companies", "Live prices" if market_open else "Last closing prices")
        _closed_banner()

        sectors    = ["All"] + sorted(set(s["sector"] for s in NIFTY50))
        sel_sec    = st.selectbox("Sector", sectors, key="all_sec")
        df_rows    = _build_stock_rows_cached()
        if sel_sec != "All":
            df_rows = df_rows[df_rows["Sector"] == sel_sec]

        disp = df_rows.drop(columns=["_curr", "_pct"], errors="ignore")
        st.dataframe(disp, use_container_width=True, hide_index=True)

        valid = df_rows[df_rows["_pct"].notna()].copy()
        if not valid.empty:
            try:
                title = "1-Day % Change" if market_open else "1-Day % Change (last session)"
                st.plotly_chart(
                    build_pct_bar(valid, "Symbol", "_pct", title, text_col="Change (%)"),
                    use_container_width=True,
                )
            except Exception:
                pass
    except Exception as e:
        st.error("Companies error: " + str(e))

# ── Tab 3: Gainers & Losers ─────────────────────────────────────────────────
with tabs[3]:
    try:
        _hero("Gainers & Losers", "Today" if market_open else "Last Session")
        _closed_banner()

        df_rows = _build_stock_rows_cached()
        valid   = df_rows[df_rows["_pct"].notna()].copy()
        top_n   = st.slider("Top N", 3, 10, 5, key="gl_n")

        if valid.empty:
            st.warning("No data available.")
        else:
            gainers   = safe_sort(valid, "_pct", ascending=False).head(top_n)
            losers    = safe_sort(valid, "_pct", ascending=True).head(top_n)
            price_col = next((c for c in df_rows.columns if "Price" in c or "Last Close" in c), "_curr")

            cg, cl = st.columns(2)
            with cg:
                _sec("Top Gainers")
                st.dataframe(
                    gainers[["Symbol", "Company", price_col, "Change (%)"]],
                    use_container_width=True, hide_index=True,
                )
            with cl:
                _sec("Top Losers")
                st.dataframe(
                    losers[["Symbol", "Company", price_col, "Change (%)"]],
                    use_container_width=True, hide_index=True,
                )

            try:
                combined = pd.concat([gainers, losers]).drop_duplicates(subset="Symbol")
                combined = combined[combined["_pct"].notna()]
                st.plotly_chart(
                    build_pct_bar(combined, "Symbol", "_pct", "Gainers vs Losers",
                                  text_col="Change (%)"),
                    use_container_width=True,
                )
            except Exception:
                pass
    except Exception as e:
        st.error("Gainers/Losers error: " + str(e))

# ── Tab 4: P&L Calculator ───────────────────────────────────────────────────
with tabs[4]:
    try:
        _hero("P&L Calculator", "Calculate profit / loss")
        _closed_banner()

        c1, c2, c3 = st.columns(3)
        with c1:
            sel_name = st.selectbox("Stock", [s["name"] for s in NIFTY50], key="pl_s")
        sel_s   = next(s for s in NIFTY50 if s["name"] == sel_name)
        sc_data = fetch_ticker(sel_s["symbol"], "5d")
        lp      = safe_float(sc_data["Close"].iloc[-1]) \
                  if not sc_data.empty and "Close" in sc_data.columns else 0.0
        with c2:
            buy_p = st.number_input("Buy Price (Rs.)", min_value=0.01,
                                    value=round(lp, 2) if lp > 0 else 100.0,
                                    step=0.5, key="pl_bp")
        with c3:
            qty = st.number_input("Quantity", min_value=1, value=10, step=1, key="pl_q")

        sell_p = st.number_input(
            "Sell / Current Price (Rs.)" if market_open else "Sell Price (Rs.)",
            min_value=0.01, value=round(lp, 2) if lp > 0 else 100.0,
            step=0.5, key="pl_sp",
        )

        pl, inv, ret = calc_pl(buy_p, sell_p, qty)
        _divider()
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Investment", "Rs." + format(inv, ",.2f"))
        mc2.metric("P&L",        "Rs." + format(pl,  "+,.2f"))
        mc3.metric("Return",     format(ret, "+.2f") + "%")
        _show_pl_result(pl)

        _divider()
        _sec("Beta-Adjusted Impact")
        ni_col, bv_col = st.columns(2)
        with ni_col:
            nifty_move = st.slider("Nifty Move (%)", -20.0, 20.0, 0.0, 0.5, key="pl_nm")
        with bv_col:
            beta_val = st.number_input("Beta", 0.1, 3.0,
                                       value=float(sel_s.get("beta", 1.0)),
                                       step=0.05, key="pl_bv")
        if nifty_move != 0:
            spct, pchg, nsp, _ov, _nv, pl_beta = calc_beta_impact(nifty_move, buy_p, qty, beta_val)
            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Stock Move",   format(spct,    "+.2f") + "%")
            b2.metric("Price Change", "Rs." + format(pchg,    "+.2f"))
            b3.metric("New Price",    "Rs." + format(nsp,     ".2f"))
            b4.metric("P&L Impact",   "Rs." + format(pl_beta, "+,.2f"))
    except Exception as e:
        st.error("P&L error: " + str(e))

# ── Tab 5: Stock Chart ──────────────────────────────────────────────────────
with tabs[5]:
    try:
        _hero("Stock Chart", "Detailed chart for any Nifty 50 stock")
        _closed_banner()

        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            sc_name = st.selectbox("Stock", [s["name"] for s in NIFTY50], key="sc_s")
        with c2:
            sc_per = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2, key="sc_p")
        with c3:
            sc_ct = st.radio("Chart", ["Line", "Candlestick", "Area"], horizontal=True, key="sc_ct")

        sc_sym = next(s["symbol"] for s in NIFTY50 if s["name"] == sc_name)
        sc_h   = fetch_ticker(sc_sym, sc_per)

        if sc_h.empty or "Close" not in sc_h.columns:
            st.warning("No data found for this stock.")
        else:
            c  = safe_float(sc_h["Close"].iloc[-1])
            p  = safe_float(sc_h["Close"].iloc[-2]) if len(sc_h) > 1 else c
            ch = c - p
            pt = ch / p * 100 if p else 0
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Price" if market_open else "Last Close", "Rs." + format(c,  ",.2f"))
            m2.metric("Change", format(ch, "+.2f"), delta=format(pt, "+.2f") + "%")
            m3.metric("High",   "Rs." + format(safe_float(sc_h["High"].max()), ",.2f"))
            m4.metric("Low",    "Rs." + format(safe_float(sc_h["Low"].min()),  ",.2f"))
            try:
                st.plotly_chart(
                    build_price_chart(sc_h, sc_name, sc_per, sc_ct, height=440),
                    use_container_width=True,
                )
            except Exception:
                st.info("Chart unavailable.")
    except Exception as e:
        st.error("Stock Chart error: " + str(e))

# ── Tab 6: Time Machine ─────────────────────────────────────────────────────
with tabs[6]:
    try:
        _hero("Time Machine", "Travel back to any NSE trading day")
        from datetime import date
        preset = st.selectbox("Famous dates", ["Custom..."] + list(FAMOUS_DATES.keys()), key="tm_preset")
        if preset == "Custom...":
            tm_date = st.date_input("Date", value=date(2020, 3, 23),
                                    min_value=date(2010, 1, 1),
                                    max_value=date.today(), key="tm_date")
        else:
            tm_date = FAMOUS_DATES[preset]
            st.info("Loaded: " + preset + " - " + str(tm_date))

        if st.button("Travel to this date", key="tm_go"):
            with st.spinner("Loading historical data (may take 30-60s first time)..."):
                all_hist = fetch_all_history()
            snap = build_time_machine_snapshot(all_hist, tm_date)
            if snap.empty:
                st.error("No data for this date. Try a nearby trading day.")
            else:
                st.success("Snapshot for " + str(tm_date))
                st.dataframe(snap, use_container_width=True)
                try:
                    st.plotly_chart(
                        build_closing_bar(
                            snap.reset_index(), "Symbol", "Close",
                            "Closing Prices - " + str(tm_date),
                        ),
                        use_container_width=True,
                    )
                except Exception:
                    pass
    except Exception as e:
        st.error("Time Machine error: " + str(e))
