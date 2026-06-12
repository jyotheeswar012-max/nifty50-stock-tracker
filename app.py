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
# ALL 50 NIFTY COMPANIES
# =========================================================
NIFTY50 = [
    {"symbol":"RELIANCE.NS",   "name":"Reliance Industries",    "sector":"Energy",             "beta":0.90},
    {"symbol":"HDFCBANK.NS",   "name":"HDFC Bank",              "sector":"Financial Services", "beta":1.10},
    {"symbol":"ICICIBANK.NS",  "name":"ICICI Bank",             "sector":"Financial Services", "beta":1.20},
    {"symbol":"INFY.NS",       "name":"Infosys",                "sector":"IT",                 "beta":0.75},
    {"symbol":"TCS.NS",        "name":"TCS",                    "sector":"IT",                 "beta":0.70},
    {"symbol":"BHARTIARTL.NS", "name":"Bharti Airtel",          "sector":"Telecom",            "beta":0.85},
    {"symbol":"ITC.NS",        "name":"ITC",                    "sector":"FMCG",               "beta":0.65},
    {"symbol":"KOTAKBANK.NS",  "name":"Kotak Mahindra Bank",    "sector":"Financial Services", "beta":1.05},
    {"symbol":"LT.NS",         "name":"Larsen & Toubro",        "sector":"Construction",       "beta":1.10},
    {"symbol":"HCLTECH.NS",    "name":"HCL Technologies",       "sector":"IT",                 "beta":0.80},
    {"symbol":"AXISBANK.NS",   "name":"Axis Bank",              "sector":"Financial Services", "beta":1.30},
    {"symbol":"SBIN.NS",       "name":"State Bank of India",    "sector":"Financial Services", "beta":1.35},
    {"symbol":"BAJFINANCE.NS", "name":"Bajaj Finance",          "sector":"Financial Services", "beta":1.40},
    {"symbol":"WIPRO.NS",      "name":"Wipro",                  "sector":"IT",                 "beta":0.72},
    {"symbol":"ASIANPAINT.NS", "name":"Asian Paints",           "sector":"Consumer Goods",     "beta":0.60},
    {"symbol":"MARUTI.NS",     "name":"Maruti Suzuki",          "sector":"Automobile",         "beta":0.95},
    {"symbol":"SUNPHARMA.NS",  "name":"Sun Pharmaceutical",     "sector":"Pharma",             "beta":0.70},
    {"symbol":"TITAN.NS",      "name":"Titan Company",          "sector":"Consumer Goods",     "beta":0.90},
    {"symbol":"ULTRACEMCO.NS", "name":"UltraTech Cement",       "sector":"Cement",             "beta":0.85},
    {"symbol":"ONGC.NS",       "name":"ONGC",                   "sector":"Energy",             "beta":1.00},
    {"symbol":"NTPC.NS",       "name":"NTPC",                   "sector":"Power",              "beta":0.80},
    {"symbol":"POWERGRID.NS",  "name":"Power Grid Corp",        "sector":"Power",              "beta":0.75},
    {"symbol":"MMTC.NS",       "name":"Mahindra & Mahindra",    "sector":"Automobile",         "beta":1.05},
    {"symbol":"TATAMOTORS.NS", "name":"Tata Motors",            "sector":"Automobile",         "beta":1.45},
    {"symbol":"TATASTEEL.NS",  "name":"Tata Steel",             "sector":"Metals",             "beta":1.50},
    {"symbol":"JSWSTEEL.NS",   "name":"JSW Steel",              "sector":"Metals",             "beta":1.40},
    {"symbol":"HINDALCO.NS",   "name":"Hindalco Industries",    "sector":"Metals",             "beta":1.35},
    {"symbol":"ADANIENT.NS",   "name":"Adani Enterprises",      "sector":"Conglomerate",       "beta":1.60},
    {"symbol":"ADANIPORTS.NS", "name":"Adani Ports",            "sector":"Infrastructure",     "beta":1.20},
    {"symbol":"BAJAJFINSV.NS", "name":"Bajaj Finserv",          "sector":"Financial Services", "beta":1.25},
    {"symbol":"BAJAJAUTO.NS",  "name":"Bajaj Auto",             "sector":"Automobile",         "beta":0.90},
    {"symbol":"HEROMOTOCO.NS", "name":"Hero MotoCorp",          "sector":"Automobile",         "beta":0.85},
    {"symbol":"CIPLA.NS",      "name":"Cipla",                  "sector":"Pharma",             "beta":0.65},
    {"symbol":"DRREDDY.NS",    "name":"Dr. Reddy's Labs",       "sector":"Pharma",             "beta":0.60},
    {"symbol":"DIVISLAB.NS",   "name":"Divi's Laboratories",    "sector":"Pharma",             "beta":0.70},
    {"symbol":"EICHERMOT.NS",  "name":"Eicher Motors",          "sector":"Automobile",         "beta":0.95},
    {"symbol":"GRASIM.NS",     "name":"Grasim Industries",      "sector":"Cement",             "beta":0.90},
    {"symbol":"HDFCLIFE.NS",   "name":"HDFC Life Insurance",    "sector":"Financial Services", "beta":0.95},
    {"symbol":"SBILIFE.NS",    "name":"SBI Life Insurance",     "sector":"Financial Services", "beta":0.90},
    {"symbol":"INDUSINDBK.NS", "name":"IndusInd Bank",          "sector":"Financial Services", "beta":1.45},
    {"symbol":"TATACONSUM.NS", "name":"Tata Consumer Products", "sector":"FMCG",               "beta":0.75},
    {"symbol":"BRITANNIA.NS",  "name":"Britannia Industries",   "sector":"FMCG",               "beta":0.60},
    {"symbol":"NESTLEIND.NS",  "name":"Nestle India",           "sector":"FMCG",               "beta":0.55},
    {"symbol":"HINDUNILVR.NS", "name":"Hindustan Unilever",     "sector":"FMCG",               "beta":0.58},
    {"symbol":"COALINDIA.NS",  "name":"Coal India",             "sector":"Energy",             "beta":0.85},
    {"symbol":"BPCL.NS",       "name":"BPCL",                   "sector":"Energy",             "beta":1.10},
    {"symbol":"TECHM.NS",      "name":"Tech Mahindra",          "sector":"IT",                 "beta":0.85},
    {"symbol":"LTF.NS",        "name":"L&T Finance",            "sector":"Financial Services", "beta":1.30},
    {"symbol":"SHRIRAMFIN.NS", "name":"Shriram Finance",        "sector":"Financial Services", "beta":1.20},
    {"symbol":"BEL.NS",        "name":"Bharat Electronics",     "sector":"Defence",            "beta":1.15},
]

