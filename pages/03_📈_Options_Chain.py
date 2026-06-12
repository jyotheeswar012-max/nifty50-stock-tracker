"""
Page: Options Chain & Put-Call Ratio
Fetches live NSE options data via yfinance .option_chain()
Displays OI heatmap, PCR, max-pain level.

Fixes applied:
  1. Proper puts variable extraction (not reusing puts_or_err alias).
  2. Correct O(n^2) Max Pain formula — for each candidate expiry price K,
     sum (OI * intrinsic loss) across all strikes for both calls and puts.
  3. OI heatmap uses an explicit left-merge on strike so calls/puts row counts
     never mismatch.
  4. ^NSEI has no Yahoo Finance options — show a clear warning and suggest
     NIFTY derivatives instead.
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Options Chain", page_icon="📈", layout="wide")

# ---- Symbol map (index removed — Yahoo has no ^NSEI options) ----
NIFTY50_NAMES = [
    "Reliance Industries", "HDFC Bank", "ICICI Bank", "Infosys", "TCS",
    "Bharti Airtel", "ITC", "Kotak Mahindra Bank", "Larsen & Toubro",
    "HCL Technologies", "Axis Bank", "State Bank of India", "Bajaj Finance",
    "Wipro", "Asian Paints", "Maruti Suzuki", "Sun Pharmaceutical",
    "Titan Company", "UltraTech Cement", "ONGC", "NTPC", "Tata Motors",
    "Tata Steel", "Adani Enterprises", "Adani Ports", "Bajaj Auto",
    "Cipla", "Dr. Reddy's Labs", "Hindustan Unilever", "Bajaj Finance",
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
# Deduplicate names list
NIFTY50_NAMES = list(dict.fromkeys(NIFTY50_NAMES))

# ------------------------------------------------------------------ helpers
def safe_float(val, default: float = 0.0) -> float:
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default


@st.cache_data(ttl=60)
def get_spot(sym: str):
    try:
        h = yf.Ticker(sym).history(period="1d", interval="1m")
        return safe_float(h["Close"].iloc[-1]) if (h is not None and not h.empty) else None
    except Exception:
        return None


@st.cache_data(ttl=300)
def get_expiries(sym: str) -> list:
    try:
        opts = yf.Ticker(sym).options
        return list(opts) if opts else []
    except Exception:
        return []


@st.cache_data(ttl=300)
def get_option_chain(sym: str, expiry: str):
    """
    Returns (calls_df, puts_df) or raises.
    Both DataFrames are guaranteed to have a clean 'strike' column.
    """
    tk = yf.Ticker(sym)
    oc = tk.option_chain(expiry)          # raises if unavailable
    calls = oc.calls.copy().reset_index(drop=True)
    puts  = oc.puts.copy().reset_index(drop=True)
    # Ensure numeric strikes
    calls["strike"] = pd.to_numeric(calls["strike"], errors="coerce")
    puts["strike"]  = pd.to_numeric(puts["strike"],  errors="coerce")
    calls = calls.dropna(subset=["strike"])
    puts  = puts.dropna(subset=["strike"])
    return calls, puts


def calc_max_pain(calls: pd.DataFrame, puts: pd.DataFrame) -> float | None:
    """
    Correct Max Pain algorithm:
    For every candidate expiry price K (= each unique strike),
    compute total loss to option writers:
      call_loss(K) = sum over all call strikes S: OI(S) * max(0, S - K)
      put_loss(K)  = sum over all put  strikes S: OI(S) * max(0, K - S)
    Max pain = K that minimises total_loss(K).
    """
    c_strikes = calls["strike"].values
    c_oi      = calls["openInterest"].fillna(0).values.astype(float)
    p_strikes = puts["strike"].values
    p_oi      = puts["openInterest"].fillna(0).values.astype(float)

    candidates = sorted(set(c_strikes) | set(p_strikes))
    if not candidates:
        return None

    min_pain = float("inf")
    max_pain_strike = None
    for K in candidates:
        call_loss = float(np.sum(c_oi * np.maximum(0, c_strikes - K)))
        put_loss  = float(np.sum(p_oi * np.maximum(0, K - p_strikes)))
        total     = call_loss + put_loss
        if total < min_pain:
            min_pain         = total
            max_pain_strike  = K
    return max_pain_strike


def build_oi_df(calls: pd.DataFrame, puts: pd.DataFrame,
                spot: float | None) -> pd.DataFrame:
    """
    Merge calls & puts on strike using an OUTER join so row counts
    always match regardless of yfinance returning different strike sets.
    Filter to ±15 % of spot if available.
    """
    c = calls[["strike", "openInterest"]].copy()
    c.columns = ["Strike", "Call OI"]
    c["Call OI"] = c["Call OI"].fillna(0).astype(float)

    p = puts[["strike", "openInterest"]].copy()
    p.columns = ["Strike", "Put OI"]
    p["Put OI"] = p["Put OI"].fillna(0).astype(float)

    merged = pd.merge(c, p, on="Strike", how="outer").fillna(0)
    merged = merged.sort_values("Strike").reset_index(drop=True)

    if spot and spot > 0:
        merged = merged[
            (merged["Strike"] >= spot * 0.85) &
            (merged["Strike"] <= spot * 1.15)
        ].copy()
    return merged


# ================================================================== UI
st.title("📈 Options Chain & PCR")
st.markdown("""
Live **options chain** with Open Interest heatmap, **Put-Call Ratio (PCR)**,
and **Max Pain** level — key institutional positioning signals.
> ℹ️ Data via Yahoo Finance. Individual NSE stocks only — index options
> (Nifty/BankNifty) are **not available** through Yahoo Finance.
""")

col1, col2 = st.columns(2)
with col1:
    sel_name = st.selectbox("🏢 Underlying", NIFTY50_NAMES)
with col2:
    sym      = NAME_TO_SYM.get(sel_name, "RELIANCE.NS")
    expiries = get_expiries(sym)
    if not expiries:
        st.error(
            f"❌ No options data found for **{sel_name}** (`{sym}`) on Yahoo Finance.\n\n"
            "This usually means the stock has no listed F&O contracts, "
            "or Yahoo Finance is temporarily unavailable. Try a large-cap like "
            "Reliance, HDFC Bank, TCS, or Infosys."
        )
        st.stop()
    expiry = st.selectbox("📅 Expiry", expiries)

# Spot price
spot = get_spot(sym)
if spot:
    st.metric("📌 Spot Price", f"₹{spot:,.2f}")
else:
    st.warning("⚠️ Could not fetch live spot price — Max Pain filter will use full chain.")

# Fetch chain
with st.spinner(f"Fetching options chain for {sel_name} — {expiry} ..."):
    try:
        calls, puts = get_option_chain(sym, expiry)
    except Exception as e:
        st.error(f"❌ Failed to fetch options chain: {e}")
        st.stop()

if calls.empty and puts.empty:
    st.warning("⚠️ Options chain returned empty. Market may be closed or data unavailable.")
    st.stop()

# ------------------------------------------------------------------ PCR
total_call_oi = safe_float(calls["openInterest"].sum())
total_put_oi  = safe_float(puts["openInterest"].sum())
pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 0.0

if   pcr < 0.7: pcr_label, pcr_color = "🔴 Bearish — more calls than puts (PCR < 0.7)",  "#ff1744"
elif pcr > 1.3: pcr_label, pcr_color = "🟢 Bullish — heavy put buying (PCR > 1.3)",       "#00c853"
else:           pcr_label, pcr_color = "🟡 Neutral (PCR 0.7–1.3)",                          "#ffd600"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Call OI", f"{int(total_call_oi):,}")
c2.metric("Total Put OI",  f"{int(total_put_oi):,}")
c3.metric("PCR",           f"{pcr}")
c4.metric("Signal",        pcr_label)

# ------------------------------------------------------------------ Max Pain
max_pain = None
try:
    max_pain = calc_max_pain(calls, puts)
    if max_pain is not None:
        dist = ""
        if spot and spot > 0:
            pct  = (max_pain - spot) / spot * 100
            dist = f" &nbsp;•&nbsp; {pct:+.1f}% from spot"
        st.info(
            f"🕹️ **Max Pain Strike: ₹{max_pain:,.0f}**{dist} — "
            "strike where option writers lose the least at expiry"
        )
except Exception as e:
    st.warning(f"⚠️ Max Pain calculation failed: {e}")

st.markdown("---")

# ------------------------------------------------------------------ OI Heatmap
st.subheader("📊 Open Interest Heatmap")
try:
    oi_df = build_oi_df(calls, puts, spot)
    if oi_df.empty:
        st.info("ℹ️ No strikes in ±15% spot range. Showing full chain.")
        oi_df = build_oi_df(calls, puts, None)

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
        title=f"{sel_name} — Call vs Put OI  ({expiry})",
        template="plotly_dark",
        barmode="relative",
        height=480,
        xaxis_title="Strike Price (₹)",
        yaxis_title="Open Interest (Call ↑ / Put ↓)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        bargap=0.1,
    )
    st.plotly_chart(fig_oi, use_container_width=True)
except Exception as e:
    st.warning(f"⚠️ OI Heatmap error: {e}")

# ------------------------------------------------------------------ IV Smile
st.subheader("📉 Implied Volatility Smile")
try:
    iv_c = calls[["strike", "impliedVolatility"]].copy()
    iv_p = puts[["strike",  "impliedVolatility"]].copy()
    iv_c.columns = ["Strike", "Call IV"]
    iv_p.columns = ["Strike", "Put IV"]
    iv_merged = pd.merge(iv_c, iv_p, on="Strike", how="outer").sort_values("Strike")
    iv_merged["Call IV"] = iv_merged["Call IV"].fillna(0) * 100
    iv_merged["Put IV"]  = iv_merged["Put IV"].fillna(0)  * 100
    if spot:
        iv_merged = iv_merged[
            (iv_merged["Strike"] >= spot * 0.85) &
            (iv_merged["Strike"] <= spot * 1.15)
        ]
    if not iv_merged.empty:
        fig_iv = go.Figure()
        fig_iv.add_trace(go.Scatter(
            x=iv_merged["Strike"], y=iv_merged["Call IV"],
            mode="lines+markers", name="Call IV %",
            line=dict(color="#00c853", width=2)))
        fig_iv.add_trace(go.Scatter(
            x=iv_merged["Strike"], y=iv_merged["Put IV"],
            mode="lines+markers", name="Put IV %",
            line=dict(color="#ff1744", width=2)))
        if spot:
            fig_iv.add_vline(x=spot, line_dash="dash", line_color="#ffd600",
                annotation_text="Spot")
        fig_iv.update_layout(
            title=f"{sel_name} — IV Smile ({expiry})",
            template="plotly_dark", height=360,
            xaxis_title="Strike (₹)", yaxis_title="Implied Volatility (%)",
        )
        st.plotly_chart(fig_iv, use_container_width=True)
except Exception as e:
    st.warning(f"⚠️ IV chart error: {e}")

# ------------------------------------------------------------------ Raw tables
st.subheader("📊 Raw Chain Data")
tab1, tab2 = st.tabs(["🟢 Calls", "🔴 Puts"])
COLS = ["strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]
with tab1:
    c_disp = calls[[col for col in COLS if col in calls.columns]].copy()
    c_disp["impliedVolatility"] = (c_disp["impliedVolatility"] * 100).round(2)
    c_disp = c_disp.sort_values("strike").reset_index(drop=True)
    c_disp.columns = [col.replace("implied", "IV ").replace("Interest", "").title()
                      for col in c_disp.columns]
    st.dataframe(c_disp, use_container_width=True, hide_index=True)
with tab2:
    p_disp = puts[[col for col in COLS if col in puts.columns]].copy()
    p_disp["impliedVolatility"] = (p_disp["impliedVolatility"] * 100).round(2)
    p_disp = p_disp.sort_values("strike").reset_index(drop=True)
    p_disp.columns = [col.replace("implied", "IV ").replace("Interest", "").title()
                      for col in p_disp.columns]
    st.dataframe(p_disp, use_container_width=True, use_container_width=True, hide_index=True)
