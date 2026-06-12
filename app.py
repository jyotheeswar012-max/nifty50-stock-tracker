import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Nifty 50 Stock Tracker", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .tag-actual  { background:#00c853;color:black;padding:2px 10px;border-radius:20px;font-size:13px;font-weight:bold; }
    .tag-assumed { background:#ffd600;color:black;padding:2px 10px;border-radius:20px;font-size:13px;font-weight:bold; }
    .stMetric label { color:#9e9e9e !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# ALL 50 NIFTY COMPANIES — Symbol, Name, Sector, Beta
# =========================================================
NIFTY50 = [
    {"symbol":"RELIANCE.NS",   "name":"Reliance Industries",      "sector":"Energy",             "beta":0.90},
    {"symbol":"HDFCBANK.NS",   "name":"HDFC Bank",                "sector":"Financial Services", "beta":1.10},
    {"symbol":"ICICIBANK.NS",  "name":"ICICI Bank",               "sector":"Financial Services", "beta":1.20},
    {"symbol":"INFY.NS",       "name":"Infosys",                  "sector":"IT",                 "beta":0.75},
    {"symbol":"TCS.NS",        "name":"TCS",                      "sector":"IT",                 "beta":0.70},
    {"symbol":"BHARTIARTL.NS", "name":"Bharti Airtel",            "sector":"Telecom",            "beta":0.85},
    {"symbol":"ITC.NS",        "name":"ITC",                      "sector":"FMCG",               "beta":0.65},
    {"symbol":"KOTAKBANK.NS",  "name":"Kotak Mahindra Bank",      "sector":"Financial Services", "beta":1.05},
    {"symbol":"LT.NS",         "name":"Larsen & Toubro",          "sector":"Construction",       "beta":1.10},
    {"symbol":"HCLTECH.NS",    "name":"HCL Technologies",         "sector":"IT",                 "beta":0.80},
    {"symbol":"AXISBANK.NS",   "name":"Axis Bank",                "sector":"Financial Services", "beta":1.30},
    {"symbol":"SBIN.NS",       "name":"State Bank of India",      "sector":"Financial Services", "beta":1.35},
    {"symbol":"BAJFINANCE.NS", "name":"Bajaj Finance",            "sector":"Financial Services", "beta":1.40},
    {"symbol":"WIPRO.NS",      "name":"Wipro",                    "sector":"IT",                 "beta":0.72},
    {"symbol":"ASIANPAINT.NS", "name":"Asian Paints",             "sector":"Consumer Goods",     "beta":0.60},
    {"symbol":"MARUTI.NS",     "name":"Maruti Suzuki",            "sector":"Automobile",         "beta":0.95},
    {"symbol":"SUNPHARMA.NS",  "name":"Sun Pharmaceutical",       "sector":"Pharma",             "beta":0.70},
    {"symbol":"TITAN.NS",      "name":"Titan Company",            "sector":"Consumer Goods",     "beta":0.90},
    {"symbol":"ULTRACEMCO.NS", "name":"UltraTech Cement",         "sector":"Cement",             "beta":0.85},
    {"symbol":"ONGC.NS",       "name":"ONGC",                     "sector":"Energy",             "beta":1.00},
    {"symbol":"NTPC.NS",       "name":"NTPC",                     "sector":"Power",              "beta":0.80},
    {"symbol":"POWERGRID.NS",  "name":"Power Grid Corp",          "sector":"Power",              "beta":0.75},
    {"symbol":"M&M.NS",        "name":"Mahindra & Mahindra",      "sector":"Automobile",         "beta":1.05},
    {"symbol":"TATAMOTORS.NS", "name":"Tata Motors",              "sector":"Automobile",         "beta":1.45},
    {"symbol":"TATASTEEL.NS",  "name":"Tata Steel",               "sector":"Metals",             "beta":1.50},
    {"symbol":"JSWSTEEL.NS",   "name":"JSW Steel",                "sector":"Metals",             "beta":1.40},
    {"symbol":"HINDALCO.NS",   "name":"Hindalco Industries",      "sector":"Metals",             "beta":1.35},
    {"symbol":"ADANIENT.NS",   "name":"Adani Enterprises",        "sector":"Conglomerate",       "beta":1.60},
    {"symbol":"ADANIPORTS.NS", "name":"Adani Ports",              "sector":"Infrastructure",     "beta":1.20},
    {"symbol":"BAJAJFINSV.NS", "name":"Bajaj Finserv",            "sector":"Financial Services", "beta":1.25},
    {"symbol":"BAJAJ-AUTO.NS", "name":"Bajaj Auto",               "sector":"Automobile",         "beta":0.90},
    {"symbol":"HEROMOTOCO.NS", "name":"Hero MotoCorp",            "sector":"Automobile",         "beta":0.85},
    {"symbol":"CIPLA.NS",      "name":"Cipla",                    "sector":"Pharma",             "beta":0.65},
    {"symbol":"DRREDDY.NS",    "name":"Dr. Reddy's Labs",         "sector":"Pharma",             "beta":0.60},
    {"symbol":"DIVISLAB.NS",   "name":"Divi's Laboratories",      "sector":"Pharma",             "beta":0.70},
    {"symbol":"EICHERMOT.NS",  "name":"Eicher Motors",            "sector":"Automobile",         "beta":0.95},
    {"symbol":"GRASIM.NS",     "name":"Grasim Industries",        "sector":"Cement",             "beta":0.90},
    {"symbol":"HDFCLIFE.NS",   "name":"HDFC Life Insurance",      "sector":"Financial Services", "beta":0.95},
    {"symbol":"SBILIFE.NS",    "name":"SBI Life Insurance",       "sector":"Financial Services", "beta":0.90},
    {"symbol":"INDUSINDBK.NS", "name":"IndusInd Bank",            "sector":"Financial Services", "beta":1.45},
    {"symbol":"TATACONSUM.NS", "name":"Tata Consumer Products",   "sector":"FMCG",               "beta":0.75},
    {"symbol":"BRITANNIA.NS",  "name":"Britannia Industries",     "sector":"FMCG",               "beta":0.60},
    {"symbol":"NESTLEIND.NS",  "name":"Nestle India",             "sector":"FMCG",               "beta":0.55},
    {"symbol":"HINDUNILVR.NS", "name":"Hindustan Unilever",       "sector":"FMCG",               "beta":0.58},
    {"symbol":"COALINDIA.NS",  "name":"Coal India",               "sector":"Energy",             "beta":0.85},
    {"symbol":"BPCL.NS",       "name":"BPCL",                     "sector":"Energy",             "beta":1.10},
    {"symbol":"TECHM.NS",      "name":"Tech Mahindra",            "sector":"IT",                 "beta":0.85},
    {"symbol":"LTF.NS",        "name":"L&T Finance",              "sector":"Financial Services", "beta":1.30},
    {"symbol":"SHRIRAMFIN.NS", "name":"Shriram Finance",          "sector":"Financial Services", "beta":1.20},
    {"symbol":"BEL.NS",        "name":"Bharat Electronics",       "sector":"Defence",            "beta":1.15},
]

nifty50_df = pd.DataFrame(NIFTY50)
sectors = ["All"] + sorted(nifty50_df["sector"].unique().tolist())

# =========================================================
# TITLE
# =========================================================
st.title("📈 Nifty 50 Stock Tracker")
st.markdown("Track **all 50 Nifty companies** — live prices, sector breakdown, heatmap, gainers/losers & your P&L calculator.")
st.markdown("---")

# =========================================================
# SECTION 1: LIVE NIFTY 50 INDEX
# =========================================================
st.header("🟢 Live Nifty 50 Index")
st.markdown('<span class="tag-actual">LIVE DATA</span> &nbsp; Real-time from Yahoo Finance / NSE', unsafe_allow_html=True)
st.markdown("")

@st.cache_data(ttl=300)
def get_nifty_data(period="3mo"):
    nifty = yf.Ticker("^NSEI")
    hist  = nifty.history(period=period)
    return hist

nifty_live_ok = False
try:
    hist = get_nifty_data()
    if hist.empty:
        raise ValueError("Empty")
    current_price = hist['Close'].iloc[-1]
    prev_price    = hist['Close'].iloc[-2]
    change        = current_price - prev_price
    pct_change    = (change / prev_price) * 100
    nifty_live_ok = True

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Current Value",  f"₹{current_price:,.2f}")
    c2.metric("Points Change",  f"{change:+.2f}")
    c3.metric("% Change",       f"{pct_change:+.2f}%")
    c4.metric("Period High",    f"₹{hist['High'].max():,.2f}")
    c5.metric("Period Low",     f"₹{hist['Low'].min():,.2f}")

    hist['MA20'] = hist['Close'].rolling(20).mean()
    fig_idx = go.Figure()
    fig_idx.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'],
        low=hist['Low'], close=hist['Close'], name="Nifty 50",
        increasing_line_color="#00c853", decreasing_line_color="#ff1744"))
    fig_idx.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], mode='lines',
        name='20-Day MA', line=dict(color='#ffd600', width=1.5, dash='dot')))
    fig_idx.update_layout(title="Nifty 50 — Last 3 Months", template="plotly_dark",
        height=420, xaxis_title="Date", yaxis_title="Index Value")
    st.plotly_chart(fig_idx, use_container_width=True)

    hist['Daily_Return_%'] = hist['Close'].pct_change() * 100
    fig_ret = px.bar(hist.dropna(), x=hist.dropna().index, y='Daily_Return_%',
        color='Daily_Return_%', color_continuous_scale=["#ff1744","#ffd600","#00c853"],
        title="Daily Returns (%)", template="plotly_dark", height=280)
    st.plotly_chart(fig_ret, use_container_width=True)

