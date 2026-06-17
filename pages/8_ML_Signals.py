"""
pages/8_ML_Signals.py  –  ML Signals UI v2

Features:
  • Single-stock deep-dive: RF / GB / LR models
  • Walk-forward CV accuracy + ROC-AUC
  • Feature importance bar chart
  • Multi-horizon signals (1d / 3d / 5d)
  • Batch scan: generate UP/DOWN signals for all Nifty 50
  • Model cache awareness (shows age of cached model)
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from utils.ml_signals import train_model, get_signal, batch_signals
from utils.data import get_stock_history
from utils.constants import NIFTY50_SYMBOLS
from utils.auth_ui import require_login

require_login()

st.set_page_config(page_title="ML Signals", page_icon="🤖", layout="wide")
st.title("🤖 ML Price-Direction Signals")
st.caption(
    "Random Forest / Gradient Boosting models trained on 30+ technical features. "
    "Walk-forward cross-validation prevents look-ahead bias. For informational purposes only."
)

tab1, tab2 = st.tabs(["🔬 Single Stock", "📡 Batch Scan"])

# ── Tab 1: Single Stock ───────────────────────────────────────────────────────
with tab1:
    col_l, col_r = st.columns([1, 2])

    with col_l:
        symbol = st.selectbox("Symbol", NIFTY50_SYMBOLS, key="ml_sym")
        model_type = st.radio(
            "Model",
            options=["rf", "gb", "lr"],
            format_func={"rf": "Random Forest", "gb": "Gradient Boost", "lr": "Logistic Regression"}.get,
            horizontal=True,
        )
        horizon = st.select_slider(
            "Prediction Horizon",
            options=[1, 3, 5, 10],
            format_func=lambda x: f"{x}d",
        )
        period_map = {"6mo": "6 Months", "1y": "1 Year", "2y": "2 Years"}
        period = st.selectbox("Training Data", list(period_map.keys()),
                              format_func=period_map.get, index=1)
        force = st.checkbox("Force Retrain (ignore cache)")
        run = st.button("🚀 Train & Predict", type="primary", use_container_width=True)

    with col_r:
        if run:
            with st.spinner(f"Fetching {symbol}..."):
                df = get_stock_history(symbol, period=period)

            if df is None or len(df) < 120:
                st.error("Insufficient data (need ≥ 120 days). Try a longer period.")
                st.stop()

            with st.spinner("Training model with walk-forward CV..."):
                pipeline, metrics = train_model(
                    df, model_type=model_type, horizon=horizon, force_retrain=force
                )

            signal = get_signal(pipeline, df, horizon=horizon)

            # Signal card
            direction_emoji = "🟢" if signal["direction"] == "UP" else "🔴"
            stars = "★" * signal["signal_strength"] + "☆" * (5 - signal["signal_strength"])
            st.markdown(f"""<div style='background:#1E1E2E;padding:20px;border-radius:12px;text-align:center'>
                <h2 style='margin:0'>{direction_emoji} {signal['direction']}</h2>
                <p style='font-size:1.1em;margin:4px 0'>{stars}</p>
                <p style='color:#aaa;margin:0'>{signal['label']}</p>
                <p style='color:#aaa;font-size:0.85em'>Prob(UP): {signal['prob_up']:.1%} &nbsp;|&nbsp;
                   Confidence: {signal['confidence']:.1%}</p>
            </div>""", unsafe_allow_html=True)

            st.divider()

            # Metrics
            if not metrics.get("cached"):
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("CV Accuracy", f"{metrics['cv_accuracy']:.1f}%")
                m2.metric("CV AUC", f"{metrics['cv_auc']:.1f}%" if metrics.get('cv_auc') else "N/A")
                m3.metric("Training Samples", metrics["n_samples"])
                m4.metric("Features", metrics["n_features"])

                # Feature importance chart
                if not metrics["feature_importance"].empty:
                    fi = metrics["feature_importance"].head(15)
                    fig = px.bar(
                        fi, x="importance", y="feature", orientation="h",
                        title=f"Top 15 Feature Importances — {symbol}",
                        color="importance", color_continuous_scale="teal",
                        labels={"importance": "Importance", "feature": ""},
                    )
                    fig.update_layout(height=400, margin=dict(l=0, r=0, t=40, b=0),
                                      showlegend=False, coloraxis_showscale=False)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"Using cached model (key: `{metrics['cache_key']}`). Check 'Force Retrain' to rebuild.")
        else:
            st.info("Select a symbol and click **🚀 Train & Predict**.")

# ── Tab 2: Batch Scan ────────────────────────────────────────────────────────
with tab2:
    st.subheader("Scan All Nifty 50 Stocks")
    col_a, col_b, col_c = st.columns(3)
    batch_model = col_a.radio("Model", ["rf", "gb", "lr"],
                               format_func={"rf": "RF", "gb": "GB", "lr": "LR"}.get,
                               horizontal=True, key="batch_model")
    batch_horizon = col_b.select_slider("Horizon", [1, 3, 5], format_func=lambda x: f"{x}d",
                                         key="batch_horizon")
    scan_btn = col_c.button("🔍 Run Scan", type="primary")

    if scan_btn:
        prog = st.progress(0, text="Scanning...")
        results = []
        for i, sym in enumerate(NIFTY50_SYMBOLS):
            prog.progress((i + 1) / len(NIFTY50_SYMBOLS), text=f"Processing {sym}...")
            try:
                df = get_stock_history(sym, period="1y")
                if df is None or len(df) < 120:
                    continue
                pipeline, _ = train_model(df, model_type=batch_model, horizon=batch_horizon)
                sig = get_signal(pipeline, df, horizon=batch_horizon)
                results.append({"Symbol": sym, "Signal": sig["direction"],
                                 "Prob UP": f"{sig['prob_up']:.1%}",
                                 "Strength": "★" * sig["signal_strength"],
                                 "Label": sig["label"]})
            except Exception:
                continue
        prog.empty()

        if results:
            df_res = pd.DataFrame(results)
            up = df_res[df_res["Signal"] == "UP"]
            down = df_res[df_res["Signal"] == "DOWN"]
            st.metric("Bullish Signals", len(up))
            st.metric("Bearish Signals", len(down), label_visibility="collapsed")

            tab_up, tab_down = st.tabs([f"🟢 Bullish ({len(up)})", f"🔴 Bearish ({len(down)})"])
            with tab_up:
                st.dataframe(up.sort_values("Prob UP", ascending=False),
                             use_container_width=True)
            with tab_down:
                st.dataframe(down.sort_values("Prob UP"), use_container_width=True)
        else:
            st.warning("No results returned. Check data availability.")
    else:
        st.info("Click **🔍 Run Scan** to generate signals for all 50 stocks.")
