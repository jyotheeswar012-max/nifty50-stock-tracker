"""
Page: Options Chain & PCR

TWO data sources:
  Tab A — NSE Index Options  (NIFTY / BANKNIFTY / FINNIFTY / MIDCPNIFTY)
            via official NSE India API with session-cookie auth.
  Tab B — Stock Options      (individual Nifty-50 constituents)
            via yfinance.

All errors are caught and shown as friendly Streamlit warnings —
no unhandled exceptions reach the user.
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from typing import Optional, Tuple, Dict, List
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Options Chain", page_icon="📈", layout="wide")

# ================================================================== constants

INDEX_SYMBOLS: List[str] = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]

STOCK_NAMES: List[str] = [
    "Reliance Industries", "HDFC Bank", "ICICI Bank", "Infosys", "TCS",
    "Bharti Airtel", "ITC", "Kotak Mahindra Bank", "Larsen & Toubro",
    "HCL Technologies", "Axis Bank", "State Bank of India", "Bajaj Finance",
    "Wipro", "Asian Paints", "Maruti Suzuki", "Sun Pharmaceutical",
    "Titan Company", "UltraTech Cement", "ONGC", "NTPC", "Tata Motors",
    "Tata Steel", "Adani Enterprises", "Adani Ports", "Bajaj Auto",
    "Cipla", "Dr. Reddy's Labs", "Hindustan Unilever",
    "Mahindra & Mahindra", "Eicher Motors", "Hero MotoCorp",
]

STOCK_SYM_MAP: Dict[str, str] = {
    "Reliance Industries":  "RELIANCE.NS",
    "HDFC Bank":            "HDFCBANK.NS",
    "ICICI Bank":           "ICICIBANK.NS",
    "Infosys":              "INFY.NS",
    "TCS":                  "TCS.NS",
    "Bharti Airtel":        "BHARTIARTL.NS",
    "ITC":                  "ITC.NS",
    "Kotak Mahindra Bank":  "KOTAKBANK.NS",
    "Larsen & Toubro":      "LT.NS",
    "HCL Technologies":     "HCLTECH.NS",
    "Axis Bank":            "AXISBANK.NS",
    "State Bank of India":  "SBIN.NS",
    "Bajaj Finance":        "BAJFINANCE.NS",
    "Wipro":                "WIPRO.NS",
    "Asian Paints":         "ASIANPAINT.NS",
    "Maruti Suzuki":        "MARUTI.NS",
    "Sun Pharmaceutical":   "SUNPHARMA.NS",
    "Titan Company":        "TITAN.NS",
    "UltraTech Cement":     "ULTRACEMCO.NS",
    "ONGC":                 "ONGC.NS",
    "NTPC":                 "NTPC.NS",
    "Tata Motors":          "TATAMOTORS.NS",
    "Tata Steel":           "TATASTEEL.NS",
    "Adani Enterprises":    "ADANIENT.NS",
    "Adani Ports":          "ADANIPORTS.NS",
    "Bajaj Auto":           "BAJAJAUTO.NS",
    "Cipla":                "CIPLA.NS",
    "Dr. Reddy's Labs":     "DRREDDY.NS",
    "Hindustan Unilever":   "HINDUNILVR.NS",
    "Mahindra & Mahindra":  "M&M.NS",
    "Eicher Motors":        "EICHERMOT.NS",
    "Hero MotoCorp":        "HEROMOTOCO.NS",
}

NSE_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":           "application/json, text/plain, */*",
    "Accept-Language":  "en-US,en;q=0.9",
    "Referer":          "https://www.nseindia.com/",
    "X-Requested-With": "XMLHttpRequest",
}


# ================================================================== helpers

def safe_float(val, default: float = 0.0) -> float:
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default


# -------- NSE session (cookie auth required) ------------------------

@st.cache_resource(ttl=600)
def get_nse_session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update(NSE_HEADERS)
    try:
        sess.get("https://www.nseindia.com/", timeout=10)
    except Exception:
        pass
    return sess


@st.cache_data(ttl=300)
def fetch_nse_index_chain(symbol: str) -> Optional[dict]:
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    try:
        sess = get_nse_session()
        resp = sess.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        # Cookie may have expired — retry once with a fresh session
        try:
            st.cache_resource.clear()
            sess = get_nse_session()
            resp = sess.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None


def parse_nse_chain(
    raw: dict, expiry: str
) -> Tuple[pd.DataFrame, pd.DataFrame, float]:
    records = raw.get("records", {})
    spot    = safe_float(records.get("underlyingValue", 0))
    ce_rows: List[dict] = []
    pe_rows: List[dict] = []

    for item in records.get("data", []):
        if item.get("expiryDate", "").strip() != expiry.strip():
            continue
        strike = safe_float(item.get("strikePrice", 0))
        for key, rows in (("CE", ce_rows), ("PE", pe_rows)):
            if key not in item:
                continue
            leg = item[key]
            rows.append({
                "strike":               strike,
                "lastPrice":            safe_float(leg.get("lastPrice")),
                "bid":                  safe_float(leg.get("bidprice")),
                "ask":                  safe_float(leg.get("askPrice")),
                "volume":               int(safe_float(leg.get("totalTradedVolume"))),
                "openInterest":         int(safe_float(leg.get("openInterest"))),
                "changeinOpenInterest": int(safe_float(leg.get("changeinOpenInterest"))),
                "impliedVolatility":    safe_float(leg.get("impliedVolatility")) / 100.0,
                "pChange":              safe_float(leg.get("pChange")),
            })

    calls = pd.DataFrame(ce_rows).sort_values("strike").reset_index(drop=True) if ce_rows else pd.DataFrame()
    puts  = pd.DataFrame(pe_rows).sort_values("strike").reset_index(drop=True) if pe_rows else pd.DataFrame()
    return calls, puts, spot


# -------- yfinance stock options ------------------------------------

@st.cache_data(ttl=60)
def get_spot_yf(sym: str) -> Optional[float]:
    try:
        h = yf.Ticker(sym).history(period="1d", interval="1m")
        if h is not None and not h.empty:
            return safe_float(h["Close"].iloc[-1])
    except Exception:
        pass
    return None


@st.cache_data(ttl=300)
def get_expiries_yf(sym: str) -> list:
    try:
        opts = yf.Ticker(sym).options
        return list(opts) if opts else []
    except Exception:
        return []


@st.cache_data(ttl=300)
def get_chain_yf(sym: str, expiry: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    tk    = yf.Ticker(sym)
    oc    = tk.option_chain(expiry)
    calls = oc.calls.copy().reset_index(drop=True)
    puts  = oc.puts.copy().reset_index(drop=True)
    for df in (calls, puts):
        df["strike"] = pd.to_numeric(df["strike"], errors="coerce")
        if "openInterest" not in df.columns:
            df["openInterest"] = 0.0
        df["openInterest"] = pd.to_numeric(
            df["openInterest"], errors="coerce").fillna(0)
        if "impliedVolatility" not in df.columns:
            df["impliedVolatility"] = np.nan
    calls = calls.dropna(subset=["strike"]).reset_index(drop=True)
    puts  = puts.dropna(subset=["strike"]).reset_index(drop=True)
    return calls, puts


# -------- shared analytics ------------------------------------------

def calc_max_pain(
    calls: pd.DataFrame, puts: pd.DataFrame
) -> Optional[float]:
    if calls.empty or puts.empty:
        return None
    c_s = calls["strike"].values.astype(float)
    c_o = calls["openInterest"].values.astype(float)
    p_s = puts["strike"].values.astype(float)
    p_o = puts["openInterest"].values.astype(float)
    candidates = sorted(set(c_s.tolist()) | set(p_s.tolist()))
    if not candidates:
        return None
    min_pain: float = float("inf")
    best_k: Optional[float] = None
    for K in candidates:
        total = (
            float(np.sum(c_o * np.maximum(0.0, c_s - K))) +
            float(np.sum(p_o * np.maximum(0.0, K - p_s)))
        )
        if total < min_pain:
            min_pain, best_k = total, K
    return best_k


def build_oi_df(
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    spot: Optional[float],
    window: float = 0.15,
) -> pd.DataFrame:
    if calls.empty and puts.empty:
        return pd.DataFrame(columns=["Strike", "Call OI", "Put OI"])
    c = (calls[["strike", "openInterest"]]
         .rename(columns={"strike": "Strike", "openInterest": "Call OI"})
         .copy())
    p = (puts[["strike", "openInterest"]]
         .rename(columns={"strike": "Strike", "openInterest": "Put OI"})
         .copy())
    c["Call OI"] = c["Call OI"].astype(float)
    p["Put OI"]  = p["Put OI"].astype(float)
    merged = (
        pd.merge(c, p, on="Strike", how="outer")
        .fillna(0).sort_values("Strike").reset_index(drop=True)
    )
    if spot and spot > 0:
        merged = merged[
            (merged["Strike"] >= spot * (1 - window)) &
            (merged["Strike"] <= spot * (1 + window))
        ].reset_index(drop=True)
    return merged


def render_oi_chart(
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    spot: Optional[float],
    max_pain: Optional[float],
    title: str,
) -> None:
    try:
        oi_df = build_oi_df(calls, puts, spot)
        if oi_df.empty:
            oi_df = build_oi_df(calls, puts, None)
        if oi_df.empty:
            st.info("ℹ️ No OI data to display.")
            return
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=oi_df["Strike"], y=oi_df["Call OI"],
            name="Call OI", marker_color="#00c853"))
        fig.add_trace(go.Bar(
            x=oi_df["Strike"], y=-oi_df["Put OI"],
            name="Put OI", marker_color="#ff1744"))
        if spot:
            fig.add_vline(x=spot, line_dash="dash", line_color="#ffd600",
                          annotation_text=f"Spot {spot:,.0f}",
                          annotation_position="top right")
        if max_pain:
            fig.add_vline(x=max_pain, line_dash="dot", line_color="#ea80fc",
                          annotation_text=f"Max Pain {max_pain:,.0f}",
                          annotation_position="top left")
        fig.update_layout(
            title=title, template="plotly_dark", barmode="relative",
            height=480, bargap=0.1,
            xaxis_title="Strike",
            yaxis_title="Open Interest (Call ↑ / Put ↓)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ OI chart error: {e}")


def render_iv_chart(
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    spot: Optional[float],
    title: str,
) -> None:
    try:
        if "impliedVolatility" not in calls.columns:
            st.info("ℹ️ IV data not available.")
            return
        iv_c = calls[["strike", "impliedVolatility"]].rename(
            columns={"strike": "Strike", "impliedVolatility": "Call IV"})
        iv_p = puts[["strike",  "impliedVolatility"]].rename(
            columns={"strike": "Strike", "impliedVolatility": "Put IV"})
        iv_df = (
            pd.merge(iv_c, iv_p, on="Strike", how="outer")
            .sort_values("Strike").reset_index(drop=True)
        )
        iv_df["Call IV"] = (iv_df["Call IV"].fillna(0) * 100).round(2)
        iv_df["Put IV"]  = (iv_df["Put IV"].fillna(0)  * 100).round(2)
        if spot and spot > 0:
            iv_df = iv_df[
                (iv_df["Strike"] >= spot * 0.85) &
                (iv_df["Strike"] <= spot * 1.15)
            ].reset_index(drop=True)
        if iv_df.empty:
            st.info("ℹ️ No IV data in range.")
            return
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=iv_df["Strike"], y=iv_df["Call IV"],
            mode="lines+markers", name="Call IV %",
            line=dict(color="#00c853", width=2)))
        fig.add_trace(go.Scatter(
            x=iv_df["Strike"], y=iv_df["Put IV"],
            mode="lines+markers", name="Put IV %",
            line=dict(color="#ff1744", width=2)))
        if spot:
            fig.add_vline(x=spot, line_dash="dash", line_color="#ffd600",
                          annotation_text="Spot")
        fig.update_layout(
            title=title, template="plotly_dark", height=360,
            xaxis_title="Strike", yaxis_title="IV (%)")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ IV chart error: {e}")


def render_pcr_metrics(calls: pd.DataFrame, puts: pd.DataFrame) -> None:
    total_c = safe_float(calls["openInterest"].sum()) if not calls.empty else 0.0
    total_p = safe_float(puts["openInterest"].sum())  if not puts.empty  else 0.0
    pcr     = round(total_p / total_c, 3) if total_c > 0 else 0.0
    if   pcr < 0.7: label = "🔴 Bearish (PCR < 0.7)"
    elif pcr > 1.3: label = "🟢 Bullish (PCR > 1.3)"
    else:           label = "🟡 Neutral (0.7–1.3)"
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Call OI", f"{int(total_c):,}")
    c2.metric("Total Put OI",  f"{int(total_p):,}")
    c3.metric("PCR",           f"{pcr:.3f}")
    c4.metric("Signal",        label)


def render_raw_tables(calls: pd.DataFrame, puts: pd.DataFrame) -> None:
    COLS = [
        "strike", "lastPrice", "bid", "ask",
        "volume", "openInterest", "changeinOpenInterest", "impliedVolatility",
    ]
    RENAME = {
        "strike":               "Strike",
        "lastPrice":            "Last Price",
        "bid":                  "Bid",
        "ask":                  "Ask",
        "volume":               "Volume",
        "openInterest":         "OI",
        "changeinOpenInterest": "OI Change",
        "impliedVolatility":    "IV (%)",
    }
    t1, t2 = st.tabs(["🟢 Calls (CE)", "🔴 Puts (PE)"])
    for tab_obj, df in ((t1, calls), (t2, puts)):
        with tab_obj:
            if df.empty:
                st.info("ℹ️ No data.")
                continue
            present = [c for c in COLS if c in df.columns]
            disp = df[present].copy().reset_index(drop=True)
            if "impliedVolatility" in disp.columns:
                disp["impliedVolatility"] = (disp["impliedVolatility"] * 100).round(2)
            disp.rename(columns=RENAME, inplace=True)
            st.dataframe(disp, use_container_width=True, hide_index=True)


def render_max_pain_info(
    calls: pd.DataFrame, puts: pd.DataFrame, spot: Optional[float]
) -> Optional[float]:
    """Compute and display max pain. Returns the strike value (or None)."""
    mp: Optional[float] = None
    try:
        mp = calc_max_pain(calls, puts)
        if mp is not None:
            dist_str = ""
            if spot and spot > 0:
                pct      = (mp - spot) / spot * 100
                dist_str = f" • {pct:+.1f}% from spot"
            st.info(
                f"🕹️ **Max Pain: {mp:,.0f}**{dist_str} — "
                "strike where option writers lose the least at expiry"
            )
    except Exception as e:
        st.warning(f"⚠️ Max Pain error: {e}")
    return mp


# ================================================================== PAGE

st.title("📈 Options Chain & PCR")
st.markdown("""
Two data sources in one page:
- **🟦 Index Options** (NIFTY / BANKNIFTY / FINNIFTY / MIDCPNIFTY) — via **NSE India official API**
- **🏢 Stock Options** (Nifty-50 F&O stocks) — via **Yahoo Finance**
""")

tab_index, tab_stock = st.tabs([
    "🟦 Index Options (Nifty / BankNifty)",
    "🏢 Stock Options (F&O Stocks)",
])


# ------------------------------------------------------------------
# TAB A — NSE INDEX OPTIONS
# ------------------------------------------------------------------
with tab_index:
    st.subheader("🟦 Index Options via NSE API")
    st.caption("📍 Data from nseindia.com — requires internet & NSE server availability")

    ia_col1, ia_col2 = st.columns(2)
    with ia_col1:
        idx_sym = st.selectbox("📊 Index", INDEX_SYMBOLS, key="idx_sym")
    with ia_col2:
        if st.button("🔄 Refresh", key="idx_refresh"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()

    with st.spinner(f"Fetching {idx_sym} option chain from NSE…"):
        raw_data = fetch_nse_index_chain(idx_sym)

    if raw_data is None:
        st.error(
            "❌ Could not fetch data from NSE India API.\n\n"
            "Possible reasons:\n"
            "- NSE rate-limiting — wait 30 s and click **Refresh**\n"
            "- Network / firewall blocking nseindia.com\n"
            "- NSE server maintenance\n\n"
            "**Tip:** Click Refresh 1–2 times to open a fresh session."
        )
    else:
        expiry_dates: list = raw_data.get("records", {}).get("expiryDates", [])
        spot_val: float    = safe_float(
            raw_data.get("records", {}).get("underlyingValue", 0))

        if not expiry_dates:
            st.warning("⚠️ No expiry dates found in NSE response.")
        else:
            ib_col1, ib_col2 = st.columns(2)
            with ib_col1:
                expiry_sel: str = st.selectbox(
                    "📅 Expiry", expiry_dates, key="idx_expiry")
            with ib_col2:
                if spot_val:
                    st.metric("📌 Spot", f"{spot_val:,.2f}")

            # Parse chain
            idx_calls = pd.DataFrame()
            idx_puts  = pd.DataFrame()
            try:
                idx_calls, idx_puts, _ = parse_nse_chain(raw_data, expiry_sel)
            except Exception as parse_err:
                st.error(f"❌ Parse error: {parse_err}")

            if idx_calls.empty and idx_puts.empty:
                st.warning("⚠️ No data for this expiry — try another date.")
            else:
                render_pcr_metrics(idx_calls, idx_puts)
                mp_idx = render_max_pain_info(idx_calls, idx_puts, spot_val)
                st.markdown("---")

                st.subheader("📊 OI Heatmap")
                render_oi_chart(
                    idx_calls, idx_puts, spot_val, mp_idx,
                    f"{idx_sym} — Call vs Put OI ({expiry_sel})",
                )

                # OI Change chart (index only — NSE provides changeinOpenInterest)
                if "changeinOpenInterest" in idx_calls.columns:
                    st.subheader("📉 OI Change (Build-up / Unwinding)")
                    try:
                        c_chg = idx_calls[["strike", "changeinOpenInterest"]].rename(
                            columns={"strike": "Strike", "changeinOpenInterest": "Call OI Δ"})
                        p_chg = idx_puts[["strike", "changeinOpenInterest"]].rename(
                            columns={"strike": "Strike", "changeinOpenInterest": "Put OI Δ"})
                        chg_df = (
                            pd.merge(c_chg, p_chg, on="Strike", how="outer")
                            .fillna(0)
                        )
                        if spot_val > 0:
                            chg_df = chg_df[
                                (chg_df["Strike"] >= spot_val * 0.85) &
                                (chg_df["Strike"] <= spot_val * 1.15)
                            ]
                        if not chg_df.empty:
                            fig_chg = go.Figure()
                            fig_chg.add_trace(go.Bar(
                                x=chg_df["Strike"], y=chg_df["Call OI Δ"],
                                name="Call OI Δ", marker_color="#69f0ae"))
                            fig_chg.add_trace(go.Bar(
                                x=chg_df["Strike"], y=-chg_df["Put OI Δ"],
                                name="Put OI Δ", marker_color="#ff6d00"))
                            if spot_val:
                                fig_chg.add_vline(
                                    x=spot_val, line_dash="dash",
                                    line_color="#ffd600",
                                    annotation_text="Spot")
                            fig_chg.update_layout(
                                title=f"{idx_sym} — OI Change ({expiry_sel})",
                                template="plotly_dark", barmode="relative",
                                height=380, bargap=0.1,
                                xaxis_title="Strike",
                                yaxis_title="OI Change (Call ↑ / Put ↓)",
                            )
                            st.plotly_chart(fig_chg, use_container_width=True)
                    except Exception as chg_err:
                        st.warning(f"⚠️ OI Change chart: {chg_err}")

                st.subheader("📉 IV Smile")
                render_iv_chart(
                    idx_calls, idx_puts, spot_val,
                    f"{idx_sym} — IV Smile ({expiry_sel})",
                )

                st.subheader("📊 Raw Chain Data")
                render_raw_tables(idx_calls, idx_puts)


# ------------------------------------------------------------------
# TAB B — STOCK OPTIONS (yfinance)
# ------------------------------------------------------------------
with tab_stock:
    st.subheader("🏢 Stock Options via Yahoo Finance")
    st.caption("📍 Yahoo Finance — individual NSE F&O stocks only")

    sc_col1, sc_col2 = st.columns(2)
    with sc_col1:
        sel_name: str = st.selectbox(
            "🏢 Underlying Stock", STOCK_NAMES, key="stk_name")
    with sc_col2:
        stk_sym: str      = STOCK_SYM_MAP.get(sel_name, "RELIANCE.NS")
        stk_expiries: list = get_expiries_yf(stk_sym)
        if not stk_expiries:
            st.error(
                f"❌ No options for **{sel_name}** (`{stk_sym}`) on Yahoo Finance. "
                "Try Reliance, HDFC Bank, TCS, or Infosys."
            )
            # Use st.empty to avoid st.stop() breaking other tabs
            stk_expiries = []
        else:
            expiry_stk: str = st.selectbox(
                "📅 Expiry", stk_expiries, key="stk_expiry")

    if stk_expiries:   # only proceed if we have expiries
        spot_stk = get_spot_yf(stk_sym)
        if spot_stk:
            st.metric("📌 Spot Price", f"₹{spot_stk:,.2f}")
        else:
            st.warning("⚠️ Live spot unavailable.")
            spot_stk = None

        stk_calls = pd.DataFrame()
        stk_puts  = pd.DataFrame()
        with st.spinner(f"Fetching {sel_name} options…"):
            try:
                stk_calls, stk_puts = get_chain_yf(stk_sym, expiry_stk)
            except Exception as fetch_err:
                st.error(f"❌ {fetch_err}")

        if stk_calls.empty and stk_puts.empty:
            st.warning("⚠️ Options chain is empty.")
        else:
            render_pcr_metrics(stk_calls, stk_puts)
            mp_stk = render_max_pain_info(stk_calls, stk_puts, spot_stk)
            st.markdown("---")

            st.subheader("📊 OI Heatmap")
            render_oi_chart(
                stk_calls, stk_puts, spot_stk, mp_stk,
                f"{sel_name} — Call vs Put OI ({expiry_stk})",
            )

            st.subheader("📉 IV Smile")
            render_iv_chart(
                stk_calls, stk_puts, spot_stk,
                f"{sel_name} — IV Smile ({expiry_stk})",
            )

            st.subheader("📊 Raw Chain Data")
            render_raw_tables(stk_calls, stk_puts)