except Exception as e:
    st.warning(f"⚠️ Live index data unavailable: {e}")
    current_price, pct_change, change = 22500.0, -0.89, -200.0

st.markdown("---")

# =========================================================
# SECTION 2: ALL 50 COMPANIES — Live Prices
# =========================================================
st.header("🏢 All 50 Nifty Companies — Live Data")
st.markdown('<span class="tag-actual">LIVE DATA</span>', unsafe_allow_html=True)
st.markdown("")

col_filter, col_sort = st.columns([2,1])
with col_filter:
    sector_filter = st.selectbox("Filter by Sector", sectors)
with col_sort:
    sort_by = st.selectbox("Sort by", ["Name", "Price ↑", "Price ↓", "Change % ↑", "Change % ↓"])

@st.cache_data(ttl=300)
def fetch_all_nifty50():
    symbols = [s["symbol"] for s in NIFTY50]
    data = yf.download(symbols, period="2d", auto_adjust=True, progress=False)
    return data

with st.spinner("⏳ Fetching live prices for all 50 stocks..."):
    try:
        raw = fetch_all_nifty50()
        rows = []
        for s in NIFTY50:
            sym = s["symbol"]
            try:
                closes = raw['Close'][sym].dropna()
                curr   = closes.iloc[-1]
                prev   = closes.iloc[-2]
                chg    = curr - prev
                pct    = (chg / prev) * 100
            except:
                curr = prev = chg = pct = None
            rows.append({
                "Symbol":   sym.replace(".NS",""),
                "Company":  s["name"],
                "Sector":   s["sector"],
                "Beta":     s["beta"],
                "Price (₹)": round(curr,2) if curr else "N/A",
                "Change (₹)": round(chg,2) if chg else "N/A",
                "Change (%)": round(pct,2) if pct else "N/A",
                "_curr": curr, "_chg": chg, "_pct": pct
            })
        all_df = pd.DataFrame(rows)
        fetch_ok = True
    except Exception as ex:
        st.warning(f"Could not fetch stock prices: {ex}")
        all_df = nifty50_df.rename(columns={"symbol":"Symbol","name":"Company","sector":"Sector","beta":"Beta"})
        all_df["Price (₹)"] = "N/A"; all_df["Change (₹)"] = "N/A"; all_df["Change (%)"] = "N/A"
        all_df["_curr"] = None; all_df["_chg"] = None; all_df["_pct"] = None
        fetch_ok = False

