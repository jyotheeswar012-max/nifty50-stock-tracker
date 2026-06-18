"""
pages/8_ML_Signals.py – ML-Based Buy / Sell Signal Scanner

Uses technical indicator features (RSI, MACD, Bollinger, EMA-cross)
fed into a RandomForest + GradientBoosting ensemble to classify each
stock as BUY / HOLD / SELL for the next trading session.

NOTE: Educational / research purposes only. Not investment advice.
"""
import os
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="ML Signals", page_icon="📶", layout="wide")

from utils.theme import inject, inject_topbar
inject()

try:
    from utils.supabase_auth import get_current_user, logout, is_guest, login_nudge
except Exception:
    def get_current_user(): return None
    def logout(): pass
    def is_guest(): return True
    def login_nudge(f=""): st.info("💡 Sign in to save your data.")

user = get_current_user()
inject_topbar(user=user)

# ---------------------------------------------------------------------------
# Ephemeral filesystem warning (Streamlit Cloud)
# ---------------------------------------------------------------------------
if os.environ.get("STREAMLIT_SHARING_MODE") or os.environ.get("IS_STREAMLIT_CLOUD"):
    st.warning(
        "⚠️ **Streamlit Cloud Notice:** The filesystem is ephemeral — "
        "any cached model files stored to disk **will be erased on every redeploy**. "
        "Models retrain automatically on each session, so no data is permanently lost.",
        icon="⚠️",
    )

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    SK_OK = True
except ImportError:
    SK_OK = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NIFTY50 = [
    {"symbol": "RELIANCE.NS",  "name": "Reliance Industries"},
    {"symbol": "HDFCBANK.NS",  "name": "HDFC Bank"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank"},
    {"symbol": "INFY.NS",      "name": "Infosys"},
    {"symbol": "TCS.NS",       "name": "TCS"},
    {"symbol": "BHARTIARTL.NS","name": "Bharti Airtel"},
    {"symbol": "ITC.NS",       "name": "ITC"},
    {"symbol": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank"},
    {"symbol": "LT.NS",        "name": "Larsen & Toubro"},
    {"symbol": "HCLTECH.NS",   "name": "HCL Technologies"},
    {"symbol": "AXISBANK.NS",  "name": "Axis Bank"},
    {"symbol": "SBIN.NS",      "name": "State Bank of India"},
    {"symbol": "BAJFINANCE.NS","name": "Bajaj Finance"},
    {"symbol": "WIPRO.NS",     "name": "Wipro"},
    {"symbol": "ASIANPAINT.NS","name": "Asian Paints"},
    {"symbol": "MARUTI.NS",    "name": "Maruti Suzuki"},
    {"symbol": "SUNPHARMA.NS", "name": "Sun Pharmaceutical"},
    {"symbol": "TITAN.NS",     "name": "Titan Company"},
    {"symbol": "ULTRACEMCO.NS","name": "UltraTech Cement"},
    {"symbol": "ONGC.NS",      "name": "ONGC"},
    {"symbol": "NTPC.NS",      "name": "NTPC"},
    {"symbol": "POWERGRID.NS", "name": "Power Grid Corp"},
    {"symbol": "M&M.NS",       "name": "Mahindra & Mahindra"},
    {"symbol": "TATAMOTORS.NS","name": "Tata Motors"},
    {"symbol": "TATASTEEL.NS", "name": "Tata Steel"},
    {"symbol": "JSWSTEEL.NS",  "name": "JSW Steel"},
    {"symbol": "HINDALCO.NS",  "name": "Hindalco Industries"},
    {"symbol": "ADANIENT.NS",  "name": "Adani Enterprises"},
    {"symbol": "ADANIPORTS.NS","name": "Adani Ports"},
    {"symbol": "BAJAJFINSV.NS","name": "Bajaj Finserv"},
    {"symbol": "BAJAJAUTO.NS", "name": "Bajaj Auto"},
    {"symbol": "HEROMOTOCO.NS","name": "Hero MotoCorp"},
    {"symbol": "CIPLA.NS",     "name": "Cipla"},
    {"symbol": "DRREDDY.NS",   "name": "Dr. Reddy's Labs"},
    {"symbol": "DIVISLAB.NS",  "name": "Divi's Laboratories"},
    {"symbol": "EICHERMOT.NS", "name": "Eicher Motors"},
    {"symbol": "GRASIM.NS",    "name": "Grasim Industries"},
    {"symbol": "HDFCLIFE.NS",  "name": "HDFC Life Insurance"},
    {"symbol": "SBILIFE.NS",   "name": "SBI Life Insurance"},
    {"symbol": "INDUSINDBK.NS","name": "IndusInd Bank"},
    {"symbol": "TATACONSUM.NS","name": "Tata Consumer Products"},
    {"symbol": "BRITANNIA.NS", "name": "Britannia Industries"},
    {"symbol": "NESTLEIND.NS", "name": "Nestle India"},
    {"symbol": "HINDUNILVR.NS","name": "Hindustan Unilever"},
    {"symbol": "COALINDIA.NS", "name": "Coal India"},
    {"symbol": "BPCL.NS",      "name": "BPCL"},
    {"symbol": "TECHM.NS",     "name": "Tech Mahindra"},
    {"symbol": "LTF.NS",       "name": "L&T Finance"},
    {"symbol": "SHRIRAMFIN.NS","name": "Shriram Finance"},
    {"symbol": "BEL.NS",       "name": "Bharat Electronics"},
]

N2S   = {s["name"]: s["symbol"] for s in NIFTY50}
NAMES = [s["name"] for s in NIFTY50]

PLT_LAYOUT = dict(
    paper_bgcolor="#ffffff", plot_bgcolor="#fafafa",
    font=dict(color="#1e293b", family="Inter, sans-serif", size=12),
    title_font=dict(size=15, color="#0f172a", family="Inter, sans-serif"),
    margin=dict(l=16, r=16, t=48, b=16),
    legend=dict(font=dict(color="#1e293b", size=12), bgcolor="rgba(255,255,255,0.85)",
                bordercolor="#e2e8f0", borderwidth=1, orientation="h", yanchor="bottom", y=1.02),
)
AXIS_STYLE = dict(
    tickfont=dict(color="#1e293b", size=11, family="Inter, sans-serif"),
    title_font=dict(color="#0f172a", size=12, family="Inter, sans-serif"),
    linecolor="#cbd5e1", gridcolor="#f1f5f9", zerolinecolor="#cbd5e1",
)

def style_fig(fig):
    fig.update_xaxes(**AXIS_STYLE)
    fig.update_yaxes(**AXIS_STYLE)
    return fig

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
.signal-buy  { background:#dcfce7;color:#166534;font-weight:700;padding:.25rem .7rem;border-radius:6px;font-size:.85rem; }
.signal-sell { background:#fee2e2;color:#991b1b;font-weight:700;padding:.25rem .7rem;border-radius:6px;font-size:.85rem; }
.signal-hold { background:#fef9c3;color:#854d0e;font-weight:700;padding:.25rem .7rem;border-radius:6px;font-size:.85rem; }
.risk-banner {
    background:linear-gradient(135deg,#7f1d1d 0%,#991b1b 60%,#b91c1c 100%);
    border:2px solid #fca5a5;border-radius:12px;padding:1rem 1.4rem;margin-bottom:1rem;
    display:flex;align-items:flex-start;gap:1rem;
}
.risk-banner-title { color:#fff!important;font-size:.95rem!important;font-weight:800!important;text-transform:uppercase;margin-bottom:.25rem; }
.risk-banner-body  { color:#fecaca!important;font-size:.83rem!important;line-height:1.6; }
.risk-banner-body b { color:#fff!important; }
.risk-footer { background:#1e1b4b;border:1.5px solid #4338ca;border-radius:10px;padding:.85rem 1.3rem;margin-top:2rem;display:flex;align-items:flex-start;gap:.75rem; }
.risk-footer-text { color:#c7d2fe!important;font-size:.78rem!important;line-height:1.65; }
.risk-footer-text b { color:#e0e7ff!important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown("""
<div style='background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 50%,#0c4a6e 100%);
     border-radius:14px;padding:1.4rem 1.8rem;margin-bottom:1rem;
     display:flex;align-items:center;gap:1.2rem;'>
  <div style='font-size:2.6rem;'>📶</div>
  <div>
    <div style='color:#fff;font-size:1.35rem;font-weight:700;'>ML Signals Scanner</div>
    <div style='color:#7dd3fc;font-size:.85rem;margin-top:.3rem;'>
      RSI · MACD · Bollinger Bands · EMA Cross → RandomForest + GradientBoosting ensemble signals
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Risk banner
st.markdown("""
<div class="risk-banner">
  <div style='font-size:2rem;flex-shrink:0;margin-top:2px;'>⚠️</div>
  <div>
    <div class="risk-banner-title">⛔ Educational Only — Not Investment Advice</div>
    <div class="risk-banner-body">
      <b>ML signals are generated from historical patterns and do not guarantee future results.</b>
      A BUY signal does not mean the stock will rise. A SELL signal does not mean it will fall.
      Never trade based solely on these outputs. <b>Always consult a SEBI-registered advisor.</b>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

if not SK_OK:
    st.error("❌ `scikit-learn` not installed. Add it to requirements.txt and redeploy.")
    st.stop()

# ---------------------------------------------------------------------------
# Helper: feature engineering
# ---------------------------------------------------------------------------
def _s(col):
    """Squeeze 2-D DataFrame column to 1-D Series."""
    if isinstance(col, pd.DataFrame):
        col = col.iloc[:, 0]
    return col

@st.cache_data(ttl=300)
def fetch_hist(sym: str, period: str = "1y") -> pd.DataFrame:
    try:
        ticker_sym = sym.replace("&", "%26") if "&" in sym else sym
        df = yf.Ticker(ticker_sym).history(period=period, auto_adjust=True)
        if df is None or df.empty:
            df = yf.Ticker(sym).history(period=period, auto_adjust=True)
        if df is not None and not df.empty:
            df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        return df
    except Exception:
        return pd.DataFrame()


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    c = _s(df["Close"]).astype(float)
    v = _s(df["Volume"]).astype(float) if "Volume" in df.columns else pd.Series(np.ones(len(c)), index=c.index)

    feat = pd.DataFrame(index=c.index)
    feat["close"] = c
    feat["ret1"]  = c.pct_change(1)
    feat["ret5"]  = c.pct_change(5)
    feat["ret10"] = c.pct_change(10)

    delta = c.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    feat["rsi"] = 100 - 100 / (1 + rs)

    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    macd_line   = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    feat["macd"]      = macd_line
    feat["macd_hist"] = macd_line - signal_line

    ma20  = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    feat["bb_pos"] = (c - ma20) / std20.replace(0, np.nan)

    ema9  = c.ewm(span=9,  adjust=False).mean()
    ema21 = c.ewm(span=21, adjust=False).mean()
    feat["ema_cross"] = ema9 - ema21
    feat["vol_zscore"] = (v - v.rolling(20).mean()) / v.rolling(20).std().replace(0, np.nan)

    feat.dropna(inplace=True)
    return feat


def make_labels(feat: pd.DataFrame, threshold: float = 0.015) -> pd.Series:
    fwd = feat["close"].pct_change(5).shift(-5)
    labels = pd.Series(0, index=feat.index)
    labels[fwd >  threshold] =  1
    labels[fwd < -threshold] = -1
    return labels.dropna()


def train_and_signal(feat: pd.DataFrame):
    labels = make_labels(feat)
    common = feat.index.intersection(labels.index)
    feat   = feat.loc[common]
    labels = labels.loc[common]

    if len(feat) < 60:
        return "HOLD", 0.33, pd.Series(dtype=float), pd.Series(dtype=float)

    FEATURE_COLS = ["ret1","ret5","ret10","rsi","macd","macd_hist","bb_pos","ema_cross","vol_zscore"]
    X = feat[FEATURE_COLS].values
    y = labels.values

    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X)

    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, random_state=42)
    rf.fit(X_sc, y)
    gb.fit(X_sc, y)

    last_X = X_sc[-1:]
    rf_proba = rf.predict_proba(last_X)[0]
    gb_proba = gb.predict_proba(last_X)[0]
    classes  = list(rf.classes_)

    avg_proba  = (rf_proba + gb_proba) / 2
    pred_class = classes[int(np.argmax(avg_proba))]
    confidence = float(np.max(avg_proba))

    signal_map = {1: "BUY", -1: "SELL", 0: "HOLD"}
    signal = signal_map.get(pred_class, "HOLD")

    rf_hist = pd.Series(rf.predict(X_sc), index=feat.index)
    gb_hist = pd.Series(gb.predict(X_sc), index=feat.index)
    hist_signal = pd.Series(
        [signal_map.get(int(round((a + b) / 2)), "HOLD")
         for a, b in zip(rf_hist, gb_hist)],
        index=feat.index
    )

    return signal, confidence, hist_signal, feat["close"]


# ---------------------------------------------------------------------------
# UI Controls
# ---------------------------------------------------------------------------
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    sel_name   = st.selectbox("🏢 Focus Stock", NAMES, key="sig_stock")
with col2:
    scan_mode  = st.checkbox("🔍 Scan all 50 stocks", value=False, key="sig_scan")
with col3:
    period_opt = st.selectbox("📅 History", ["6mo", "1y", "2y"], index=1, key="sig_period")

# ---------------------------------------------------------------------------
# Single-stock deep-dive
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader(f"📊 Signal Analysis — {sel_name}")

with st.spinner(f"Training models for {sel_name}..."):
    sym  = N2S[sel_name]
    hist = fetch_hist(sym, period_opt)

if hist.empty or len(hist) < 60:
    st.warning("⚠️ Not enough data. Try a longer history period.")
else:
    feat = compute_features(hist)
    signal, conf, hist_sigs, hist_close = train_and_signal(feat)

    sig_color = {"BUY": "#16a34a", "SELL": "#dc2626", "HOLD": "#d97706"}
    sig_bg    = {"BUY": "#dcfce7",  "SELL": "#fee2e2",  "HOLD": "#fef9c3"}

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Signal", signal)
    k2.metric("Ensemble Confidence", f"{conf:.1%}")
    k3.metric("Current Price", f"₹{float(_s(hist['Close']).iloc[-1]):,.2f}")
    k4.metric("Data Points", len(feat))

    css_class = f"signal-{signal.lower()}"
    st.markdown(
        f"<p>Latest ML signal: <span class='{css_class}'>{signal}</span> "
        f"with <b>{conf:.1%}</b> ensemble confidence.</p>",
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["📈 Price + Signal History", "📊 Feature Heatmap"])

    with tab1:
        if len(hist_sigs) > 0:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hist_close.index, y=hist_close.values,
                mode="lines", name="Price",
                line=dict(color="#1e293b", width=1.8)
            ))
            buy_idx  = hist_sigs[hist_sigs == "BUY"].index
            sell_idx = hist_sigs[hist_sigs == "SELL"].index
            if len(buy_idx):
                fig.add_trace(go.Scatter(
                    x=buy_idx, y=hist_close.reindex(buy_idx),
                    mode="markers", name="BUY signal",
                    marker=dict(symbol="triangle-up", color="#16a34a", size=9)
                ))
            if len(sell_idx):
                fig.add_trace(go.Scatter(
                    x=sell_idx, y=hist_close.reindex(sell_idx),
                    mode="markers", name="SELL signal",
                    marker=dict(symbol="triangle-down", color="#dc2626", size=9)
                ))
            fig.update_layout(**PLT_LAYOUT,
                title=f"{sel_name} — Historical ML Signals (in-sample)",
                height=460, xaxis_title="Date", yaxis_title="Price (₹)")
            style_fig(fig)
            fig.update_layout(autosize=True)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("⚠️ Signals shown are in-sample (trained on same data). Do not use to infer historical profitability.")
        else:
            st.info("Not enough data to plot signal history.")

    with tab2:
        FEATURE_COLS = ["ret1","ret5","ret10","rsi","macd","macd_hist","bb_pos","ema_cross","vol_zscore"]
        last30 = feat[FEATURE_COLS].tail(30)
        fig_hm = px.imshow(
            last30.T.values,
            x=[d.strftime("%d %b") for d in last30.index],
            y=FEATURE_COLS,
            color_continuous_scale="RdYlGn",
            title="Feature Values (last 30 days, normalised per row)",
            aspect="auto",
        )
        fig_hm.update_layout(**PLT_LAYOUT, height=380)
        fig_hm.update_layout(autosize=True)
        st.plotly_chart(fig_hm, use_container_width=True)

# ---------------------------------------------------------------------------
# Full Nifty 50 scan
# ---------------------------------------------------------------------------
if scan_mode:
    st.markdown("---")
    st.subheader("🔍 Nifty 50 Signal Scan")
    st.caption("Trains a fresh model for every stock. May take 60-90 seconds.")

    prog  = st.progress(0, text="Starting scan...")
    rows  = []
    total = len(NIFTY50)

    for i, entry in enumerate(NIFTY50):
        prog.progress((i + 1) / total, text=f"Scanning {entry['name']} ({i+1}/{total})...")
        try:
            h = fetch_hist(entry["symbol"], period_opt)
            if h.empty or len(h) < 60:
                rows.append({"Company": entry["name"], "Signal": "N/A", "Confidence": 0.0, "Error": "Insufficient data"})
                continue
            f  = compute_features(h)
            sig, conf, _, _ = train_and_signal(f)
            rows.append({"Company": entry["name"], "Signal": sig, "Confidence": round(conf, 4), "Error": ""})
        except Exception as e:
            rows.append({"Company": entry["name"], "Signal": "N/A", "Confidence": 0.0, "Error": str(e)[:60]})

    prog.empty()
    scan_df = pd.DataFrame(rows)

    buys  = len(scan_df[scan_df["Signal"] == "BUY"])
    sells = len(scan_df[scan_df["Signal"] == "SELL"])
    holds = len(scan_df[scan_df["Signal"] == "HOLD"])
    s1, s2, s3 = st.columns(3)
    s1.metric("🟢 BUY signals",  buys)
    s2.metric("🔴 SELL signals", sells)
    s3.metric("🟡 HOLD signals", holds)

    def badge(row):
        s = row["Signal"]
        c = {"BUY": "signal-buy", "SELL": "signal-sell", "HOLD": "signal-hold"}.get(s, "")
        return f"<span class='{c}'>{s}</span>"

    scan_df["Signal Badge"] = scan_df.apply(badge, axis=1)
    display_cols = ["Company", "Signal", "Confidence"]
    st.dataframe(
        scan_df[display_cols].style.background_gradient(subset=["Confidence"], cmap="RdYlGn"),
        use_container_width=True, hide_index=True
    )

    valid_df = scan_df[scan_df["Signal"] != "N/A"].sort_values("Confidence", ascending=True)
    color_map = {"BUY": "#16a34a", "SELL": "#dc2626", "HOLD": "#d97706"}
    bar_colors = [color_map.get(s, "#94a3b8") for s in valid_df["Signal"]]

    fig_bar = go.Figure(go.Bar(
        x=valid_df["Confidence"],
        y=valid_df["Company"],
        orientation="h",
        marker_color=bar_colors,
        text=[f"{c:.1%}" for c in valid_df["Confidence"]],
        textposition="outside",
    ))
    fig_bar.update_layout(
        **PLT_LAYOUT,
        title="Ensemble Confidence by Stock (🟢 BUY · 🔴 SELL · 🟡 HOLD)",
        height=max(500, len(valid_df) * 22),
        xaxis_title="Confidence",
        xaxis_tickformat=".0%",
        yaxis_title="",
        showlegend=False,
    )
    style_fig(fig_bar)
    fig_bar.update_layout(autosize=True)
    st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------------------------------
# Footer disclaimer
# ---------------------------------------------------------------------------
st.markdown("""
<div class="risk-footer">
  <div style='font-size:1.2rem;flex-shrink:0;'>⚖️</div>
  <div class="risk-footer-text">
    <b>Legal Disclaimer:</b> All ML signals on this page are generated from historical price data
    using machine learning classifiers. They are <b>for educational and research purposes only</b>
    and do not constitute financial advice, investment recommendations, or an offer to buy or sell
    any securities. ML models trained on historical data can and do fail in live markets.
    Past signal accuracy is not indicative of future performance.
    <b>Always consult a SEBI-registered financial advisor before making investment decisions.</b>
  </div>
</div>
""", unsafe_allow_html=True)
