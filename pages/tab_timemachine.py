"""Tab 6 — Time Machine (historical snapshot)."""
from datetime import date

import streamlit as st

from utils.logger import get_logger
from utils.constants import FAMOUS_DATES
from utils.calculations import build_time_machine_snapshot
from utils.charts import build_closing_bar
from utils.export import export_buttons

log = get_logger(__name__)


def _sanitize_snapshot(df):
    import pandas as pd
    _PURE_NUM = r"^[\-+]?[\d,\.]+$"
    df = df.copy()
    for col in df.columns:
        if df[col].dtype != object:
            continue
        non_null = df[col].dropna()
        if non_null.empty or df[col].isna().mean() > 0.05:
            continue
        if non_null.astype(str).str.match(_PURE_NUM).all():
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
        "Famous dates", ["Custom..."] + list(FAMOUS_DATES.keys()), key="tm_preset",
    )
    if preset == "Custom...":
        tm_date = st.date_input(
            "Date", value=date(2020, 3, 23),
            min_value=date(2010, 1, 1), max_value=date.today(), key="tm_date",
        )
    else:
        tm_date = FAMOUS_DATES[preset]
        st.info("Loaded: " + preset + " — " + str(tm_date))

    if st.button("Travel to this date", key="tm_go"):
        # Spinner already wraps the full expensive fetch
        with st.spinner("Loading historical data for all 50 stocks (30–60 s first time)…"):
            try:
                all_hist = fetch_all_history()
            except OSError as exc:
                log.error("tab_timemachine: network error: %s", exc, exc_info=True)
                st.error("Network error — could not load historical data.")
                return
            except Exception as exc:  # noqa: BLE001
                log.error("tab_timemachine: unexpected: %s", exc, exc_info=True)
                st.error("Could not load historical data.")
                return

        try:
            snap = build_time_machine_snapshot(all_hist, tm_date)
        except (KeyError, ValueError) as exc:
            log.error("tab_timemachine: snapshot error date=%s: %s", tm_date, exc, exc_info=True)
            st.error("Could not build snapshot for this date.")
            return
        except Exception as exc:  # noqa: BLE001
            log.error("tab_timemachine: unexpected snapshot: %s", exc, exc_info=True)
            st.error("Unexpected error building snapshot.")
            return

        if snap.empty:
            log.warning("tab_timemachine: empty snapshot for %s", tm_date)
            st.error("No data for this date. Try a nearby trading day.")
            return

        st.success("Snapshot for " + str(tm_date))
        clean_snap = _sanitize_snapshot(snap)
        st.dataframe(clean_snap, use_container_width=True)

        # Export buttons
        export_buttons(
            clean_snap,
            filename_stem=f"nifty50_snapshot_{tm_date}",
            title=f"Nifty 50 Snapshot — {tm_date}",
            key_suffix=str(tm_date),
        )

        try:
            fig = build_closing_bar(
                snap.reset_index(), "Symbol", "Close",
                "Closing Prices — " + str(tm_date),
            )
            fig.update_layout(autosize=True)
            st.plotly_chart(fig, use_container_width=True)
        except (KeyError, ValueError) as exc:
            log.error("tab_timemachine: closing bar error: %s", exc, exc_info=True)
        except Exception as exc:  # noqa: BLE001
            log.error("tab_timemachine: closing bar unexpected: %s", exc, exc_info=True)
