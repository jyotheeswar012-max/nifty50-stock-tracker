"""Tab 6 — Time Machine (historical snapshot)."""
from datetime import date

import streamlit as st

from utils.logger import get_logger
from utils.constants import FAMOUS_DATES
from utils.calculations import build_time_machine_snapshot
from utils.charts import build_closing_bar

log = get_logger(__name__)


def _sanitize_snapshot(df):
    """Coerce strictly-numeric string columns; leave formatted strings intact."""
    import pandas as pd
    _PURE_NUM = r"^[\-+]?[\d,\.]+$"
    df = df.copy()
    for col in df.columns:
        if df[col].dtype != object:
            continue
        non_null = df[col].dropna()
        if non_null.empty:
            continue
        if non_null.astype(str).str.match(_PURE_NUM).all() and df[col].isna().mean() <= 0.05:
            try:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(",", "", regex=False),
                    errors="raise",
                )
            except (ValueError, TypeError) as exc:
                log.warning("tab_timemachine: skipping coerce for '%s': %s", col, exc)
    return df


def render() -> None:
    from utils.app_helpers import hero
    from utils.data import fetch_all_history
    hero("Time Machine", "Travel back to any NSE trading day")

    preset = st.selectbox(
        "Famous dates",
        ["Custom..."] + list(FAMOUS_DATES.keys()),
        key="tm_preset",
    )
    if preset == "Custom...":
        tm_date = st.date_input(
            "Date",
            value=date(2020, 3, 23),
            min_value=date(2010, 1, 1),
            max_value=date.today(),
            key="tm_date",
        )
    else:
        tm_date = FAMOUS_DATES[preset]
        st.info("Loaded: " + preset + " \u2014 " + str(tm_date))

    if st.button("Travel to this date", key="tm_go"):
        with st.spinner("Loading historical data (may take 30\u201360s first time)..."):
            try:
                all_hist = fetch_all_history()
            except OSError as exc:
                log.error("tab_timemachine: network error in fetch_all_history: %s", exc, exc_info=True)
                st.error("Network error — could not load historical data.")
                return
            except Exception as exc:  # noqa: BLE001
                log.error("tab_timemachine: unexpected error in fetch_all_history: %s", exc, exc_info=True)
                st.error("Could not load historical data.")
                return

        try:
            snap = build_time_machine_snapshot(all_hist, tm_date)
        except (KeyError, ValueError) as exc:
            log.error(
                "tab_timemachine: snapshot build error date=%s: %s", tm_date, exc, exc_info=True
            )
            st.error("Could not build snapshot for this date.")
            return
        except Exception as exc:  # noqa: BLE001
            log.error(
                "tab_timemachine: unexpected snapshot error date=%s: %s", tm_date, exc, exc_info=True
            )
            st.error("Unexpected error building snapshot.")
            return

        if snap.empty:
            log.warning("tab_timemachine: empty snapshot for date=%s", tm_date)
            st.error("No data for this date. Try a nearby trading day.")
            return

        st.success("Snapshot for " + str(tm_date))
        st.dataframe(_sanitize_snapshot(snap), use_container_width=True)

        try:
            fig = build_closing_bar(
                snap.reset_index(),
                "Symbol",
                "Close",
                "Closing Prices \u2014 " + str(tm_date),
            )
            fig.update_layout(autosize=True)
            st.plotly_chart(fig, use_container_width=True)
        except (KeyError, ValueError) as exc:
            log.error("tab_timemachine: closing bar chart error: %s", exc, exc_info=True)
        except Exception as exc:  # noqa: BLE001
            log.error("tab_timemachine: closing bar unexpected: %s", exc, exc_info=True)