nifty50_df = pd.DataFrame(NIFTY50)
sectors    = ["All"] + sorted(nifty50_df["sector"].unique().tolist())

# =========================================================
# HELPERS
# =========================================================
def safe_float(val, default=0.0):
    """Safely convert a value to float, returning default on failure."""
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default

def calc_impact(nifty_pct, sp, qty, b):
    """Calculate stock impact from index movement."""
    spct  = nifty_pct * b
    pchg  = sp * (spct / 100)
    nsp   = sp + pchg
    pl    = pchg * qty
    return spct, pchg, nsp, sp * qty, nsp * qty, pl

# =========================================================
# TITLE
# =========================================================
st.title("📈 Nifty 50 Stock Tracker")
st.markdown("Track **all 50 Nifty companies** — live prices, heatmap, gainers/losers & P&L calculator.")
st.markdown("---")

# =========================================================
# SECTION 1: LIVE NIFTY 50 INDEX
# =========================================================
st.header("🟢 Live Nifty 50 Index")
st.markdown('<span class="tag-actual">LIVE DATA</span> &nbsp; Real-time from Yahoo Finance / NSE', unsafe_allow_html=True)
st.markdown("")

@st.cache_data(ttl=300)
def get_nifty_data(period="3mo"):
    try:
        nifty = yf.Ticker("^NSEI")
        hist  = nifty.history(period=period)
        return hist if not hist.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

nifty_live_ok = False
current_price  = 22500.0
pct_change     = 0.0
change         = 0.0

hist = get_nifty_data()

