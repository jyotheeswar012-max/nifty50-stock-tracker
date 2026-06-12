"""
Page: Options Chain & Put-Call Ratio
Fetches live NSE options data via yfinance .option_chain()
Displays OI heatmap, IV smile, PCR, max-pain level.
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Optional, Tuple
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Options Chain", page_icon="📈", layout="wide")

# ---- Symbol map (^NSEI removed — Yahoo has no index options) ----
NIFTY50_NAMES = [
    "Reliance Industries", "HDFC Bank", "ICICI Bank", "Infosys", "TCS",
    "Bharti Airtel", "ITC", "Kotak Mahindra Bank", "Larsen & Toubro",
    "HCL Technologies", "Axis Bank", "State Bank of India", "Bajaj Finance",
    "Wipro", "Asian Paints", "Maruti Suzuki", "Sun Pharmaceutical",
    "Titan Company", "UltraTech Cement", "ONGC", "NTPC", "Tata Motors",
    "Tata Steel", "Adani Enterprises", "Adani Ports", "Bajaj Auto",
    "Cipla", "Dr. Reddy's Labs", "Hindustan Unilever",
    "Mahindra & Mahindra", "Eicher Motors", "Hero MotoCorp",
]

NAME_TO_SYM = {
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

# ================================================================== helpers

def safe_float(val, default: float = 0.0) -> float:
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default


@st.cache_data(ttl=60)
def get_spot(sym: str) -> Optional[float]:
    try:
        h = yf.Ticker(sym).history(period="1d", interval="1m")
        if h is not None and not h.empty:
            return safe_float(h["Close"].iloc[-1])
    except Exception:
        pass
    return None


@st.cache_data(ttl=300)
def get_expiries(sym: str) -> list:
    try:
        opts = yf.Ticker(sym).options
        return list(opts) if opts else []
    except Exception:
        return []


@st.cache_data(ttl=300)
def get_option_chain(sym: str, expiry: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (calls_df, puts_df). Raises on failure.
    Guarantees numeric 'strike' and 'openInterest' columns in both frames.
    """
    tk = yf.Ticker(sym)
    oc = tk.option_chain(expiry)
    calls = oc.calls.copy().reset_index(drop=True)
    puts  = oc.puts.copy().reset_index(drop=True)

    for df in (calls, puts):
        df["strike"] = pd.to_numeric(df["strike"], errors="coerce")
        if "openInterest" not in df.columns:
            df["openInterest"] = 0.0
        df["openInterest"] = pd.to_numeric(df["openInterest"], errors="coerce").fillna(0)
        if "impliedVolatility" not in df.columns:
            df["impliedVolatility"] = np.nan

    calls = calls.dropna(subset=["strike"]).reset_index(drop=True)
    puts  = puts.dropna(subset=["strike"]).reset_index(drop=True)
    return calls, puts


def calc_max_pain(calls: pd.DataFrame, puts: pd.DataFrame) -> Optional[float]:
    """
    Vectorised Max Pain:
    For each candidate strike K, compute writer loss =
      sum_c(OI_c * max(0, S_c - K))  +  sum_p(OI_p * max(0, K - S_p))
    Return K that minimises total loss.
    """
    c_strikes = calls["strike"].values.astype(float)
    c_oi      = calls["openInterest"].values.astype(float)
    p_strikes = puts["strike"].values.astype(float)
    p_oi      = puts["openInterest"].values.astype(float)

    candidates = sorted(set(c_strikes.tolist()) | set(p_strikes.tolist()))
    if not candidates:
        return None

    min_pain        = float("inf")
    max_pain_strike = None
    for K in candidates:
        total = (
            float(np.sum(c_oi * np.maximum(0.0, c_strikes - K))) +
            float(np.sum(p_oi * np.maximum(0.0, K - p_strikes)))
        )
        if total < min_pain:
            min_pain        = total
            max_pain_strike = K
    return max_pain_strike


