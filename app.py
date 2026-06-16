"""NSE & Nifty 50 Tracker — Streamlit entry point."""
import time
import warnings
from datetime import datetime

import pandas as pd
import pytz
import streamlit as st

warnings.filterwarnings("ignore")

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

st.set_page_config(
    page_title="NSE & Nifty 50 Tracker",
    page_icon="chart_with_upwards_trend",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from utils.logger import get_logger, read_recent_logs, log_file_path
log = get_logger(__name__)
log.info("app.py startup — Streamlit session initialised")

try:
    from utils.theme import inject, inject_topbar
    inject()
except Exception:
    pass

try:
    inject_topbar(user=None)
except Exception:
    pass

from utils.constants import REFRESH_MS, NIFTY50, NSE_INDICES, FAMOUS_DATES, CACHE_TTL
from utils.data import (
    is_nse_open,
    fetch_ticker, fetch_intraday,
    fetch_indices, fetch_all_stocks_5d, fetch_all_history,
    get_source_status,
)
from utils.calculations import (
    safe_float, build_stock_rows, safe_sort,
    calc_pl, calc_beta_impact, build_time_machine_snapshot,
)
from utils.charts import (
    build_price_chart, build_pct_bar, build_closing_bar, build_trend_chart,
)
from utils.alerts import get_alerts, add_alert, remove_alert, fire_alerts
from utils.notifications import smtp_configured, twilio_configured

# ---------------------------------------------------------------------------
# Market state
# ---------------------------------------------------------------------------
market_open, market_status, last_close_label = is_nse_open()

refresh_count = 0
if AUTOREFRESH_AVAILABLE and market_open:
    try:
        refresh_count = st_autorefresh(interval=REFRESH_MS, key="live_refresh")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Cached stock-row builder
# ---------------------------------------------------------------------------

@st.cache_data(ttl=CACHE_TTL)
def _build_stock_rows_cached():
    return build_stock_rows(fetch_all_stocks_5d(), market_open, fetch_intraday)


# ---------------------------------------------------------------------------
# Shared UI helpers
# ---------------------------------------------------------------------------

def _hero(title, sub=""):
    st.subheader(title)
    if sub:
        st.caption(sub)


def _sec(label):
    st.markdown("**" + label + "**")


def _divider():
    st.markdown("---")


def _status_banner():
    try:
        ist_now = datetime.now(pytz.timezone("Asia/Kolkata"))
        ist_str = ist_now.strftime("%I:%M:%S %p IST")
        if market_open:
            pulse        = ["[LIVE]", "[ -- ]"][refresh_count % 2]
            next_data_in = CACHE_TTL - (int(time.time()) % CACHE_TTL)
            st.success(
                pulse + "  NSE LIVE  |  " + ist_str +
                "  |  Refreshing every 5s  |  New data in " + str(next_data_in) + "s  |  MARKET OPEN"
            )
        else:
            st.warning(
                "NSE CLOSED — " + market_status +
                (" | " + last_close_label if last_close_label else "") +
                " | Showing last closing prices"
            )
    except Exception as exc:
        log.error("_status_banner failed: %s", exc)
        st.info("NSE Tracker")


def _closed_banner():
    if not market_open:
        st.warning(
            "NSE CLOSED — " + market_status +
            (" | " + last_close_label if last_close_label else "") +
            " | Showing last closing prices"
        )


def _show_pl_result(pl):
    pl = safe_float(pl)
    if   pl > 0: st.success("GAIN  Rs." + format(pl, ",.2f"))
    elif pl < 0: st.error(  "LOSS  Rs." + format(abs(pl), ",.2f"))
    else:        st.info("No Change")


def _show_data_warnings():
    warnings_list = st.session_state.get("data_warnings", [])
    for w in warnings_list:
        st.warning(w)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### ⚙️ System")

    with st.expander("🔌 Data Source Status", expanded=False):
        try:
            src = get_source_status()
            icons = {"ok": "🟢", "degraded": "🟡", "down": "🔴", "not installed": "⚫"}
            st.markdown(f"{icons.get(src.get('yfinance','?'), '?')} **Yahoo Finance**: `{src.get('yfinance','?')}`")
            st.markdown(f"{icons.get(src.get('nselib','?'), '?')} **NSE (nselib)**: `{src.get('nselib','?')}`")
        except Exception as exc:
            log.error("Source status widget failed: %s", exc)
            st.caption("Status unavailable")

    with st.expander("📋 Live Logs", expanded=False):
        try:
            n_lines = st.slider("Lines", 20, 200, 50, step=10, key="log_lines")
            level_filter = st.selectbox(
                "Min level", ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                index=2, key="log_level_filter",
            )
            lines = read_recent_logs(n_lines)
            if level_filter != "ALL":
                lvl_order = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                min_idx   = lvl_order.index(level_filter)
                lines = [l for l in lines if any(lv in l for lv in lvl_order[min_idx:])]
            if lines:
                st.code("\n".join(lines), language="")
            else:
                st.caption("No log entries yet.")
            st.caption(f"Log file: `{log_file_path()}`")
        except Exception as exc:
            log.error("Log viewer widget failed: %s", exc)
            st.caption("Log viewer unavailable")


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
_status_banner()
_show_data_warnings()

tabs = st.tabs([
    "Market Overview",
    "Nifty 50 Index",
    "All 50 Companies",
    "Gainers & Losers",
    "P&L Calculator",
    "Stock Chart",
    "Time Machine",
    "🔔 Alerts",
])

# ── Tab 0: Market Overview ──────────────────────────────────────────────────
with tabs[0]:
    try:
        t0 = time.perf_counter()
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
            except Exception as exc:
                log.error("Tab0: error building row for %s: %s", idx["name"], exc)
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
            except Exception as exc:
                log.error("Tab0: bar chart failed: %s", exc)

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
                    st.plotly_chart(build_trend_chart(series, height=360), use_container_width=True)
            except Exception as exc:
                log.error("Tab0: trend chart failed: %s", exc)
                st.info("Could not render trend chart.")
        log.info("Tab0 Market Overview rendered in %.0f ms", (time.perf_counter() - t0) * 1000)
    except Exception as exc:
        log.error("Tab0 fatal: %s", exc, exc_info=True)
        st.error("Market Overview error: " + str(exc))

# ── Tab 1: Nifty 50 Index ───────────────────────────────────────────────────
with tabs[1]:
    try:
        t0 = time.perf_counter()
        _hero("Nifty 50 Index", "^NSEI — NSE Flagship Index")
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
                    build_price_chart(nifty, "Nifty 50", n_period, chart_type, y_title="Index Value", height=440),
                    use_container_width=True,
                )
            except Exception as exc:
                log.error("Tab1: chart failed: %s", exc)
                st.info("Chart unavailable.")
        log.info("Tab1 Nifty 50 rendered in %.0f ms", (time.perf_counter() - t0) * 1000)
    except Exception as exc:
        log.error("Tab1 fatal: %s", exc, exc_info=True)
        st.error("Nifty 50 error: " + str(exc))

