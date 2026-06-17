"""Tab 2 — All 50 Companies."""
import pandas as pd
import streamlit as st

from utils.logger import get_logger
from utils.constants import NIFTY50
from utils.charts import build_pct_bar

log = get_logger(__name__)


def _sanitize_numeric_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce strictly-numeric object columns to float64.
    Only columns where *every* non-null value is a plain number string
    (no currency prefix, no percent suffix) are touched.
    """
    _PURE_NUM = r"^[\-+]?[\d,\.]+$"
    df = df.copy()
    for col in df.columns:
        if df[col].dtype != object or df[col].dtype == bool:
            continue
        non_null = df[col].dropna()
        if non_null.empty or non_null.astype(str).str.match(_PURE_NUM).all() is False:
            continue
        null_frac = df[col].isna().mean()
        if null_frac > 0.05:
            continue
        try:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="raise",
            )
        except (ValueError, TypeError) as exc:
            log.warning("tab_companies: skipping coercion of '%s': %s", col, exc)
    return df


def render(
    market_open: bool,
    _market_status: str,
    _last_close_label: str,
    build_stock_rows_cached,
) -> None:
    from utils.app_helpers import hero, closed_banner
    hero(
        "All 50 Companies",
        "Live prices" if market_open else "Last closing prices",
    )
    closed_banner(market_open, _market_status, _last_close_label)

    sectors = ["All"] + sorted({s["sector"] for s in NIFTY50})
    sel_sec = st.selectbox("Sector", sectors, key="all_sec")

    try:
        df_rows = build_stock_rows_cached()
    except Exception as exc:  # noqa: BLE001
        log.error("tab_companies: build_stock_rows_cached failed: %s", exc, exc_info=True)
        st.error("Could not load stock data.")
        return

    if sel_sec != "All":
        df_rows = df_rows[df_rows["Sector"] == sel_sec]

    st.dataframe(
        _sanitize_numeric_cols(df_rows.drop(columns=["_curr", "_pct"], errors="ignore")),
        use_container_width=True,
        hide_index=True,
    )

    valid = df_rows[df_rows["_pct"].notna()].copy()
    if not valid.empty:
        try:
            title = "1-Day % Change" if market_open else "1-Day % Change (last session)"
            fig = build_pct_bar(valid, "Symbol", "_pct", title, text_col="Change (%)")
            fig.update_layout(autosize=True)
            st.plotly_chart(fig, use_container_width=True)
        except ValueError as exc:
            log.error("tab_companies: bar chart ValueError: %s", exc, exc_info=True)
        except Exception as exc:  # noqa: BLE001
            log.error("tab_companies: bar chart unexpected: %s", exc, exc_info=True)