# Filter
display_df = all_df if sector_filter == "All" else all_df[all_df["Sector"] == sector_filter]

# Sort
if sort_by == "Price ↑"     and "_curr" in display_df: display_df = display_df.sort_values("_curr", ascending=True)
elif sort_by == "Price ↓"   and "_curr" in display_df: display_df = display_df.sort_values("_curr", ascending=False)
elif sort_by == "Change % ↑" and "_pct" in display_df: display_df = display_df.sort_values("_pct", ascending=True)
elif sort_by == "Change % ↓" and "_pct" in display_df: display_df = display_df.sort_values("_pct", ascending=False)
else: display_df = display_df.sort_values("Company")

st.dataframe(
    display_df[["Symbol","Company","Sector","Beta","Price (₹)","Change (₹)","Change (%)"]],
    use_container_width=True, hide_index=True
)
st.caption(f"Showing {len(display_df)} of 50 companies")

st.markdown("---")

# =========================================================
# SECTION 3: TOP GAINERS & LOSERS
# =========================================================
st.header("🏆 Top Gainers & Losers")

if fetch_ok:
    valid = all_df.dropna(subset=["_pct"])
    gainers = valid.nlargest(5, "_pct")[["Company","Sector","Price (₹)","Change (%)"]]
    losers  = valid.nsmallest(5, "_pct")[["Company","Sector","Price (₹)","Change (%)"]]

    col_g, col_l = st.columns(2)
    with col_g:
        st.markdown("### 🟢 Top 5 Gainers")
        st.dataframe(gainers, use_container_width=True, hide_index=True)
    with col_l:
        st.markdown("### 🔴 Top 5 Losers")
        st.dataframe(losers, use_container_width=True, hide_index=True)

    # Heatmap of all 50 stocks by % change
    valid2 = all_df.dropna(subset=["_pct"]).copy()
    fig_heat = px.treemap(
        valid2, path=["Sector","Company"],
        values=[abs(p) if p else 0.01 for p in valid2["_pct"]],
        color="_pct",
        color_continuous_scale=["#ff1744","#ffd600","#00c853"],
        color_continuous_midpoint=0,
        title="📊 Nifty 50 Heatmap — % Change by Sector & Stock",
        hover_data={"Price (₹)": True, "Change (%)": True}
    )
    fig_heat.update_layout(template="plotly_dark", height=500)
    st.plotly_chart(fig_heat, use_container_width=True)