# ── Tab 2: All 50 Companies ─────────────────────────────────────────────────
with tabs[2]:
    try:
        t0 = time.perf_counter()
        _hero("All 50 Companies", "Live prices" if market_open else "Last closing prices")
        _closed_banner()

        sectors = ["All"] + sorted(set(s["sector"] for s in NIFTY50))
        sel_sec = st.selectbox("Sector", sectors, key="all_sec")
        df_rows = _build_stock_rows_cached()
        if sel_sec != "All":
            df_rows = df_rows[df_rows["Sector"] == sel_sec]

        disp = df_rows.drop(columns=["_curr", "_pct"], errors="ignore")
        st.dataframe(disp, use_container_width=True, hide_index=True)

        valid = df_rows[df_rows["_pct"].notna()].copy()
        if not valid.empty:
            try:
                title = "1-Day % Change" if market_open else "1-Day % Change (last session)"
                st.plotly_chart(build_pct_bar(valid, "Symbol", "_pct", title, text_col="Change (%)"), use_container_width=True)
            except Exception as exc:
                log.error("Tab2: bar chart failed: %s", exc)
        log.info("Tab2 All Companies rendered in %.0f ms", (time.perf_counter() - t0) * 1000)
    except Exception as exc:
        log.error("Tab2 fatal: %s", exc, exc_info=True)
        st.error("Companies error: " + str(exc))

# ── Tab 3: Gainers & Losers ─────────────────────────────────────────────────
with tabs[3]:
    try:
        t0 = time.perf_counter()
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
            cg, cl    = st.columns(2)
            with cg:
                _sec("Top Gainers")
                st.dataframe(gainers[["Symbol", "Company", price_col, "Change (%)"]], use_container_width=True, hide_index=True)
            with cl:
                _sec("Top Losers")
                st.dataframe(losers[["Symbol", "Company", price_col, "Change (%)"]], use_container_width=True, hide_index=True)
            try:
                combined = pd.concat([gainers, losers]).drop_duplicates(subset="Symbol")
                combined = combined[combined["_pct"].notna()]
                st.plotly_chart(build_pct_bar(combined, "Symbol", "_pct", "Gainers vs Losers", text_col="Change (%)"), use_container_width=True)
            except Exception as exc:
                log.error("Tab3: combined chart failed: %s", exc)
        log.info("Tab3 Gainers/Losers rendered in %.0f ms", (time.perf_counter() - t0) * 1000)
    except Exception as exc:
        log.error("Tab3 fatal: %s", exc, exc_info=True)
        st.error("Gainers/Losers error: " + str(exc))