if not hist.empty and len(hist) >= 2:
    try:
        current_price = safe_float(hist["Close"].iloc[-1], 22500.0)
        prev_price    = safe_float(hist["Close"].iloc[-2], current_price)
        change        = current_price - prev_price
        pct_change    = (change / prev_price * 100) if prev_price != 0 else 0.0
        nifty_live_ok = True

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Current Value", f"₹{current_price:,.2f}")
        c2.metric("Points Change", f"{change:+.2f}")
        c3.metric("% Change",      f"{pct_change:+.2f}%")
        c4.metric("Period High",   f"₹{safe_float(hist['High'].max()):,.2f}")
        c5.metric("Period Low",    f"₹{safe_float(hist['Low'].min()):,.2f}")

        hist = hist.copy()
        hist["MA20"] = hist["Close"].rolling(20).mean()

        fig_idx = go.Figure()
        fig_idx.add_trace(go.Candlestick(
            x=hist.index,
            open=hist["Open"], high=hist["High"],
            low=hist["Low"],   close=hist["Close"],
            name="Nifty 50",
            increasing_line_color="#00c853",
            decreasing_line_color="#ff1744"
        ))
        fig_idx.add_trace(go.Scatter(
            x=hist.index, y=hist["MA20"], mode="lines",
            name="20-Day MA", line=dict(color="#ffd600", width=1.5, dash="dot")
        ))
        fig_idx.update_layout(
            title="Nifty 50 — Last 3 Months", template="plotly_dark",
            height=420, xaxis_title="Date", yaxis_title="Index Value",
            xaxis_rangeslider_visible=False
        )
        st.plotly_chart(fig_idx, use_container_width=True)

        hist["Daily_Return_%"] = hist["Close"].pct_change() * 100
        ret_df = hist.dropna(subset=["Daily_Return_%"]).copy()
        if not ret_df.empty:
            fig_ret = px.bar(
                ret_df, x=ret_df.index, y="Daily_Return_%",
                color="Daily_Return_%",
                color_continuous_scale=["#ff1744", "#ffd600", "#00c853"],
                title="Daily Returns (%)", template="plotly_dark", height=280
            )
            st.plotly_chart(fig_ret, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ Error rendering index chart: {e}")
        nifty_live_ok = False
else:
    st.warning("⚠️ Could not fetch live Nifty 50 data. Showing fallback values.")

st.markdown("---")

# =========================================================
# SECTION 2: ALL 50 COMPANIES — Live Prices
# =========================================================
st.header("🏢 All 50 Nifty Companies — Live Data")
st.markdown('<span class="tag-actual">LIVE DATA</span>', unsafe_allow_html=True)
st.markdown("")

col_filter, col_sort = st.columns([2, 1])
with col_filter:
    sector_filter = st.selectbox("Filter by Sector", sectors)
with col_sort:
    sort_by = st.selectbox("Sort by", ["Name", "Price ↑", "Price ↓", "Change % ↑", "Change % ↓"])

@st.cache_data(ttl=300)
def fetch_all_nifty50():
    symbols = [s["symbol"] for s in NIFTY50]
    try:
        data = yf.download(
            symbols, period="5d",
            auto_adjust=True, progress=False,
            group_by="ticker"
        )
        return data
    except Exception:
        return pd.DataFrame()

def extract_close(raw, sym):
    """Safely extract Close series for a symbol from yf.download output."""
    try:
        # group_by='ticker' → raw[sym]['Close']
        if isinstance(raw.columns, pd.MultiIndex):
            if sym in raw.columns.get_level_values(0):
                s = raw[sym]["Close"].dropna()
            elif "Close" in raw.columns.get_level_values(0):
                # flat multi-index with (field, ticker)
                s = raw["Close"][sym].dropna()
            else:
                return None, None
        else:
            s = raw["Close"].dropna() if "Close" in raw.columns else None
            if s is None:
                return None, None
        if len(s) >= 2:
            return safe_float(s.iloc[-1]), safe_float(s.iloc[-2])
        elif len(s) == 1:
            return safe_float(s.iloc[-1]), None
    except Exception:
        pass
    return None, None

fetch_ok = False
all_df   = pd.DataFrame()

with st.spinner("⏳ Fetching live prices for all 50 stocks..."):
    raw = fetch_all_nifty50()
    rows = []
    for s in NIFTY50:
        sym  = s["symbol"]
        curr, prev = None, None
        chg,  pct  = None, None

        if not raw.empty:
            curr, prev = extract_close(raw, sym)
            if curr is not None and prev is not None and prev != 0:
                chg = curr - prev
                pct = (chg / prev) * 100

        rows.append({
            "Symbol":     sym.replace(".NS", ""),
            "Company":    s["name"],
            "Sector":     s["sector"],
            "Beta":       s["beta"],
            "Price (₹)":  round(curr, 2) if curr is not None else "N/A",
            "Change (₹)": round(chg, 2)  if chg  is not None else "N/A",
            "Change (%)": round(pct, 2)  if pct  is not None else "N/A",
            "_curr":      curr,
            "_pct":       pct,
        })

    if rows:
        all_df   = pd.DataFrame(rows)
        fetch_ok = True
    else:
        all_df = nifty50_df.copy()
        all_df.rename(columns={"symbol":"Symbol","name":"Company","sector":"Sector","beta":"Beta"}, inplace=True)
        all_df["Price (₹)"] = "N/A"
        all_df["Change (₹)"] = "N/A"
        all_df["Change (%)"] = "N/A"
        all_df["_curr"] = None
        all_df["_pct"]  = None
        st.warning("⚠️ Could not fetch individual stock prices. Showing company list only.")

# Filter
display_df = all_df.copy() if sector_filter == "All" else all_df[all_df["Sector"] == sector_filter].copy()

# Safe numeric sort
numeric_curr = pd.to_numeric(display_df["_curr"], errors="coerce")
numeric_pct  = pd.to_numeric(display_df["_pct"],  errors="coerce")

if sort_by == "Price ↑":
    display_df = display_df.iloc[numeric_curr.argsort()]
elif sort_by == "Price ↓":
    display_df = display_df.iloc[numeric_curr.argsort()[::-1]]
elif sort_by == "Change % ↑":
    display_df = display_df.iloc[numeric_pct.argsort()]
elif sort_by == "Change % ↓":
    display_df = display_df.iloc[numeric_pct.argsort()[::-1]]
else:
    display_df = display_df.sort_values("Company")

st.dataframe(
    display_df[["Symbol", "Company", "Sector", "Beta", "Price (₹)", "Change (₹)", "Change (%)"]],
    use_container_width=True, hide_index=True
)
st.caption(f"Showing {len(display_df)} of 50 companies")

st.markdown("---")

# =========================================================
# SECTION 3: TOP GAINERS & LOSERS + HEATMAP
# =========================================================
st.header("🏆 Top Gainers & Losers")

if fetch_ok:
    valid_df = all_df.copy()
    valid_df["_pct_num"] = pd.to_numeric(valid_df["_pct"], errors="coerce")
    valid_df = valid_df.dropna(subset=["_pct_num"])

    if not valid_df.empty:
        gainers = valid_df.nlargest(5, "_pct_num")[["Company", "Sector", "Price (₹)", "Change (%)"]]
        losers  = valid_df.nsmallest(5, "_pct_num")[["Company", "Sector", "Price (₹)", "Change (%)"]]

        cg, cl = st.columns(2)
        with cg:
            st.markdown("### 🟢 Top 5 Gainers")
            st.dataframe(gainers, use_container_width=True, hide_index=True)
        with cl:
            st.markdown("### 🔴 Top 5 Losers")
            st.dataframe(losers, use_container_width=True, hide_index=True)

        # Treemap heatmap — safe values (must be positive)
        valid_df["_heat_val"] = valid_df["_pct_num"].abs().clip(lower=0.01)
        try:
            fig_heat = px.treemap(
                valid_df,
                path=["Sector", "Company"],
                values="_heat_val",
                color="_pct_num",
                color_continuous_scale=["#ff1744", "#ffd600", "#00c853"],
                color_continuous_midpoint=0,
                title="📊 Nifty 50 Heatmap — % Change by Sector & Stock",
            )
            fig_heat.update_layout(template="plotly_dark", height=500)
            st.plotly_chart(fig_heat, use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ Could not render heatmap: {e}")
    else:
        st.info("Not enough live data to show gainers/losers today.")
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
    assumed_base   = st.number_input("Assumed Base Nifty Value", value=float(round(current_price, 2)), step=50.0, min_value=1.0)
    assumed_change = st.number_input("Assumed Change in Points (+ gain / − loss)", value=-200.0, step=10.0)
    assumed_new    = assumed_base + assumed_change
    assumed_pct    = (assumed_change / assumed_base) * 100 if assumed_base != 0 else 0.0
    st.info(f"📌 Assumed % Change: **{assumed_pct:+.2f}%** → New Value: **{assumed_new:,.2f}**")

    if nifty_live_ok:
        compare_df = pd.DataFrame({
            "Metric":     ["Base Value", "Change (pts)", "Change (%)", "New Value"],
            "🟢 Actual":  [f"₹{current_price:,.2f}", f"{change:+.2f}", f"{pct_change:+.2f}%", f"₹{current_price:,.2f}"],
            "🟡 Assumed": [f"₹{assumed_base:,.2f}",  f"{assumed_change:+.2f}", f"{assumed_pct:+.2f}%", f"₹{assumed_new:,.2f}"]
        })
        st.dataframe(compare_df, use_container_width=True, hide_index=True)

with col_r:
    st.subheader("💼 Your Stock Details")
    company_names = ["-- Custom --"] + nifty50_df["name"].tolist()
    selected_co   = st.selectbox("Select Nifty 50 Company (or Custom)", company_names)

    if selected_co != "-- Custom --":
        match        = nifty50_df[nifty50_df["name"] == selected_co]
        default_beta = float(match["beta"].iloc[0]) if not match.empty else 1.0
        stock_name   = selected_co
        beta_hint    = f"💡 Default beta for **{selected_co}**: **{default_beta}**"
    else:
        default_beta = 1.0
        stock_name   = st.text_input("Enter Stock Name", value="My Stock")
        beta_hint    = "💡 Enter Beta manually below"

    stock_price = st.number_input("Stock Current Price (₹)", value=100.0, min_value=0.01, step=10.0)
    quantity    = st.number_input("Quantity (Shares)", value=10, min_value=1, step=1)
    beta        = st.slider(
        "Beta (Market Sensitivity)", 0.0, 3.0,
        value=float(round(default_beta, 1)), step=0.1,
        help="Beta=1: moves with Nifty | >1: more volatile | <1: less volatile"
    )
    st.caption(beta_hint)

st.markdown("---")

# =========================================================
# SECTION 5: IMPACT ANALYSIS
# =========================================================
st.header("📉 Impact Analysis — Actual vs Assumed")

col_a, col_s = st.columns(2)

with col_a:
    st.markdown("### 🟢 Based on Actual Nifty")
    if nifty_live_ok:
        a_spct, a_pchg, a_nprice, a_oval, a_nval, a_pl = calc_impact(pct_change, stock_price, quantity, beta)
        st.metric("Stock % Change",  f"{a_spct:+.2f}%")
        st.metric("New Stock Price", f"₹{a_nprice:,.2f}", delta=f"₹{a_pchg:+.2f}")
        st.metric("Portfolio P&L",   f"₹{a_pl:+,.2f}")
        if a_pl > 0:   st.success(f"✅ GAIN ₹{a_pl:,.2f}")
        elif a_pl < 0: st.error(f"❌ LOSS ₹{abs(a_pl):,.2f}")
        else:          st.info("⚖️ No Change")
    else:
        st.warning("Live Nifty data unavailable. Use assumed scenario →")

with col_s:
    st.markdown("### 🟡 Based on Assumed Nifty")
    s_spct, s_pchg, s_nprice, s_oval, s_nval, s_pl = calc_impact(assumed_pct, stock_price, quantity, beta)
    st.metric("Stock % Change",  f"{s_spct:+.2f}%")
    st.metric("New Stock Price", f"₹{s_nprice:,.2f}", delta=f"₹{s_pchg:+.2f}")
    st.metric("Portfolio P&L",   f"₹{s_pl:+,.2f}")
    if s_pl > 0:   st.success(f"✅ GAIN ₹{s_pl:,.2f}")
    elif s_pl < 0: st.error(f"❌ LOSS ₹{abs(s_pl):,.2f}")
    else:          st.info("⚖️ No Change")

# P&L Bar chart (actual vs assumed)
if nifty_live_ok:
    try:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=["Actual P&L", "Assumed P&L"],
            y=[a_pl, s_pl],
            marker_color=["#00c853" if a_pl >= 0 else "#ff1744",
                          "#00c853" if s_pl >= 0 else "#ff1744"],
            text=[f"₹{a_pl:+,.2f}", f"₹{s_pl:+,.2f}"],
            textposition="outside"
        ))
        fig_bar.update_layout(
            title=f"Actual vs Assumed P&L — {stock_name} ({quantity} shares)",
            yaxis_title="Profit / Loss (₹)", template="plotly_dark", height=350
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ Could not render P&L chart: {e}")

# Sensitivity Table
st.markdown("#### 📋 Sensitivity Table — What if Nifty moves by...")
sen_rows = []
for pts in [-500, -300, -200, -100, 0, 100, 200, 300, 500]:
    p     = (pts / assumed_base * 100) if assumed_base != 0 else 0.0
    sp_   = p * beta
    pchg  = stock_price * (sp_ / 100)
    pl_s  = pchg * quantity
    sen_rows.append({
        "Nifty Chg (pts)": f"{pts:+}",
        "Nifty %":         f"{p:+.2f}%",
        "Stock %":         f"{sp_:+.2f}%",
        "New Price":       f"₹{stock_price + pchg:,.2f}",
        "P&L (₹)":        f"₹{pl_s:+,.2f}"
    })
st.dataframe(pd.DataFrame(sen_rows), use_container_width=True, hide_index=True)

with st.expander("📘 Formula Reference"):
    st.markdown(f"""
    | Formula | Expression |
    |---------|------------|
    | Nifty % Change | `points_change ÷ base_value × 100` |
    | Stock % Change | `Nifty % × Beta ({beta})` |
    | New Stock Price | `Current Price × (1 + Stock% ÷ 100)` |
    | P&L | `(New Price − Old Price) × Quantity` |

    > ⚠️ **Disclaimer**: Estimates use Beta correlation only. Actual movement depends on company news, sector trends, and global cues.
    """)

st.markdown("---")

# =========================================================
# SECTION 6: LIVE INDIVIDUAL STOCK CHART
# =========================================================
st.header("🔍 Live Stock Chart (Any NSE Stock)")

col_sym, col_per = st.columns([2, 1])
with col_sym:
    sym_in = st.text_input("NSE Symbol (e.g., RELIANCE, HDFCBANK, TCS)", value="RELIANCE")
with col_per:
    per_ch = st.selectbox("Period", ["1wk", "1mo", "3mo", "6mo", "1y"], index=1)

if st.button("🔎 Fetch Stock Data"):
    clean_sym = sym_in.strip().upper()
    if not clean_sym:
        st.error("Please enter a valid symbol.")
    else:
        with st.spinner(f"Fetching data for {clean_sym}..."):
            try:
                ticker = f"{clean_sym}.NS"
                sh = yf.Ticker(ticker).history(period=per_ch)
                if sh is None or sh.empty:
                    st.error(f"No data found for **{clean_sym}**. Check symbol — use caps like RELIANCE, HDFCBANK, TCS.")
                elif len(sh) < 2:
                    st.warning("Not enough data points to calculate change.")
                    st.metric("Latest Price", f"₹{safe_float(sh['Close'].iloc[-1]):,.2f}")
                else:
                    lp  = safe_float(sh["Close"].iloc[-1])
                    pp  = safe_float(sh["Close"].iloc[-2])
                    chg = lp - pp
                    pct = (chg / pp * 100) if pp != 0 else 0.0

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Current Price", f"₹{lp:,.2f}")
                    c2.metric("Change",        f"₹{chg:+.2f}")
                    c3.metric("% Change",      f"{pct:+.2f}%")

                    fig_s = go.Figure()
                    fig_s.add_trace(go.Candlestick(
                        x=sh.index,
                        open=sh["Open"], high=sh["High"],
                        low=sh["Low"],   close=sh["Close"],
                        name=clean_sym,
                        increasing_line_color="#00c853",
                        decreasing_line_color="#ff1744"
                    ))
                    fig_s.update_layout(
                        title=f"{clean_sym} — Price Chart",
                        template="plotly_dark", height=400,
                        xaxis_rangeslider_visible=False
                    )
                    st.plotly_chart(fig_s, use_container_width=True)
            except Exception as ex:
                st.error(f"❌ Error fetching **{clean_sym}**: {str(ex)}")
                st.info("💡 Tips: Use NSE symbols in CAPS (e.g., RELIANCE, HDFCBANK, INFY, TCS)")

st.markdown("---")
st.markdown("<center>Built with ❤️ using Streamlit | Data: Yahoo Finance (yfinance) | All 50 Nifty Companies</center>", unsafe_allow_html=True)