else:
    st.info("Live data unavailable for gainers/losers.")

st.markdown("---")

# =========================================================
# SECTION 4: ASSUMED SCENARIO + CALCULATOR
# =========================================================
st.header("🟡 Assumed Nifty Scenario + P&L Calculator")
st.markdown('<span class="tag-assumed">SIMULATED</span> &nbsp; Pick any Nifty 50 company and simulate impact', unsafe_allow_html=True)
st.markdown("")

col_l, col_r = st.columns(2)

with col_l:
    st.subheader("📊 Set Assumed Nifty Movement")
    assumed_base   = st.number_input("Assumed Base Nifty Value", value=float(round(current_price,2)), step=50.0)
    assumed_change = st.number_input("Assumed Change in Points (+ gain / − loss)", value=-200.0, step=10.0)
    assumed_new    = assumed_base + assumed_change
    assumed_pct    = (assumed_change / assumed_base) * 100
    st.info(f"📌 Assumed % Change: **{assumed_pct:+.2f}%** → New Value: **{assumed_new:,.2f}**")

    if nifty_live_ok:
        compare_df = pd.DataFrame({
            "Metric":     ["Base Value","Change (pts)","Change (%)","New Value"],
            "🟢 Actual":  [f"₹{current_price:,.2f}", f"{change:+.2f}", f"{pct_change:+.2f}%", f"₹{current_price:,.2f}"],
            "🟡 Assumed": [f"₹{assumed_base:,.2f}", f"{assumed_change:+.2f}", f"{assumed_pct:+.2f}%", f"₹{assumed_new:,.2f}"]
        })
        st.dataframe(compare_df, use_container_width=True, hide_index=True)

with col_r:
    st.subheader("💼 Your Stock Details")
    company_names = ["Custom"] + nifty50_df["name"].tolist()
    selected_co   = st.selectbox("Select Nifty 50 Company (or Custom)", company_names)

    if selected_co != "Custom":
        row         = nifty50_df[nifty50_df["name"] == selected_co].iloc[0]
        default_beta = float(row["beta"])
        stock_name  = selected_co
    else:
        default_beta = 1.0
        stock_name   = st.text_input("Enter Stock Name", value="My Stock")

    stock_price = st.number_input("Stock Current Price (₹)", value=2500.0, step=10.0)
    quantity    = st.number_input("Quantity (Shares)", value=10, step=1)
    beta        = st.slider("Beta (Market Sensitivity)", 0.0, 3.0, default_beta, 0.1,
                    help="Beta=1: moves with Nifty | >1: more volatile | <1: less volatile")
    st.caption(f"💡 Default beta for {selected_co}: **{default_beta}**")

st.markdown("---")

# =========================================================
# SECTION 5: IMPACT ANALYSIS
# =========================================================
st.header("📉 Impact Analysis — Actual vs Assumed")

