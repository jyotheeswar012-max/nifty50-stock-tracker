"""Tab 0 — NSE Market Overview."""
import pandas as pd
import streamlit as st

from utils.logger import get_logger
from utils.constants import NSE_INDICES, NIFTY50
from utils.data import fetch_indices, fetch_ticker
from utils.calculations import safe_float
from utils.charts import build_pct_bar, build_trend_chart, build_sector_pie

log = get_logger(__name__)

_NUMERIC_PAT = r"^[\-+]?[\d,\.]+$"


def _sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce exclusively-numeric string columns to float64 (strict)."""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype != object or df[col].dtype == bool:
            continue
        non_null = df[col].dropna()
        if non_null.empty or df[col].isna().mean() > 0.05:
            continue
        if non_null.astype(str).str.match(_NUMERIC_PAT).all():
            try:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(",", "", regex=False),
                    errors="raise",
                )
                log.debug("_sanitize_df: coerced '%s'", col)
            except (ValueError, TypeError) as exc:
                log.warning("_sanitize_df: skipping '%s': %s", col, exc)
    return df


def render(market_open: bool, market_status: str, last_close_label: str) -> None:
    from utils.app_helpers import hero, sec, divider, closed_banner
    hero("NSE Market Overview", "National Stock Exchange")
    closed_banner(market_open, market_status, last_close_label)
    sec("NSE Indices Snapshot")

    with st.spinner("Fetching index data…"):
        try:
            idx_data = fetch_indices()
        except OSError as exc:
            log.error("fetch_indices network error: %s", exc, exc_info=True)
            st.error("Network error fetching indices — please retry.")
            return
        except Exception as exc:
            log.error("fetch_indices unexpected: %s", exc, exc_info=True)
            st.error("Could not load index data.")
            return

    val_lbl = "Value" if market_open else "Last Close"
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
                    "Index": idx["name"],
                    val_lbl: "Rs." + format(c, ",.2f"),
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
            log.error("tab_overview: error for '%s': %s", idx.get("symbol"), exc, exc_info=True)
            idx_rows.append({"Index": idx["name"], val_lbl: "N/A",
                              "Change (pts)": "N/A", "Change (%)": "N/A",
                              "High": "N/A", "Low": "N/A", "_pct": None})

    idx_df = pd.DataFrame(idx_rows)
    st.dataframe(_sanitize_df(idx_df.drop(columns=["_pct"])),
                 use_container_width=True, hide_index=True)

    valid_idx = idx_df[idx_df["_pct"].notna()].copy()
    if not valid_idx.empty:
        try:
            title = "Today's % Change by Index" if market_open else "Last Session % Change by Index"
            fig = build_pct_bar(valid_idx, "Index", "_pct", title,
                                text_col="Change (%)", height=300)
            fig.update_layout(autosize=True)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:
            log.error("tab_overview: pct bar error: %s", exc, exc_info=True)

    from utils.app_helpers import divider, sec
    divider()
    sec("Nifty 50 Sector Allocation")
    try:
        sector_df = pd.DataFrame([{"Sector": s["sector"]} for s in NIFTY50])
        fig_pie = build_sector_pie(sector_df, title="Nifty 50 — Stocks per Sector", height=400)
        fig_pie.update_layout(autosize=True)
        st.plotly_chart(fig_pie, use_container_width=True)
    except Exception as exc:
        log.error("tab_overview: sector pie failed: %s", exc, exc_info=True)

    divider()
    sec("Trend Comparison")

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
        with st.spinner("Loading trend data…"):
            try:
                series = {}
                for ni in sel_idx:
                    meta = sym_map.get(ni)
                    if not meta:
                        continue
                    h = fetch_ticker(meta["symbol"], p_sel)
                    if not h.empty and "Close" in h.columns:
                        series[ni] = {"df": h, "color": meta["color"]}
            except Exception as exc:
                log.error("tab_overview: trend error: %s", exc, exc_info=True)
                st.info("Could not load trend data.")
                return

        if series:
            try:
                fig = build_trend_chart(series, height=360)
                fig.update_layout(autosize=True)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:
                log.error("tab_overview: trend chart error: %s", exc, exc_info=True)
        else:
            st.info("No data available for selected indices.")
