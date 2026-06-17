import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="ML Predictions", page_icon="🤖", layout="wide")

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

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error, r2_score
    SK_OK = True
except ImportError:
    SK_OK = False

NIFTY50 = [
    {"symbol":"RELIANCE.NS","name":"Reliance Industries"},{"symbol":"HDFCBANK.NS","name":"HDFC Bank"},
    {"symbol":"ICICIBANK.NS","name":"ICICI Bank"},{"symbol":"INFY.NS","name":"Infosys"},{"symbol":"TCS.NS","name":"TCS"},
    {"symbol":"BHARTIARTL.NS","name":"Bharti Airtel"},{"symbol":"ITC.NS","name":"ITC"},{"symbol":"KOTAKBANK.NS","name":"Kotak Mahindra Bank"},
    {"symbol":"LT.NS","name":"Larsen & Toubro"},{"symbol":"HCLTECH.NS","name":"HCL Technologies"},
    {"symbol":"AXISBANK.NS","name":"Axis Bank"},{"symbol":"SBIN.NS","name":"State Bank of India"},
    {"symbol":"BAJFINANCE.NS","name":"Bajaj Finance"},{"symbol":"WIPRO.NS","name":"Wipro"},
    {"symbol":"ASIANPAINT.NS","name":"Asian Paints"},{"symbol":"MARUTI.NS","name":"Maruti Suzuki"},
    {"symbol":"SUNPHARMA.NS","name":"Sun Pharmaceutical"},{"symbol":"TITAN.NS","name":"Titan Company"},
    {"symbol":"ULTRACEMCO.NS","name":"UltraTech Cement"},{"symbol":"ONGC.NS","name":"ONGC"},
    {"symbol":"NTPC.NS","name":"NTPC"},{"symbol":"POWERGRID.NS","name":"Power Grid Corp"},
    {"symbol":"M&M.NS","name":"Mahindra & Mahindra"},{"symbol":"TATAMOTORS.NS","name":"Tata Motors"},
    {"symbol":"TATASTEEL.NS","name":"Tata Steel"},{"symbol":"JSWSTEEL.NS","name":"JSW Steel"},
    {"symbol":"HINDALCO.NS","name":"Hindalco Industries"},{"symbol":"ADANIENT.NS","name":"Adani Enterprises"},
    {"symbol":"ADANIPORTS.NS","name":"Adani Ports"},{"symbol":"BAJAJFINSV.NS","name":"Bajaj Finserv"},
    {"symbol":"BAJAJAUTO.NS","name":"Bajaj Auto"},{"symbol":"HEROMOTOCO.NS","name":"Hero MotoCorp"},
    {"symbol":"CIPLA.NS","name":"Cipla"},{"symbol":"DRREDDY.NS","name":"Dr. Reddy's Labs"},
    {"symbol":"DIVISLAB.NS","name":"Divi's Laboratories"},{"symbol":"EICHERMOT.NS","name":"Eicher Motors"},
    {"symbol":"GRASIM.NS","name":"Grasim Industries"},{"symbol":"HDFCLIFE.NS","name":"HDFC Life Insurance"},
    {"symbol":"SBILIFE.NS","name":"SBI Life Insurance"},{"symbol":"INDUSINDBK.NS","name":"IndusInd Bank"},
    {"symbol":"TATACONSUM.NS","name":"Tata Consumer Products"},{"symbol":"BRITANNIA.NS","name":"Britannia Industries"},
    {"symbol":"NESTLEIND.NS","name":"Nestle India"},{"symbol":"HINDUNILVR.NS","name":"Hindustan Unilever"},
    {"symbol":"COALINDIA.NS","name":"Coal India"},{"symbol":"BPCL.NS","name":"BPCL"},
    {"symbol":"TECHM.NS","name":"Tech Mahindra"},{"symbol":"LTF.NS","name":"L&T Finance"},
    {"symbol":"SHRIRAMFIN.NS","name":"Shriram Finance"},{"symbol":"BEL.NS","name":"Bharat Electronics"},
]

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
    fig.update_xaxes(**AXIS_STYLE); fig.update_yaxes(**AXIS_STYLE); return fig

def safe_float(v, d=0.0):
    try:
        f = float(v); return d if (np.isnan(f) or np.isinf(f)) else f
    except: return d

