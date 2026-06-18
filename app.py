"""NSE & Nifty 50 Tracker — Streamlit entry point.

app.py is intentionally thin: startup, sidebar, status banner, tab wiring.
All tab logic lives in tabs/tab_*.py (NOT pages/ — to avoid duplicate URL registration).
"""
import time
import warnings
from datetime import datetime

import pytz
import streamlit as st

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="NSE & Nifty 50 Tracker",
    page_icon="chart_with_upwards_trend",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from utils.logger import get_logger, read_recent_logs, log_file_path

log = get_logger(__name__)
log.info("app.py startup")

# Inject responsive CSS before any content renders
from utils.mobile_css import inject_mobile_css
inject_mobile_css()

try:
    from utils.theme import inject, inject_topbar
    inject()
    inject_topbar()
except ImportError as exc:
    log.warning("theme module unavailable: %s", exc)
except Exception as exc:  # noqa: BLE001
    log.error("theme injection failed: %s", exc, exc_info=True)

from utils.constants import REFRESH_MS, CACHE_TTL
from utils.data import (
    is_nse_open,
    fetch_intraday,
    fetch_all_stocks_5d,
    get_source_status,
)
from utils.calculations import build_stock_rows

market_open, market_status, last_close_label = is_nse_open()


@st.cache_data(ttl=CACHE_TTL)
def _build_stock_rows_cached():
    return build_stock_rows(fetch_all_stocks_5d(), market_open, fetch_intraday)


def _show_data_warnings() -> None:
    for w in st.session_state.get("data_warnings", []):
        st.warning(w)


# ── Sidebar ──────────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### \u2699\ufe0f System")
    with st.expander("\U0001f50c Data Source Status", expanded=False):
        try:
            src = get_source_status()
            icons = {
                "ok": "\U0001f7e2",
                "degraded": "\U0001f7e1",
                "down": "\U0001f534",
                "not installed": "\u26ab",
            }
            st.markdown(f"{icons.get(src.get('yfinance','?'),'?')} **Yahoo Finance**: `{src.get('yfinance','?')}`")
            st.markdown(f"{icons.get(src.get('nselib','?'),'?')} **NSE (nselib)**: `{src.get('nselib','?')}`")
        except Exception as exc:  # noqa: BLE001
            log.error("sidebar: get_source_status failed: %s", exc, exc_info=True)
            st.caption("Status unavailable")
    with st.expander("\U0001f4cb Live Logs", expanded=False):
        try:
            n_lines = st.slider("Lines", 20, 200, 50, step=10, key="log_lines")
            level_filter = st.selectbox(
                "Min level",
                ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                index=2, key="log_level_filter",
            )
            lines = read_recent_logs(n_lines)
            if level_filter != "ALL":
                lvl_order = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                min_idx = lvl_order.index(level_filter)
                lines = [l for l in lines if any(lv in l for lv in lvl_order[min_idx:])]
            st.code("\n".join(lines) if lines else "No log entries yet.", language="")
            st.caption(f"Log file: `{log_file_path()}`")
        except (OSError, ValueError) as exc:
            log.error("sidebar: log viewer failed: %s", exc, exc_info=True)
            st.caption("Log viewer unavailable")
        except Exception as exc:  # noqa: BLE001
            log.error("sidebar: log viewer unexpected: %s", exc, exc_info=True)
            st.caption("Log viewer unavailable")


# ── Live status banner ───────────────────────────────────────────────────────────────────────────────────────
@st.fragment(run_every=REFRESH_MS / 1000 if market_open else None)
def _status_banner() -> None:
    try:
        ist_now = datetime.now(pytz.timezone("Asia/Kolkata"))
        ist_str = ist_now.strftime("%I:%M:%S %p IST")
        if market_open:
            pulse = "[LIVE]" if int(time.time()) % 2 == 0 else "[ -- ]"
            next_data_in = CACHE_TTL - (int(time.time()) % CACHE_TTL)
            st.success(
                pulse + "  NSE LIVE  |  " + ist_str
                + "  |  Refreshing every 5s  |  New data in "
                + str(next_data_in) + "s  |  MARKET OPEN"
            )
        else:
            st.warning(
                "NSE CLOSED \u2014 " + market_status
                + (" | " + last_close_label if last_close_label else "")
                + " | Showing last closing prices"
            )
    except Exception as exc:  # noqa: BLE001
        log.error("_status_banner failed: %s", exc, exc_info=True)
        st.info("NSE Tracker")


_status_banner()
_show_data_warnings()

# ── Tabs ────────────────────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "Market Overview",
    "Nifty 50 Index",
    "All 50 Companies",
    "Gainers & Losers",
    "P&L Calculator",
    "Stock Chart",
    "Time Machine",
    "\U0001f514 Alerts",
])

_ctx = dict(
    market_open=market_open,
    market_status=market_status,
    last_close_label=last_close_label,
)

# NOTE: ALL imports use tabs/ (not pages/) so Streamlit never registers them as pages.
with tabs[0]:
    from tabs.tab_overview import render as _r0
    _r0(**_ctx)

with tabs[1]:
    from tabs.tab_nifty import render as _r1
    _r1(**_ctx)

with tabs[2]:
    from tabs.tab_companies import render as _r2  # fixed: was pages.tab_companies
    _r2(**_ctx, build_stock_rows_cached=_build_stock_rows_cached)

with tabs[3]:
    from tabs.tab_gainers import render as _r3
    _r3(**_ctx, build_stock_rows_cached=_build_stock_rows_cached)

with tabs[4]:
    from tabs.tab_pl import render as _r4
    _r4(**_ctx)

with tabs[5]:
    from tabs.tab_chart import render as _r5
    _r5(**_ctx)

with tabs[6]:
    from tabs.tab_timemachine import render as _r6
    _r6()

with tabs[7]:
    from tabs.tab_alerts import render as _r7
    _r7(build_stock_rows_cached=_build_stock_rows_cached)
