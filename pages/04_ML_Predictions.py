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

st.markdown("""
<div style='background:linear-gradient(135deg,#1e1b4b 0%,#312e81 50%,#4c1d95 100%);
     border-radius:14px;padding:1.4rem 1.8rem;margin-bottom:1.2rem;
     display:flex;align-items:center;gap:1.2rem;'>
  <div style='font-size:2.6rem;'>🤖</div>
  <div>
    <div style='color:#fff;font-size:1.35rem;font-weight:700;'>ML Predictions</div>
    <div style='color:#c4b5fd;font-size:.85rem;margin-top:.3rem;'>
      <span style='background:rgba(239,68,68,.25);color:#fca5a5;border:1px solid rgba(239,68,68,.4);
        border-radius:20px;padding:.15rem .7rem;font-size:.75rem;font-weight:600;'>⚠️ Risk Analysis</span>
      &nbsp;&nbsp;Predicts worst-case drawdowns using ML models
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

    m1,m2,m3,m4,m5,m6=st.columns(6)
    m1.metric("Current Price",f"₹{last_price:,.2f}")
    m2.metric("RF MAE",f"{rf_mae:.3f}%")
    m3.metric("GB MAE",f"{gb_mae:.3f}%")
    m4.metric("RF R²",f"{rf_r2:.3f}")
    m5.metric("GB R²",f"{gb_r2:.3f}")
    m6.metric("Worst Drawdown",f"{worst_pct:.2f}%",delta=f"₹{worst_price:,.2f}",delta_color="inverse")

    st.markdown('<hr style="border:none;border-top:1px solid #e2e8f0;margin:.6rem 0;">',unsafe_allow_html=True)
    best_model_worst=min(float(rf_fut.min()),float(gb_fut.min()))
    if best_model_worst<=-dd_pct:
        st.error(f"🚨 HIGH DOWNSIDE RISK — drawdown up to **{best_model_worst:.1f}%** in {ml_horizon} days. Trigger: ₹{trigger:,.2f}")
    elif best_model_worst<=-dd_pct*0.5:
        st.warning(f"⚠️ MODERATE RISK — drawdown: **{best_model_worst:.1f}%**. Watch ₹{trigger:,.2f}")
    else:
        st.success(f"✅ LOW RISK — Max drawdown: **{best_model_worst:.1f}%** over {ml_horizon} days.")

    tab1,tab2,tab3=st.tabs(["📉 Drawdown Forecast","💹 Price Forecast","📊 Model Comparison"])
    with tab1:
        fig_dd=go.Figure()
        fig_dd.add_trace(go.Scatter(x=dates[10:],y=y_dd,mode="lines",name="Actual",line=dict(color="#1e293b",width=1.5)))
        fig_dd.add_trace(go.Scatter(x=dates[10:],y=rf_pred_hist,mode="lines",name="RF hist",line=dict(color="#ef4444",width=1.5,dash="dot")))
        fig_dd.add_trace(go.Scatter(x=fut_dates,y=rf_fut,mode="lines+markers",name="RF Forecast",line=dict(color="#ef4444",width=2.5)))
        fig_dd.add_trace(go.Scatter(x=fut_dates,y=gb_fut,mode="lines+markers",name="GB Forecast",line=dict(color="#f59e0b",width=2.5)))
        fig_dd.add_trace(go.Scatter(x=fut_dates,y=lr_fut,mode="lines+markers",name="Linear",line=dict(color="#8b5cf6",width=2,dash="dash")))
        fig_dd.add_hline(y=-dd_pct,line_dash="dash",line_color="#ef4444",annotation_text=f"Trigger −{dd_pct}%")
        fig_dd.update_layout(**PLT_LAYOUT,title=f"{ml_stock} — {ml_horizon}-Day Drawdown Forecast",height=460,xaxis_title="Date",yaxis_title="Drawdown (%)")
        style_fig(fig_dd); st.plotly_chart(fig_dd,use_container_width=True)
    with tab2:
        fig_pr=go.Figure()
        fig_pr.add_trace(go.Scatter(x=dates,y=close,mode="lines",name="Actual",line=dict(color="#1e293b",width=2)))
        fig_pr.add_trace(go.Scatter(x=fut_dates,y=rf_prices,mode="lines+markers",name="RF Implied",line=dict(color="#ef4444",width=2.5)))
        fig_pr.add_trace(go.Scatter(x=fut_dates,y=gb_prices,mode="lines+markers",name="GB Implied",line=dict(color="#f59e0b",width=2.5)))
        fig_pr.add_hline(y=trigger,line_dash="dash",line_color="#ef4444",annotation_text=f"Trigger ₹{trigger:,.0f}")
        fig_pr.update_layout(**PLT_LAYOUT,title=f"{ml_stock} — Implied Price",height=460,xaxis_title="Date",yaxis_title="Price (₹)")
        style_fig(fig_pr); st.plotly_chart(fig_pr,use_container_width=True)
    with tab3:
        cmp_df=pd.DataFrame({"Date":[d.strftime("%d %b") for d in fut_dates],"RF %":[f"{v:.2f}%" for v in rf_fut],"GB %":[f"{v:.2f}%" for v in gb_fut],"LR %":[f"{v:.2f}%" for v in lr_fut],"RF Price":[f"₹{v:,.2f}" for v in rf_prices],"GB Price":[f"₹{v:,.2f}" for v in gb_prices]})
        st.dataframe(cmp_df,use_container_width=True,hide_index=True)
        feat_names=["Index","Return 1D","Return 5D","Return 10D","MA5","MA10","StdDev5","High5","Low5"]
        fi_df=pd.DataFrame({"Feature":feat_names,"Importance":rf.feature_importances_}).sort_values("Importance",ascending=True)
        fig_fi=px.bar(fi_df,x="Importance",y="Feature",orientation="h",color="Importance",color_continuous_scale="Reds_r",title="Feature Importance",template="plotly_white",height=320)
        fig_fi.update_layout(**PLT_LAYOUT,coloraxis_showscale=False)
        style_fig(fig_fi); st.plotly_chart(fig_fi,use_container_width=True)

    st.caption("⚠️ Educational purposes only — not investment advice.")
except Exception as e:
    st.error(f"❌ Model error: {e}")