def build_oi_df(
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    spot: Optional[float],
) -> pd.DataFrame:
    """
    Outer-merge calls & puts on Strike so row counts always match.
    Optionally filter to ±15% of spot.
    """
    c = calls[["strike", "openInterest"]].rename(
        columns={"strike": "Strike", "openInterest": "Call OI"})
    c["Call OI"] = c["Call OI"].astype(float)

    p = puts[["strike", "openInterest"]].rename(
        columns={"strike": "Strike", "openInterest": "Put OI"})
    p["Put OI"] = p["Put OI"].astype(float)

    merged = (
        pd.merge(c, p, on="Strike", how="outer")
        .fillna(0)
        .sort_values("Strike")
        .reset_index(drop=True)
    )
    if spot and spot > 0:
        merged = merged[
            (merged["Strike"] >= spot * 0.85) &
            (merged["Strike"] <= spot * 1.15)
        ].reset_index(drop=True)
    return merged


def clean_display(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """Select available columns, scale IV to %, rename nicely."""
    present = [c for c in cols if c in df.columns]
    out = df[present].copy().reset_index(drop=True)
    if "impliedVolatility" in out.columns:
        out["impliedVolatility"] = (out["impliedVolatility"] * 100).round(2)
    # Human-readable column names
    rename_map = {
        "strike":            "Strike (₹)",
        "lastPrice":         "Last Price",
        "bid":               "Bid",
        "ask":               "Ask",
        "volume":            "Volume",
        "openInterest":      "Open Interest",
        "impliedVolatility": "IV (%)",
    }
    out.rename(columns=rename_map, inplace=True)
    return out


# ================================================================== UI
st.title("📈 Options Chain & PCR")
st.markdown("""
Live **options chain** with OI heatmap, **Put-Call Ratio**, **Max Pain**,
and **IV Smile** — key institutional positioning signals.
> ℹ️ Data via Yahoo Finance — **individual NSE stocks only**.
> Nifty / BankNifty index options are not available through Yahoo Finance.
""")

col1, col2 = st.columns(2)
with col1:
    sel_name = st.selectbox("🏢 Underlying", NIFTY50_NAMES)
with col2:
    sym      = NAME_TO_SYM.get(sel_name, "RELIANCE.NS")
    expiries = get_expiries(sym)
    if not expiries:
        st.error(
            f"❌ No options data for **{sel_name}** (`{sym}`) on Yahoo Finance. "
            "Try Reliance, HDFC Bank, TCS, or Infosys."
        )
        st.stop()
    expiry = st.selectbox("📅 Expiry", expiries)

# Spot price
spot = get_spot(sym)
if spot:
    st.metric("📌 Spot Price", f"₹{spot:,.2f}")
else:
    st.warning("⚠️ Live spot unavailable — charts will show full chain.")

# Fetch chain
with st.spinner(f"Fetching options chain for {sel_name} — {expiry}…"):
    try:
        calls, puts = get_option_chain(sym, expiry)
    except Exception as fetch_err:
        st.error(f"❌ Could not fetch options chain: {fetch_err}")
        st.stop()

if calls.empty and puts.empty:
    st.warning("⚠️ Options chain is empty. Market may be closed or data unavailable.")
    st.stop()

# ------------------------------------------------------------------ PCR
total_call_oi = safe_float(calls["openInterest"].sum())
total_put_oi  = safe_float(puts["openInterest"].sum())
pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 0.0

if   pcr < 0.7: pcr_label = "🔴 Bearish (PCR < 0.7)"
elif pcr > 1.3: pcr_label = "🟢 Bullish (PCR > 1.3)"
else:           pcr_label = "🟡 Neutral (0.7–1.3)"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Call OI", f"{int(total_call_oi):,}")
c2.metric("Total Put OI",  f"{int(total_put_oi):,}")
c3.metric("PCR",           f"{pcr:.3f}")
c4.metric("Signal",        pcr_label)

# ------------------------------------------------------------------ Max Pain
max_pain = None
try:
    max_pain = calc_max_pain(calls, puts)
    if max_pain is not None:
        dist_str = ""
        if spot and spot > 0:
            pct      = (max_pain - spot) / spot * 100
            dist_str = f" • {pct:+.1f}% from spot"
        st.info(
            f"🕹️ **Max Pain: ₹{max_pain:,.0f}**{dist_str} — "
            "strike where option writers lose the least at expiry"
        )
except Exception as mp_err:
    st.warning(f"⚠️ Max Pain failed: {mp_err}")

st.markdown("---")

# ------------------------------------------------------------------ OI Heatmap
st.subheader("📊 Open Interest Heatmap")
try:
    oi_df = build_oi_df(calls, puts, spot)
    if oi_df.empty:
        st.info("ℹ️ No strikes within ±15% of spot — showing full chain.")
        oi_df = build_oi_df(calls, puts, None)

    if not oi_df.empty:
        fig_oi = go.Figure()
        fig_oi.add_trace(go.Bar(
            x=oi_df["Strike"], y=oi_df["Call OI"],
            name="Call OI", marker_color="#00c853",
        ))
        fig_oi.add_trace(go.Bar(
            x=oi_df["Strike"], y=-oi_df["Put OI"],
            name="Put OI",  marker_color="#ff1744",
        ))
        if spot:
            fig_oi.add_vline(
                x=spot, line_dash="dash", line_color="#ffd600",
                annotation_text=f"Spot ₹{spot:,.0f}",
                annotation_position="top right",
            )
        if max_pain:
            fig_oi.add_vline(
                x=max_pain, line_dash="dot", line_color="#ea80fc",
                annotation_text=f"Max Pain ₹{max_pain:,.0f}",
                annotation_position="top left",
            )
        fig_oi.update_layout(
            title=f"{sel_name} — Call vs Put OI ({expiry})",
            template="plotly_dark",
            barmode="relative",
            height=480,
            xaxis_title="Strike Price (₹)",
            yaxis_title="Open Interest (Call ↑ / Put ↓)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            bargap=0.1,
        )
        st.plotly_chart(fig_oi, use_container_width=True)
except Exception as oi_err:
    st.warning(f"⚠️ OI Heatmap error: {oi_err}")

# ------------------------------------------------------------------ IV Smile
st.subheader("📉 Implied Volatility Smile")
try:
    if "impliedVolatility" in calls.columns and "impliedVolatility" in puts.columns:
        iv_c = calls[["strike", "impliedVolatility"]].rename(
            columns={"strike": "Strike", "impliedVolatility": "Call IV"})
        iv_p = puts[["strike",  "impliedVolatility"]].rename(
            columns={"strike": "Strike", "impliedVolatility": "Put IV"})
        iv_df = (
            pd.merge(iv_c, iv_p, on="Strike", how="outer")
            .sort_values("Strike")
            .reset_index(drop=True)
        )
        iv_df["Call IV"] = (iv_df["Call IV"].fillna(0) * 100).round(2)
        iv_df["Put IV"]  = (iv_df["Put IV"].fillna(0)  * 100).round(2)

        if spot and spot > 0:
            iv_df = iv_df[
                (iv_df["Strike"] >= spot * 0.85) &
                (iv_df["Strike"] <= spot * 1.15)
            ].reset_index(drop=True)

        if not iv_df.empty:
            fig_iv = go.Figure()
            fig_iv.add_trace(go.Scatter(
                x=iv_df["Strike"], y=iv_df["Call IV"],
                mode="lines+markers", name="Call IV %",
                line=dict(color="#00c853", width=2),
            ))
            fig_iv.add_trace(go.Scatter(
                x=iv_df["Strike"], y=iv_df["Put IV"],
                mode="lines+markers", name="Put IV %",
                line=dict(color="#ff1744", width=2),
            ))
            if spot:
                fig_iv.add_vline(
                    x=spot, line_dash="dash", line_color="#ffd600",
                    annotation_text="Spot",
                )
            fig_iv.update_layout(
                title=f"{sel_name} — IV Smile ({expiry})",
                template="plotly_dark", height=360,
                xaxis_title="Strike (₹)",
                yaxis_title="Implied Volatility (%)",
            )
            st.plotly_chart(fig_iv, use_container_width=True)
        else:
            st.info("ℹ️ No IV data in range.")
    else:
        st.info("ℹ️ Implied volatility data not available for this symbol.")
except Exception as iv_err:
    st.warning(f"⚠️ IV Smile error: {iv_err}")

# ------------------------------------------------------------------ Raw tables
st.subheader("📊 Raw Chain Data")
DISP_COLS = ["strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]
tab1, tab2 = st.tabs(["🟢 Calls", "🔴 Puts"])
with tab1:
    st.dataframe(clean_display(calls, DISP_COLS), use_container_width=True, hide_index=True)
with tab2:
    st.dataframe(clean_display(puts,  DISP_COLS), use_container_width=True, hide_index=True)