# ── RISK DISCLOSURE CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
/* Full-width top risk banner */
.risk-banner {
    background: linear-gradient(135deg, #7f1d1d 0%, #991b1b 60%, #b91c1c 100%);
    border: 2px solid #fca5a5;
    border-radius: 12px;
    padding: 1.1rem 1.5rem;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: flex-start;
    gap: 1rem;
}
.risk-banner-icon { font-size: 2rem; flex-shrink: 0; margin-top: 2px; }
.risk-banner-title {
    color: #ffffff !important;
    font-size: 1rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}
.risk-banner-body {
    color: #fecaca !important;
    font-size: 0.85rem !important;
    line-height: 1.6;
}
.risk-banner-body b { color: #ffffff !important; }

/* Inline risk level badge */
.risk-level-high {
    background: #fff1f2;
    border: 2px solid #f87171;
    border-left: 6px solid #dc2626;
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    margin: 0.8rem 0;
}
.risk-level-moderate {
    background: #fffbeb;
    border: 2px solid #fbbf24;
    border-left: 6px solid #d97706;
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    margin: 0.8rem 0;
}
.risk-level-low {
    background: #f0fdf4;
    border: 2px solid #86efac;
    border-left: 6px solid #16a34a;
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    margin: 0.8rem 0;
}
.risk-level-title {
    font-size: 1rem !important;
    font-weight: 800 !important;
    margin-bottom: 0.25rem;
}
.risk-level-high   .risk-level-title { color: #991b1b !important; }
.risk-level-moderate .risk-level-title { color: #92400e !important; }
.risk-level-low    .risk-level-title { color: #14532d !important; }
.risk-level-body {
    font-size: 0.88rem !important;
    line-height: 1.5;
}
.risk-level-high   .risk-level-body { color: #7f1d1d !important; }
.risk-level-moderate .risk-level-body { color: #78350f !important; }
.risk-level-low    .risk-level-body { color: #166534 !important; }

/* Sticky footer disclaimer */
.risk-footer {
    background: #1e1b4b;
    border: 1.5px solid #4338ca;
    border-radius: 10px;
    padding: 0.85rem 1.3rem;
    margin-top: 2rem;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
}
.risk-footer-icon { font-size: 1.2rem; flex-shrink: 0; }
.risk-footer-text {
    color: #c7d2fe !important;
    font-size: 0.78rem !important;
    line-height: 1.65;
}
.risk-footer-text b { color: #e0e7ff !important; }

/* Model accuracy callout */
.model-caveat {
    background: #fefce8;
    border: 1.5px solid #fde047;
    border-radius: 8px;
    padding: 0.6rem 1rem;
    margin: 0.5rem 0 1rem;
    font-size: 0.82rem !important;
    color: #713f12 !important;
}
</style>
""", unsafe_allow_html=True)

# ── HERO ──────────────────────────────────────────────────────────────────
st.markdown("""
<div style='background:linear-gradient(135deg,#1e1b4b 0%,#312e81 50%,#4c1d95 100%);
     border-radius:14px;padding:1.4rem 1.8rem;margin-bottom:1rem;
     display:flex;align-items:center;gap:1.2rem;'>
  <div style='font-size:2.6rem;'>🤖</div>
  <div>
    <div style='color:#fff;font-size:1.35rem;font-weight:700;'>ML Predictions</div>
    <div style='color:#c4b5fd;font-size:.85rem;margin-top:.3rem;'>
      Predicts worst-case drawdowns using Random Forest, Gradient Boosting & Linear Regression
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── ⚠️ PROMINENT RISK DISCLOSURE BANNER (always visible, top of page) ─────
st.markdown("""
<div class="risk-banner">
  <div class="risk-banner-icon">⚠️</div>
  <div>
    <div class="risk-banner-title">⛔ Not Investment Advice — Read Before Using</div>
    <div class="risk-banner-body">
      <b>These ML predictions are for educational and research purposes only.</b>
      They do <b>not</b> constitute financial advice, investment recommendations, or solicitation to buy/sell
      any security. Stock market predictions are inherently uncertain — past patterns do not guarantee
      future results. <b>ML models trained on historical data can fail significantly in real markets</b>,
      especially during earnings, macro events, or high-volatility regimes.
      <br><br>
      🔴 <b>Never make real trading decisions based solely on these outputs.</b>
      Always consult a SEBI-registered financial advisor before investing.
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

if not SK_OK:
    st.error("❌ `scikit-learn` not installed. Add it to requirements.txt and redeploy.")
    st.stop()

ML_N2S   = {s["name"]: s["symbol"] for s in NIFTY50}
ML_NAMES = [s["name"] for s in NIFTY50]

c1, c2, c3, c4 = st.columns(4)
with c1: ml_stock   = st.selectbox("🏢 Company",       ML_NAMES,           key="dml_stock")
with c2: ml_period  = st.selectbox("📅 History",       ["6mo","1y","2y"],  key="dml_period")
with c3: ml_horizon = st.slider(  "📆 Forecast days", 5, 30, 10,          key="dml_horizon")
with c4: dd_pct     = st.slider(  "📉 Drawdown trigger %", 1, 20, 5,       key="dml_dd")

@st.cache_data(ttl=300)
def _load(sym, period):
    try:
        h = yf.Ticker(sym).history(period=period, auto_adjust=True)
        if h is not None and not h.empty:
            h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
            return h
    except: pass
    return pd.DataFrame()

with st.spinner("🔮 Fetching data & training models…"):
    hist = _load(ML_N2S[ml_stock], ml_period)

if hist.empty or len(hist) < 40:
    st.warning("⚠️ Not enough data. Try a longer period.")
    st.stop()

try:
    _c = hist["Close"]
    if isinstance(_c, pd.DataFrame): _c = _c.iloc[:, 0]
    close = _c.dropna().astype(float).values.flatten()
    dates = hist.index[:len(close)]
    if len(close) < 40:
        st.warning("⚠️ Not enough clean price data. Try a longer period."); st.stop()

    def make_features(prices):
        n = len(prices); feats = []
        for i in range(10, n):
            p=prices[i]; r1=(p-prices[i-1])/prices[i-1]*100 if prices[i-1]!=0 else 0
            r5=(p-prices[i-5])/prices[i-5]*100 if prices[i-5]!=0 else 0
            r10=(p-prices[i-10])/prices[i-10]*100 if prices[i-10]!=0 else 0
            ma5=prices[i-5:i].mean(); ma10=prices[i-10:i].mean()
            std5=prices[i-5:i].std(); hi5=prices[i-5:i].max(); lo5=prices[i-5:i].min()
            drawdown=(p-hi5)/hi5*100 if hi5!=0 else 0
            feats.append([i,r1,r5,r10,ma5,ma10,std5,hi5,lo5,drawdown])
        return np.array(feats)

    feats = make_features(close)
    X_all = feats[:, :-1]; y_dd = feats[:, -1]
    scaler = StandardScaler(); X_sc = scaler.fit_transform(X_all)
    rf = RandomForestRegressor(n_estimators=150, random_state=42)
    gb = GradientBoostingRegressor(n_estimators=150, learning_rate=0.05, random_state=42)
    lr = LinearRegression()
    rf.fit(X_sc, y_dd); gb.fit(X_sc, y_dd); lr.fit(X_sc, y_dd)
    rf_pred_hist=rf.predict(X_sc); gb_pred_hist=gb.predict(X_sc); lr_pred_hist=lr.predict(X_sc)
    rf_mae=mean_absolute_error(y_dd,rf_pred_hist); gb_mae=mean_absolute_error(y_dd,gb_pred_hist)
    rf_r2=r2_score(y_dd,rf_pred_hist); gb_r2=r2_score(y_dd,gb_pred_hist)

    fut_feats=[]; ext=close.tolist()
    for i in range(ml_horizon):
        last_idx=len(ext)-1; p=ext[-1]
        r1=(p-ext[-2])/ext[-2]*100 if len(ext)>=2 and ext[-2]!=0 else 0
        r5=(p-ext[-6])/ext[-6]*100 if len(ext)>=6 and ext[-6]!=0 else 0
        r10=(p-ext[-11])/ext[-11]*100 if len(ext)>=11 and ext[-11]!=0 else 0
        ma5=float(np.mean(ext[-5:])); ma10=float(np.mean(ext[-10:]))
        std5=float(np.std(ext[-5:])); hi5=float(max(ext[-5:])); lo5=float(min(ext[-5:]))
        fut_feats.append([last_idx+i+1,r1,r5,r10,ma5,ma10,std5,hi5,lo5])
        ext.append(p*(1+float(np.random.normal(0,0.005))))

    fut_X=np.array(fut_feats); fut_X_sc=scaler.transform(fut_X)
    rf_fut=rf.predict(fut_X_sc); gb_fut=gb.predict(fut_X_sc); lr_fut=lr.predict(fut_X_sc)

    last_date=pd.Timestamp(dates[-1]); fut_dates=[]; _d=last_date
    while len(fut_dates)<ml_horizon:
        _d+=pd.Timedelta(days=1)
        if _d.weekday()<5: fut_dates.append(_d)

    last_price=float(close[-1])
    rf_prices=[last_price*(1+dd/100) for dd in rf_fut]
    gb_prices=[last_price*(1+dd/100) for dd in gb_fut]
    lr_prices=[last_price*(1+dd/100) for dd in lr_fut]
    worst_pct=min(float(rf_fut.min()),float(gb_fut.min()))
    worst_price=last_price*(1+worst_pct/100)
    trigger=last_price*(1-dd_pct/100)

    # ── KPI row ────────────────────────────────────────────────────────────
    m1,m2,m3,m4,m5,m6=st.columns(6)
    m1.metric("Current Price",f"₹{last_price:,.2f}")
    m2.metric("RF MAE",f"{rf_mae:.3f}%")
    m3.metric("GB MAE",f"{gb_mae:.3f}%")
    m4.metric("RF R²",f"{rf_r2:.3f}")
    m5.metric("GB R²",f"{gb_r2:.3f}")
    m6.metric("Worst Drawdown",f"{worst_pct:.2f}%",delta=f"₹{worst_price:,.2f}",delta_color="inverse")

    # ── Model accuracy caveat (always shown) ───────────────────────────────
    st.markdown(f"""
    <div class="model-caveat">
      📐 <b>Model accuracy note:</b> RF R² = <b>{rf_r2:.3f}</b>, GB R² = <b>{gb_r2:.3f}</b>.
      R² close to 1.0 may indicate <b>overfitting to historical data</b> — this does not mean the model
      will predict future prices accurately. MAE is measured on <i>training data</i> and is not
      an out-of-sample performance metric.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr style="border:none;border-top:1px solid #e2e8f0;margin:.6rem 0;">',unsafe_allow_html=True)

    # ── PROMINENT inline risk level alert ──────────────────────────────────
    best_model_worst = min(float(rf_fut.min()), float(gb_fut.min()))

    if best_model_worst <= -dd_pct:
        st.markdown(f"""
        <div class="risk-level-high">
          <div class="risk-level-title">🚨 HIGH DOWNSIDE RISK DETECTED</div>
          <div class="risk-level-body">
            Models project a drawdown of up to <b>{best_model_worst:.1f}%</b> within <b>{ml_horizon} trading days</b>.<br>
            Trigger price: <b>₹{trigger:,.2f}</b> (−{dd_pct}% from current ₹{last_price:,.2f})<br><br>
            ⚠️ <b>This is a model output — not a guaranteed outcome.</b> Real markets can move
            far beyond model predictions. Do NOT use this as a stop-loss or sell signal without
            independent analysis.
          </div>
        </div>
        """, unsafe_allow_html=True)
    elif best_model_worst <= -dd_pct * 0.5:
        st.markdown(f"""
        <div class="risk-level-moderate">
          <div class="risk-level-title">⚠️ MODERATE RISK — Monitor Closely</div>
          <div class="risk-level-body">
            Models suggest a drawdown of <b>{best_model_worst:.1f}%</b> over <b>{ml_horizon} trading days</b>.<br>
            Watch level: <b>₹{trigger:,.2f}</b><br><br>
            This is within normal market volatility range but warrants attention.
            <b>Not a recommendation to buy, hold, or sell.</b>
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="risk-level-low">
          <div class="risk-level-title">✅ LOW PREDICTED RISK</div>
          <div class="risk-level-body">
            Models predict a max drawdown of <b>{best_model_worst:.1f}%</b> over <b>{ml_horizon} trading days</b>.<br><br>
            Low predicted risk does <b>not</b> mean safe to invest. Models cannot anticipate
            earnings surprises, macro shocks, or geopolitical events. <b>Always do your own research.</b>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Charts ─────────────────────────────────────────────────────────────
    tab1,tab2,tab3=st.tabs(["📉 Drawdown Forecast","💹 Price Forecast","📊 Model Comparison"])

    with tab1:
        st.markdown("""
        <div class="model-caveat">
          📌 <b>Chart note:</b> Shaded forecast region uses randomly simulated future prices as model input.
          The forecast band is illustrative — actual drawdowns may be larger or smaller.
        </div>
        """, unsafe_allow_html=True)
        fig_dd=go.Figure()
        fig_dd.add_trace(go.Scatter(x=dates[10:],y=y_dd,mode="lines",name="Actual",line=dict(color="#1e293b",width=1.5)))
        fig_dd.add_trace(go.Scatter(x=dates[10:],y=rf_pred_hist,mode="lines",name="RF hist",line=dict(color="#ef4444",width=1.5,dash="dot")))
        fig_dd.add_trace(go.Scatter(x=fut_dates,y=rf_fut,mode="lines+markers",name="RF Forecast",line=dict(color="#ef4444",width=2.5)))
        fig_dd.add_trace(go.Scatter(x=fut_dates,y=gb_fut,mode="lines+markers",name="GB Forecast",line=dict(color="#f59e0b",width=2.5)))
        fig_dd.add_trace(go.Scatter(x=fut_dates,y=lr_fut,mode="lines+markers",name="Linear",line=dict(color="#8b5cf6",width=2,dash="dash")))
        fig_dd.add_hline(y=-dd_pct,line_dash="dash",line_color="#ef4444",annotation_text=f"Trigger −{dd_pct}%")
        fig_dd.update_layout(**PLT_LAYOUT,title=f"{ml_stock} — {ml_horizon}-Day Drawdown Forecast (Simulated)",height=460,xaxis_title="Date",yaxis_title="Drawdown (%)")
        style_fig(fig_dd); fig_dd.update_layout(autosize=True); st.plotly_chart(fig_dd,use_container_width=True)

    with tab2:
        st.markdown("""
        <div class="model-caveat">
          📌 <b>Chart note:</b> Implied prices are derived from drawdown predictions, not direct price forecasts.
          The dashed trigger line is a reference level — <b>not a prediction of where price will go.</b>
        </div>
        """, unsafe_allow_html=True)
        fig_pr=go.Figure()
        fig_pr.add_trace(go.Scatter(x=dates,y=close,mode="lines",name="Actual",line=dict(color="#1e293b",width=2)))
        fig_pr.add_trace(go.Scatter(x=fut_dates,y=rf_prices,mode="lines+markers",name="RF Implied",line=dict(color="#ef4444",width=2.5)))
        fig_pr.add_trace(go.Scatter(x=fut_dates,y=gb_prices,mode="lines+markers",name="GB Implied",line=dict(color="#f59e0b",width=2.5)))
        fig_pr.add_hline(y=trigger,line_dash="dash",line_color="#ef4444",annotation_text=f"Trigger ₹{trigger:,.0f}")
        fig_pr.update_layout(**PLT_LAYOUT,title=f"{ml_stock} — Implied Price (Educational Only)",height=460,xaxis_title="Date",yaxis_title="Price (₹)")
        style_fig(fig_pr); fig_pr.update_layout(autosize=True); st.plotly_chart(fig_pr,use_container_width=True)

    with tab3:
        cmp_df=pd.DataFrame({"Date":[d.strftime("%d %b") for d in fut_dates],"RF %":[f"{v:.2f}%" for v in rf_fut],"GB %":[f"{v:.2f}%" for v in gb_fut],"LR %":[f"{v:.2f}%" for v in lr_fut],"RF Price":[f"₹{v:,.2f}" for v in rf_prices],"GB Price":[f"₹{v:,.2f}" for v in gb_prices]})
        st.dataframe(cmp_df,use_container_width=True,hide_index=True)
        feat_names=["Index","Return 1D","Return 5D","Return 10D","MA5","MA10","StdDev5","High5","Low5"]
        fi_df=pd.DataFrame({"Feature":feat_names,"Importance":rf.feature_importances_}).sort_values("Importance",ascending=True)
        fig_fi=px.bar(fi_df,x="Importance",y="Feature",orientation="h",color="Importance",color_continuous_scale="Reds_r",title="Feature Importance (RF)",template="plotly_white",height=320)
        fig_fi.update_layout(**PLT_LAYOUT,coloraxis_showscale=False)
        style_fig(fig_fi); fig_fi.update_layout(autosize=True); st.plotly_chart(fig_fi,use_container_width=True)

    # ── FOOTER DISCLAIMER (always visible at bottom) ───────────────────────
    st.markdown("""
    <div class="risk-footer">
      <div class="risk-footer-icon">⚖️</div>
      <div class="risk-footer-text">
        <b>Legal Disclaimer:</b> All predictions and outputs on this page are generated by machine learning
        models trained on historical market data. They are provided <b>for educational and research purposes
        only</b> and do not constitute financial advice, investment recommendations, or an offer to buy or sell
        any securities. Past performance and model accuracy on historical data are <b>not indicative of future
        results</b>. Stock markets involve substantial risk of loss. The creators of this tool are not SEBI-registered
        investment advisors. <b>Always consult a qualified financial professional before making investment decisions.</b>
      </div>
    </div>
    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"❌ Model error: {e}")