def calc_impact(nifty_pct, sp, qty, b):
    spct  = nifty_pct * b
    pchg  = sp * (spct / 100)
    nsp   = sp + pchg
    pl    = pchg * qty
    return spct, pchg, nsp, sp*qty, nsp*qty, pl

if nifty_live_ok:
    a_spct,a_pchg,a_nprice,a_oval,a_nval,a_pl = calc_impact(pct_change, stock_price, quantity, beta)
s_spct,s_pchg,s_nprice,s_oval,s_nval,s_pl     = calc_impact(assumed_pct, stock_price, quantity, beta)

col_a, col_s = st.columns(2)
with col_a:
    st.markdown("### 🟢 Based on Actual Nifty")
    if nifty_live_ok:
        st.metric("Stock % Change", f"{a_spct:+.2f}%")
        st.metric("New Stock Price", f"₹{a_nprice:,.2f}", delta=f"₹{a_pchg:+.2f}")
        st.metric("Portfolio P&L",   f"₹{a_pl:+,.2f}")
        st.success(f"✅ GAIN ₹{a_pl:,.2f}") if a_pl>0 else (st.error(f"❌ LOSS ₹{abs(a_pl):,.2f}") if a_pl<0 else st.info("⚖️ No Change"))
    else:
        st.warning("Live data unavailable.")

with col_s:
    st.markdown("### 🟡 Based on Assumed Nifty")
    st.metric("Stock % Change", f"{s_spct:+.2f}%")
    st.metric("New Stock Price", f"₹{s_nprice:,.2f}", delta=f"₹{s_pchg:+.2f}")
    st.metric("Portfolio P&L",   f"₹{s_pl:+,.2f}")
    st.success(f"✅ GAIN ₹{s_pl:,.2f}") if s_pl>0 else (st.error(f"❌ LOSS ₹{abs(s_pl):,.2f}") if s_pl<0 else st.info("⚖️ No Change"))

# Sensitivity Table
st.markdown("#### 📋 Sensitivity Table")
rows = []
for pts in [-500,-300,-200,-100,0,100,200,300,500]:
    p    = (pts / assumed_base) * 100
    sp_  = p * beta
    pchg = stock_price * (sp_ / 100)
    rows.append({
        "Nifty Chg (pts)": f"{pts:+}",
        "Nifty %":         f"{p:+.2f}%",
        "Stock %":         f"{sp_:+.2f}%",
        "New Price":       f"₹{stock_price+pchg:,.2f}",
        "P&L (₹)":        f"₹{pchg*quantity:+,.2f}"
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.markdown("---")

# =========================================================
# SECTION 6: LIVE INDIVIDUAL STOCK CHART
# =========================================================
st.header("🔍 Live Stock Chart (Any NSE Stock)")

col_sym, col_per = st.columns([2,1])
with col_sym:
    sym_in = st.text_input("NSE Symbol (e.g., RELIANCE, HDFCBANK, TCS)", value="RELIANCE")
with col_per:
    per_ch = st.selectbox("Period", ["1wk","1mo","3mo","6mo","1y"], index=1)

if st.button("🔎 Fetch Stock Data"):
    try:
        sh = yf.Ticker(f"{sym_in.strip().upper()}.NS").history(period=per_ch)
        if sh.empty:
            st.error("No data. Check symbol (use caps: RELIANCE, HDFCBANK).")
        else:
            lp,pp = sh['Close'].iloc[-1], sh['Close'].iloc[-2]
            chg   = lp - pp; pct = (chg/pp)*100
            c1,c2,c3 = st.columns(3)
            c1.metric("Current Price", f"₹{lp:,.2f}")
            c2.metric("Change",        f"₹{chg:+.2f}")
            c3.metric("% Change",      f"{pct:+.2f}%")
            fig_s = go.Figure()
            fig_s.add_trace(go.Candlestick(x=sh.index, open=sh['Open'], high=sh['High'],
                low=sh['Low'], close=sh['Close'], name=sym_in.upper(),
                increasing_line_color="#00c853", decreasing_line_color="#ff1744"))
            fig_s.update_layout(title=f"{sym_in.upper()} — Price Chart",
                template="plotly_dark", height=400)
            st.plotly_chart(fig_s, use_container_width=True)
    except Exception as ex:
        st.error(f"Error: {ex}")

st.markdown("---")
st.markdown("<center>Built with ❤️ using Streamlit | Data: Yahoo Finance | All 50 Nifty Companies Included</center>", unsafe_allow_html=True)