# ── Tab 4: P&L Calculator ───────────────────────────────────────────────────
with tabs[4]:
    try:
        t0 = time.perf_counter()
        _hero("P&L Calculator", "Calculate profit / loss")
        _closed_banner()

        c1, c2, c3 = st.columns(3)
        with c1:
            sel_name = st.selectbox("Stock", [s["name"] for s in NIFTY50], key="pl_s")
        sel_s   = next(s for s in NIFTY50 if s["name"] == sel_name)
        sc_data = fetch_ticker(sel_s["symbol"], "5d")
        lp      = safe_float(sc_data["Close"].iloc[-1]) if not sc_data.empty and "Close" in sc_data.columns else 0.0
        with c2:
            buy_p = st.number_input("Buy Price (Rs.)", min_value=0.01, value=round(lp, 2) if lp > 0 else 100.0, step=0.5, key="pl_bp")
        with c3:
            qty = st.number_input("Quantity", min_value=1, value=10, step=1, key="pl_q")

        sell_p = st.number_input(
            "Sell / Current Price (Rs.)" if market_open else "Sell Price (Rs.)",
            min_value=0.01, value=round(lp, 2) if lp > 0 else 100.0, step=0.5, key="pl_sp",
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
            beta_val = st.number_input("Beta", 0.1, 3.0, value=float(sel_s.get("beta", 1.0)), step=0.05, key="pl_bv")
        if nifty_move != 0:
            spct, pchg, nsp, _ov, _nv, pl_beta = calc_beta_impact(nifty_move, buy_p, qty, beta_val)
            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Stock Move",   format(spct,    "+.2f") + "%")
            b2.metric("Price Change", "Rs." + format(pchg,    "+.2f"))
            b3.metric("New Price",    "Rs." + format(nsp,     ".2f"))
            b4.metric("P&L Impact",   "Rs." + format(pl_beta, "+,.2f"))
        log.info("Tab4 P&L rendered in %.0f ms", (time.perf_counter() - t0) * 1000)
    except Exception as exc:
        log.error("Tab4 fatal: %s", exc, exc_info=True)
        st.error("P&L error: " + str(exc))

# ── Tab 5: Stock Chart ──────────────────────────────────────────────────────
with tabs[5]:
    try:
        t0 = time.perf_counter()
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
                st.plotly_chart(build_price_chart(sc_h, sc_name, sc_per, sc_ct, height=440), use_container_width=True)
            except Exception as exc:
                log.error("Tab5: chart render failed for %s: %s", sc_name, exc)
                st.info("Chart unavailable.")
        log.info("Tab5 Stock Chart rendered in %.0f ms", (time.perf_counter() - t0) * 1000)
    except Exception as exc:
        log.error("Tab5 fatal: %s", exc, exc_info=True)
        st.error("Stock Chart error: " + str(exc))

# ── Tab 6: Time Machine ─────────────────────────────────────────────────────
with tabs[6]:
    try:
        t0 = time.perf_counter()
        _hero("Time Machine", "Travel back to any NSE trading day")
        from datetime import date
        preset = st.selectbox("Famous dates", ["Custom..."] + list(FAMOUS_DATES.keys()), key="tm_preset")
        if preset == "Custom...":
            tm_date = st.date_input("Date", value=date(2020, 3, 23),
                                    min_value=date(2010, 1, 1), max_value=date.today(), key="tm_date")
        else:
            tm_date = FAMOUS_DATES[preset]
            st.info("Loaded: " + preset + " — " + str(tm_date))

        if st.button("Travel to this date", key="tm_go"):
            with st.spinner("Loading historical data (may take 30–60s first time)..."):
                all_hist = fetch_all_history()
            snap = build_time_machine_snapshot(all_hist, tm_date)
            if snap.empty:
                st.error("No data for this date. Try a nearby trading day.")
            else:
                st.success("Snapshot for " + str(tm_date))
                st.dataframe(snap, use_container_width=True)
                try:
                    st.plotly_chart(
                        build_closing_bar(snap.reset_index(), "Symbol", "Close", "Closing Prices — " + str(tm_date)),
                        use_container_width=True,
                    )
                except Exception as exc:
                    log.error("Tab6: bar chart failed: %s", exc)
        log.info("Tab6 Time Machine rendered in %.0f ms", (time.perf_counter() - t0) * 1000)
    except Exception as exc:
        log.error("Tab6 fatal: %s", exc, exc_info=True)
        st.error("Time Machine error: " + str(exc))

# ── Tab 7: Alerts ───────────────────────────────────────────────────────────
with tabs[7]:
    try:
        t0 = time.perf_counter()
        _hero("🔔 Price Alerts", "Get notified by email when a stock hits your target")

        # ── Delivery channel status ──────────────────────────────────────────
        if smtp_configured():
            st.success("📧 Email alerts: **configured**")
        else:
            st.warning("📧 Email alerts: not configured — add [smtp] to Streamlit Cloud Secrets")

        _divider()

        # ── Add new alert ────────────────────────────────────────────────────
        _sec("➕ Add New Alert")
        with st.form("add_alert_form", clear_on_submit=True):
            al_email = st.text_input("📧 Your Email", placeholder="you@example.com")

            r2c1, r2c2, r2c3 = st.columns([2, 1, 1])
            with r2c1:
                al_stock_name = st.selectbox("Stock", [s["name"] for s in NIFTY50], key="al_stock")
            with r2c2:
                al_direction = st.selectbox("Alert when price", ["rises above ↑", "drops below ↓"])
            with r2c3:
                al_sym    = next(s["symbol"] for s in NIFTY50 if s["name"] == al_stock_name)
                live_data = fetch_ticker(al_sym, "5d")
                live_px   = safe_float(live_data["Close"].iloc[-1]) if not live_data.empty and "Close" in live_data.columns else 100.0
                al_thresh = st.number_input(
                    "Target Price (Rs.)",
                    min_value=0.01,
                    value=round(live_px, 2),
                    step=1.0,
                )

            submitted = st.form_submit_button("🔔 Set Alert", type="primary", use_container_width=True)
            if submitted:
                if not al_email:
                    st.error("Enter your email to receive the alert.")
                elif not al_email.strip().count("@"):
                    st.error("Enter a valid email address.")
                else:
                    direction = "above" if "above" in al_direction else "below"
                    add_alert(
                        stock=al_stock_name,
                        symbol=al_sym,
                        direction=direction,
                        threshold=al_thresh,
                        email=al_email,
                        phone="",
                    )
                    st.success(f"✅ Alert set: {al_stock_name} {'>' if direction == 'above' else '<'} Rs.{al_thresh:,.2f}")

        _divider()

        # ── Active alerts ────────────────────────────────────────────────────
        alerts = get_alerts()
        active  = [a for a in alerts if not a["triggered"]]
        fired   = [a for a in alerts if a["triggered"]]

        _sec(f"📋 Active Alerts ({len(active)})")
        if not active:
            st.caption("No active alerts. Add one above.")
        else:
            for al in active:
                col_info, col_del = st.columns([5, 1])
                with col_info:
                    arrow = "↑" if al["direction"] == "above" else "↓"
                    st.markdown(
                        f"**{al['stock']}** price {arrow} Rs.{al['threshold']:,.2f}  "
                        f"· 📧 {al['email']}  · `#{al['id']}`"
                    )
                with col_del:
                    if st.button("🗑️", key=f"del_{al['id']}", help="Remove this alert"):
                        remove_alert(al["id"])
                        st.rerun()

        # ── Fire check on every refresh ──────────────────────────────────────
        if active:
            try:
                live_rows = _build_stock_rows_cached()
                price_map = dict(zip(
                    [s["symbol"] for s in NIFTY50],
                    live_rows["_curr"].fillna(0).tolist(),
                )) if "_curr" in live_rows.columns else {}
                n_fired = fire_alerts(price_map)
                if n_fired:
                    st.toast(f"🔔 {n_fired} alert(s) triggered!", icon="🔔")
                    st.rerun()
            except Exception as exc:
                log.error("Alerts fire_alerts failed: %s", exc)

        # ── Triggered history ────────────────────────────────────────────────
        if fired:
            with st.expander(f"✅ Triggered Alerts ({len(fired)})", expanded=False):
                for al in fired:
                    arrow = "↑" if al["direction"] == "above" else "↓"
                    st.markdown(
                        f"~~**{al['stock']}**~~ price {arrow} Rs.{al['threshold']:,.2f}  "
                        f"· 📧 {al['email']}  · `#{al['id']}` · {al['created']}"
                    )

        # ── Notification dispatch log ────────────────────────────────────────
        alert_log = st.session_state.get("_alert_log", [])
        if alert_log:
            with st.expander("📜 Notification Log", expanded=False):
                for entry in alert_log:
                    st.text(entry)

        log.info("Tab7 Alerts rendered in %.0f ms", (time.perf_counter() - t0) * 1000)
    except Exception as exc:
        log.error("Tab7 fatal: %s", exc, exc_info=True)
        st.error("Alerts error: " + str(exc))
