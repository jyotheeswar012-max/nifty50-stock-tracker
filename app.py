import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import pytz

st.set_page_config(page_title="NSE & Nifty 50 Tracker", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .tag-actual  { background:#00c853;color:black;padding:2px 10px;border-radius:20px;font-size:13px;font-weight:bold; }
    .tag-assumed { background:#ffd600;color:black;padding:2px 10px;border-radius:20px;font-size:13px;font-weight:bold; }
    .tag-nse     { background:#1565c0;color:white;padding:2px 10px;border-radius:20px;font-size:13px;font-weight:bold; }
    .tag-open    { background:#00c853;color:black;padding:3px 12px;border-radius:20px;font-size:14px;font-weight:bold; }
    .tag-closed  { background:#ff1744;color:white;padding:3px 12px;border-radius:20px;font-size:14px;font-weight:bold; }
    .stMetric label { color:#9e9e9e !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# HELPERS
# =========================================================
def safe_float(val, default=0.0):
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default

def calc_impact(nifty_pct, sp, qty, b):
    spct = nifty_pct * b
    pchg = sp * (spct / 100)
    nsp  = sp + pchg
    pl   = pchg * qty
    return spct, pchg, nsp, sp * qty, nsp * qty, pl

def is_nse_open():
    """Check if NSE market is currently open (Mon-Fri 9:15 AM - 3:30 PM IST)."""
    try:
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
        if now.weekday() >= 5:
            return False, "Weekend"
        market_open  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        if market_open <= now <= market_close:
            return True, "Open"
        elif now < market_open:
            return False, f"Opens at 9:15 AM IST"
        else:
            return False, "Closed (Today's session ended)"
    except Exception:
        return False, "Unknown"

@st.cache_data(ttl=300)
def fetch_ticker(symbol, period="3mo"):
    try:
        t = yf.Ticker(symbol)
        h = t.history(period=period)
        return h if not h.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def index_metrics(hist, label):
    """Render 5 metric cards for an index."""
    if hist.empty or len(hist) < 2:
        st.warning(f"⚠️ No data for {label}")
        return None, None, None
    curr  = safe_float(hist["Close"].iloc[-1])
    prev  = safe_float(hist["Close"].iloc[-2], curr)
    chg   = curr - prev
    pct   = (chg / prev * 100) if prev != 0 else 0.0
    hi    = safe_float(hist["High"].max())
    lo    = safe_float(hist["Low"].min())
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric(f"{label} Value", f"₹{curr:,.2f}")
    c2.metric("Points Change",  f"{chg:+.2f}")
    c3.metric("% Change",       f"{pct:+.2f}%")
    c4.metric("Period High",    f"₹{hi:,.2f}")
    c5.metric("Period Low",     f"₹{lo:,.2f}")
    return curr, chg, pct

# =========================================================
# NSE INDICES CONFIG
# =========================================================
NSE_INDICES = [
    {"symbol": "^NSEI",   "name": "Nifty 50",         "color": "#00e5ff"},
    {"symbol": "^NSEBANK","name": "Nifty Bank",       "color": "#ffd600"},
    {"symbol": "^CNXIT",  "name": "Nifty IT",         "color": "#69f0ae"},
    {"symbol": "^CNXAUTO","name": "Nifty Auto",       "color": "#ff6d00"},
    {"symbol": "^CNXPHARMA","name":"Nifty Pharma",    "color": "#ea80fc"},
    {"symbol": "^CNXFMCG", "name": "Nifty FMCG",      "color": "#80d8ff"},
    {"symbol": "^CNXMETAL","name": "Nifty Metal",     "color": "#ff6e40"},
    {"symbol": "^CNXREALTY","name":"Nifty Realty",    "color": "#b9f6ca"},
]

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
    {"symbol":"MM.NS",         "name":"Mahindra & Mahindra",    "sector":"Automobile",         "beta":1.05},
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
# SIDEBAR NAVIGATION
# =========================================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/NSE_Logo.svg/200px-NSE_Logo.svg.png", width=120)
st.sidebar.title("📈 NSE & Nifty Tracker")
page = st.sidebar.radio("Navigate", [
    "🏦 NSE Market Overview",
    "📈 Nifty 50 Index",
    "🏢 All 50 Companies",
    "🏆 Gainers & Losers",
    "🧮 P&L Calculator",
    "🔍 Stock Chart Lookup",
])

ist = pytz.timezone("Asia/Kolkata")
st.sidebar.markdown(f"**🕒 IST Time:** {datetime.now(ist).strftime('%d %b %Y %I:%M %p')}")
market_open, market_status = is_nse_open()
if market_open:
    st.sidebar.markdown('<span class="tag-open">● MARKET OPEN</span>', unsafe_allow_html=True)
else:
    st.sidebar.markdown(f'<span class="tag-closed">● {market_status}</span>', unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.caption("📊 Data: Yahoo Finance (yfinance)")
st.sidebar.caption("⚠️ For educational use only")

# =========================================================
# PAGE 1: NSE MARKET OVERVIEW
# =========================================================
if page == "🏦 NSE Market Overview":
    st.title("🏦 NSE Market Overview")
    st.markdown('<span class="tag-nse">NSE INDIA</span> &nbsp; National Stock Exchange — All Key Indices', unsafe_allow_html=True)
    st.markdown("")

    # Market Status Banner
    if market_open:
        st.success("✅ NSE Market is currently **OPEN** | Trading Hours: Mon–Fri, 9:15 AM – 3:30 PM IST")
    else:
        st.error(f"❌ NSE Market is **CLOSED** — {market_status}")

    st.markdown("---")

    # All NSE Indices snapshot
    st.subheader("📊 NSE Indices Snapshot")
    idx_rows = []
    with st.spinner("Fetching all NSE indices..."):
        for idx in NSE_INDICES:
            h = fetch_ticker(idx["symbol"], period="5d")
            if not h.empty and len(h) >= 2:
                c  = safe_float(h["Close"].iloc[-1])
                p  = safe_float(h["Close"].iloc[-2], c)
                ch = c - p
                pt = (ch / p * 100) if p != 0 else 0.0
                hi = safe_float(h["High"].max())
                lo = safe_float(h["Low"].min())
                idx_rows.append({
                    "Index":          idx["name"],
                    "Current Value":  f"₹{c:,.2f}",
                    "Change (pts)":   f"{ch:+.2f}",
                    "Change (%)":     f"{pt:+.2f}%",
                    "Period High":    f"₹{hi:,.2f}",
                    "Period Low":     f"₹{lo:,.2f}",
                    "_pct":           pt,
                })
            else:
                idx_rows.append({
                    "Index": idx["name"], "Current Value": "N/A",
                    "Change (pts)": "N/A", "Change (%)": "N/A",
                    "Period High": "N/A", "Period Low": "N/A", "_pct": None
                })

    idx_df = pd.DataFrame(idx_rows)
    st.dataframe(idx_df.drop(columns=["_pct"]), use_container_width=True, hide_index=True)

    # NSE Indices Bar Chart
    valid_idx = idx_df.dropna(subset=["_pct"]).copy()
    if not valid_idx.empty:
        fig_idx_bar = px.bar(
            valid_idx, x="Index", y="_pct",
            color="_pct",
            color_continuous_scale=["#ff1744", "#ffd600", "#00c853"],
            color_continuous_midpoint=0,
            text="Change (%)",
            title="NSE Indices — % Change Today",
            template="plotly_dark", height=400,
            labels={"_pct": "% Change"}
        )
        fig_idx_bar.update_traces(textposition="outside")
        fig_idx_bar.update_layout(showlegend=False)
        st.plotly_chart(fig_idx_bar, use_container_width=True)

    st.markdown("---")

    # Multi-index line chart comparison
    st.subheader("📉 NSE Indices — 3-Month Trend Comparison")
    period_sel = st.selectbox("Select Period", ["1mo", "3mo", "6mo", "1y"], index=1)
    selected_indices = st.multiselect(
        "Select Indices to Compare",
        [i["name"] for i in NSE_INDICES],
        default=["Nifty 50", "Nifty Bank", "Nifty IT"]
    )

    if selected_indices:
        fig_multi = go.Figure()
        sym_map   = {i["name"]: i for i in NSE_INDICES}
        with st.spinner("Fetching index data..."):
            for name in selected_indices:
                meta = sym_map.get(name)
                if not meta:
                    continue
                h = fetch_ticker(meta["symbol"], period=period_sel)
                if h.empty or len(h) < 2:
                    continue
                # Normalize to 100 for comparison
                base = safe_float(h["Close"].iloc[0], 1)
                norm = (h["Close"] / base) * 100 if base != 0 else h["Close"]
                fig_multi.add_trace(go.Scatter(
                    x=h.index, y=norm,
                    mode="lines", name=name,
                    line=dict(color=meta["color"], width=2)
                ))
        fig_multi.update_layout(
            title="NSE Indices — Normalized Trend (Base = 100)",
            template="plotly_dark", height=450,
            xaxis_title="Date", yaxis_title="Normalized Value",
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )
        st.plotly_chart(fig_multi, use_container_width=True)

    st.markdown("---")

    # Advance / Decline
    st.subheader("📊 Nifty 50 — Advance / Decline Today")
    with st.spinner("Calculating advance/decline..."):
        symbols = [s["symbol"] for s in NIFTY50]
        try:
            raw_ad = yf.download(symbols, period="5d", auto_adjust=True,
                                 progress=False, group_by="ticker")
            advances = declines = unchanged = 0
            for s in NIFTY50:
                sym = s["symbol"]
                try:
                    if isinstance(raw_ad.columns, pd.MultiIndex):
                        lvl0 = raw_ad.columns.get_level_values(0)
                        if sym in lvl0:
                            cl = raw_ad[sym]["Close"].dropna()
                        elif "Close" in lvl0:
                            cl = raw_ad["Close"][sym].dropna()
                        else:
                            continue
                    else:
                        continue
                    if len(cl) >= 2:
                        diff = safe_float(cl.iloc[-1]) - safe_float(cl.iloc[-2])
                        if diff > 0:   advances  += 1
                        elif diff < 0: declines   += 1
                        else:          unchanged  += 1
                except Exception:
                    continue

            col_a, col_d, col_u = st.columns(3)
            col_a.metric("🟢 Advances",  advances)
            col_d.metric("🔴 Declines",  declines)
            col_u.metric("⚪ Unchanged", unchanged)

            if advances + declines > 0:
                fig_ad = go.Figure(go.Pie(
                    labels=["Advances", "Declines", "Unchanged"],
                    values=[advances, declines, unchanged],
                    marker_colors=["#00c853", "#ff1744", "#9e9e9e"],
                    hole=0.5
                ))
                fig_ad.update_layout(
                    title="Advance / Decline Ratio",
                    template="plotly_dark", height=300
                )
                st.plotly_chart(fig_ad, use_container_width=True)
        except Exception as ex:
            st.warning(f"⚠️ Could not compute advance/decline: {ex}")

# =========================================================
# PAGE 2: NIFTY 50 INDEX
# =========================================================
elif page == "📈 Nifty 50 Index":
    st.title("📈 Nifty 50 Index")
    st.markdown('<span class="tag-actual">LIVE DATA</span> &nbsp; Real-time NSE Nifty 50 Index', unsafe_allow_html=True)
    st.markdown("")

    period_n = st.selectbox("Select Period", ["1mo", "3mo", "6mo", "1y"], index=1)
    hist_n   = fetch_ticker("^NSEI", period=period_n)
    nifty_live_ok = False
    current_price = 22500.0; pct_change = 0.0; change = 0.0

    if not hist_n.empty and len(hist_n) >= 2:
        current_price, change, pct_change = index_metrics(hist_n, "Nifty 50")
        if current_price: nifty_live_ok = True

        hist_n = hist_n.copy()
        hist_n["MA20"] = hist_n["Close"].rolling(20).mean()
        hist_n["MA50"] = hist_n["Close"].rolling(50).mean()

        fig_n = go.Figure()
        fig_n.add_trace(go.Candlestick(
            x=hist_n.index, open=hist_n["Open"], high=hist_n["High"],
            low=hist_n["Low"], close=hist_n["Close"], name="Nifty 50",
            increasing_line_color="#00c853", decreasing_line_color="#ff1744"
        ))
        fig_n.add_trace(go.Scatter(x=hist_n.index, y=hist_n["MA20"],
            mode="lines", name="20-Day MA", line=dict(color="#ffd600", width=1.5, dash="dot")))
        fig_n.add_trace(go.Scatter(x=hist_n.index, y=hist_n["MA50"],
            mode="lines", name="50-Day MA", line=dict(color="#ea80fc", width=1.5, dash="dash")))
        fig_n.update_layout(
            title=f"Nifty 50 — {period_n}", template="plotly_dark",
            height=480, xaxis_rangeslider_visible=False
        )
        st.plotly_chart(fig_n, use_container_width=True)

        hist_n["Daily_Return_%"] = hist_n["Close"].pct_change() * 100
        ret_df = hist_n.dropna(subset=["Daily_Return_%"])
        if not ret_df.empty:
            fig_ret = px.bar(
                ret_df, x=ret_df.index, y="Daily_Return_%",
                color="Daily_Return_%",
                color_continuous_scale=["#ff1744", "#ffd600", "#00c853"],
                title="Daily Returns (%)", template="plotly_dark", height=280
            )
            st.plotly_chart(fig_ret, use_container_width=True)

        # Volume
        if "Volume" in hist_n.columns:
            vol_df = hist_n[hist_n["Volume"] > 0]
            if not vol_df.empty:
                fig_vol = px.bar(vol_df, x=vol_df.index, y="Volume",
                    title="Nifty 50 Volume", template="plotly_dark", height=250,
                    color_discrete_sequence=["#00e5ff"])
                st.plotly_chart(fig_vol, use_container_width=True)
    else:
        st.warning("⚠️ Could not fetch Nifty 50 data.")

# =========================================================
# PAGE 3: ALL 50 COMPANIES
# =========================================================
elif page == "🏢 All 50 Companies":
    st.title("🏢 All 50 Nifty Companies")
    st.markdown('<span class="tag-actual">LIVE DATA</span> &nbsp; All companies with live NSE prices', unsafe_allow_html=True)
    st.markdown("")

    col_f, col_s = st.columns([2, 1])
    with col_f: sector_filter = st.selectbox("Filter by Sector", sectors)
    with col_s: sort_by = st.selectbox("Sort by", ["Name","Price ↑","Price ↓","Change % ↑","Change % ↓"])

    @st.cache_data(ttl=300)
    def fetch_all():
        syms = [s["symbol"] for s in NIFTY50]
        try:
            return yf.download(syms, period="5d", auto_adjust=True,
                               progress=False, group_by="ticker")
        except Exception:
            return pd.DataFrame()

    def get_curr_prev(raw, sym):
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                lvl0 = raw.columns.get_level_values(0)
                s = raw[sym]["Close"].dropna() if sym in lvl0 else raw["Close"][sym].dropna()
            else:
                s = raw["Close"].dropna()
            if len(s) >= 2: return safe_float(s.iloc[-1]), safe_float(s.iloc[-2])
            if len(s) == 1: return safe_float(s.iloc[-1]), None
        except Exception: pass
        return None, None

    with st.spinner("⏳ Loading live prices..."):
        raw = fetch_all()
        rows = []
        for s in NIFTY50:
            curr, prev = get_curr_prev(raw, s["symbol"]) if not raw.empty else (None, None)
            chg = (curr - prev) if (curr and prev) else None
            pct = (chg / prev * 100) if (chg and prev and prev != 0) else None
            rows.append({
                "Symbol":     s["symbol"].replace(".NS",""),
                "Company":    s["name"],
                "Sector":     s["sector"],
                "Beta":       s["beta"],
                "Price (₹)":  round(curr,2) if curr else "N/A",
                "Change (₹)": round(chg,2)  if chg  else "N/A",
                "Change (%)": round(pct,2)  if pct  else "N/A",
                "_curr": curr, "_pct": pct,
            })
        all_df   = pd.DataFrame(rows)
        fetch_ok = True

    disp = all_df.copy() if sector_filter=="All" else all_df[all_df["Sector"]==sector_filter].copy()
    nc   = pd.to_numeric(disp["_curr"], errors="coerce")
    np_  = pd.to_numeric(disp["_pct"],  errors="coerce")
    if sort_by=="Price ↑":      disp = disp.iloc[nc.argsort()]
    elif sort_by=="Price ↓":    disp = disp.iloc[nc.argsort()[::-1]]
    elif sort_by=="Change % ↑": disp = disp.iloc[np_.argsort()]
    elif sort_by=="Change % ↓": disp = disp.iloc[np_.argsort()[::-1]]
    else: disp = disp.sort_values("Company")

    st.dataframe(disp[["Symbol","Company","Sector","Beta","Price (₹)","Change (₹)","Change (%)"]], use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(disp)} of 50 companies")

# =========================================================
# PAGE 4: GAINERS & LOSERS
# =========================================================
elif page == "🏆 Gainers & Losers":
    st.title("🏆 Top Gainers & Losers")
    st.markdown('<span class="tag-actual">LIVE DATA</span>', unsafe_allow_html=True)
    st.markdown("")

    @st.cache_data(ttl=300)
    def fetch_all_gl():
        syms = [s["symbol"] for s in NIFTY50]
        try:
            return yf.download(syms, period="5d", auto_adjust=True,
                               progress=False, group_by="ticker")
        except Exception: return pd.DataFrame()

    def get_cp(raw, sym):
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                lvl0 = raw.columns.get_level_values(0)
                s = raw[sym]["Close"].dropna() if sym in lvl0 else raw["Close"][sym].dropna()
            else:
                s = raw["Close"].dropna()
            if len(s) >= 2: return safe_float(s.iloc[-1]), safe_float(s.iloc[-2])
        except: pass
        return None, None

    with st.spinner("Fetching data..."):
        raw = fetch_all_gl()
        rows = []
        for s in NIFTY50:
            curr, prev = get_cp(raw, s["symbol"]) if not raw.empty else (None, None)
            chg = (curr - prev) if (curr and prev) else None
            pct = (chg / prev * 100) if (chg and prev and prev != 0) else None
            rows.append({"Company":s["name"],"Sector":s["sector"],
                         "Price (₹)":round(curr,2) if curr else "N/A",
                         "Change (%)": round(pct,2) if pct else "N/A",
                         "_pct": pct})
        gl_df = pd.DataFrame(rows)

    valid = gl_df.dropna(subset=["_pct"]).copy()
    if not valid.empty:
        top_n = st.slider("Show Top N", 3, 10, 5)
        gainers = valid.nlargest(top_n, "_pct")[["Company","Sector","Price (₹)","Change (%)"]]
        losers  = valid.nsmallest(top_n, "_pct")[["Company","Sector","Price (₹)","Change (%)"]]

        cg, cl = st.columns(2)
        with cg:
            st.markdown(f"### 🟢 Top {top_n} Gainers")
            st.dataframe(gainers, use_container_width=True, hide_index=True)
        with cl:
            st.markdown(f"### 🔴 Top {top_n} Losers")
            st.dataframe(losers, use_container_width=True, hide_index=True)

        # Heatmap
        valid["_heat"] = valid["_pct"].abs().clip(lower=0.01)
        valid["Sector2"] = valid["Sector"]
        try:
            fig_h = px.treemap(valid, path=["Sector2","Company"],
                values="_heat", color="_pct",
                color_continuous_scale=["#ff1744","#ffd600","#00c853"],
                color_continuous_midpoint=0,
                title="Nifty 50 Heatmap — % Change by Sector & Stock",
                hover_data={"Price (₹)":True,"Change (%)":True})
            fig_h.update_layout(template="plotly_dark", height=520)
            st.plotly_chart(fig_h, use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ Heatmap error: {e}")
    else:
        st.info("Not enough live data.")

# =========================================================
# PAGE 5: P&L CALCULATOR
# =========================================================
elif page == "🧮 P&L Calculator":
    st.title("🧮 Stock P&L Calculator")
    st.markdown('<span class="tag-assumed">SIMULATED</span> &nbsp; Actual vs Assumed Nifty impact on your stock', unsafe_allow_html=True)
    st.markdown("")

    # Fetch live Nifty for actual data
    hist_calc = fetch_ticker("^NSEI", period="5d")
    nifty_live_ok = False
    current_price = 22500.0; pct_change = 0.0; change = 0.0
    if not hist_calc.empty and len(hist_calc) >= 2:
        current_price = safe_float(hist_calc["Close"].iloc[-1], 22500.0)
        prev_p        = safe_float(hist_calc["Close"].iloc[-2], current_price)
        change        = current_price - prev_p
        pct_change    = (change / prev_p * 100) if prev_p != 0 else 0.0
        nifty_live_ok = True

    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("📊 Nifty Movement")
        assumed_base   = st.number_input("Base Nifty Value", value=float(round(current_price,2)), step=50.0, min_value=1.0)
        assumed_change = st.number_input("Change in Points (+ gain / − loss)", value=-200.0, step=10.0)
        assumed_new    = assumed_base + assumed_change
        assumed_pct    = (assumed_change / assumed_base * 100) if assumed_base != 0 else 0.0
        st.info(f"📌 Assumed % Change: **{assumed_pct:+.2f}%** → New Value: **{assumed_new:,.2f}**")

        if nifty_live_ok:
            st.dataframe(pd.DataFrame({
                "Metric":     ["Base Value","Change (pts)","Change (%)","New Value"],
                "🟢 Actual":  [f"₹{current_price:,.2f}",f"{change:+.2f}",f"{pct_change:+.2f}%",f"₹{current_price:,.2f}"],
                "🟡 Assumed": [f"₹{assumed_base:,.2f}",f"{assumed_change:+.2f}",f"{assumed_pct:+.2f}%",f"₹{assumed_new:,.2f}"]
            }), use_container_width=True, hide_index=True)

    with col_r:
        st.subheader("💼 Your Stock")
        company_names = ["-- Custom --"] + nifty50_df["name"].tolist()
        selected_co   = st.selectbox("Select Nifty 50 Company", company_names)
        if selected_co != "-- Custom --":
            match        = nifty50_df[nifty50_df["name"] == selected_co]
            default_beta = float(match["beta"].iloc[0]) if not match.empty else 1.0
            stock_name   = selected_co
        else:
            default_beta = 1.0
            stock_name   = st.text_input("Stock Name", value="My Stock")
        stock_price = st.number_input("Current Price (₹)", value=100.0, min_value=0.01, step=10.0)
        quantity    = st.number_input("Quantity", value=10, min_value=1, step=1)
        beta        = st.slider("Beta", 0.0, 3.0, float(round(default_beta,1)), 0.1)
        st.caption(f"💡 Beta for **{selected_co}**: **{default_beta}**")

    st.markdown("---")
    col_a, col_s = st.columns(2)
    with col_a:
        st.markdown("### 🟢 Actual Nifty Impact")
        if nifty_live_ok:
            a = calc_impact(pct_change, stock_price, quantity, beta)
            st.metric("Stock % Change",  f"{a[0]:+.2f}%")
            st.metric("New Stock Price", f"₹{a[2]:,.2f}", delta=f"₹{a[1]:+.2f}")
            st.metric("Portfolio P&L",   f"₹{a[5]:+,.2f}")
            st.success(f"✅ GAIN ₹{a[5]:,.2f}") if a[5]>0 else (st.error(f"❌ LOSS ₹{abs(a[5]):,.2f}") if a[5]<0 else st.info("⚖️ No Change"))
        else:
            st.warning("Live data unavailable.")
    with col_s:
        st.markdown("### 🟡 Assumed Nifty Impact")
        s = calc_impact(assumed_pct, stock_price, quantity, beta)
        st.metric("Stock % Change",  f"{s[0]:+.2f}%")
        st.metric("New Stock Price", f"₹{s[2]:,.2f}", delta=f"₹{s[1]:+.2f}")
        st.metric("Portfolio P&L",   f"₹{s[5]:+,.2f}")
        st.success(f"✅ GAIN ₹{s[5]:,.2f}") if s[5]>0 else (st.error(f"❌ LOSS ₹{abs(s[5]):,.2f}") if s[5]<0 else st.info("⚖️ No Change"))

    st.markdown("#### 📋 Sensitivity Table")
    sen = []
    for pts in [-500,-300,-200,-100,0,100,200,300,500]:
        p   = (pts / assumed_base * 100) if assumed_base != 0 else 0
        sp_ = p * beta
        pc  = stock_price * (sp_ / 100)
        sen.append({"Nifty Chg":f"{pts:+}","Nifty %":f"{p:+.2f}%","Stock %":f"{sp_:+.2f}%",
                    "New Price":f"₹{stock_price+pc:,.2f}","P&L (₹)":f"₹{pc*quantity:+,.2f}"})
    st.dataframe(pd.DataFrame(sen), use_container_width=True, hide_index=True)

# =========================================================
# PAGE 6: STOCK CHART LOOKUP
# =========================================================
elif page == "🔍 Stock Chart Lookup":
    st.title("🔍 NSE Stock Chart Lookup")
    st.markdown('<span class="tag-nse">NSE</span> &nbsp; Search any NSE listed stock by symbol', unsafe_allow_html=True)
    st.markdown("")

    # Quick pick from Nifty 50
    quick = st.selectbox("Quick Pick (Nifty 50)", ["-- Type manually below --"] + [f"{s['name']} ({s['symbol'].replace('.NS','')})" for s in NIFTY50])
    if quick != "-- Type manually below --":
        default_sym = quick.split("(")[-1].replace(")","").strip()
    else:
        default_sym = "RELIANCE"

    col_sym, col_per, col_type = st.columns([2,1,1])
    with col_sym:  sym_in  = st.text_input("NSE Symbol", value=default_sym)
    with col_per:  per_ch  = st.selectbox("Period", ["1wk","1mo","3mo","6mo","1y"], index=1)
    with col_type: ch_type = st.selectbox("Chart Type", ["Candlestick","Line","Area"])

    if st.button("🔎 Fetch & Plot"):
        clean = sym_in.strip().upper()
        if not clean:
            st.error("Enter a valid symbol.")
        else:
            with st.spinner(f"Fetching {clean}..."):
                try:
                    sh = yf.Ticker(f"{clean}.NS").history(period=per_ch)
                    if sh is None or sh.empty:
                        st.error(f"No data for **{clean}**. Try: RELIANCE, HDFCBANK, TCS, INFY")
                    elif len(sh) < 2:
                        st.warning("Not enough data.")
                    else:
                        lp  = safe_float(sh["Close"].iloc[-1])
                        pp  = safe_float(sh["Close"].iloc[-2])
                        chg = lp - pp
                        pct = (chg/pp*100) if pp!=0 else 0
                        wk_hi = safe_float(sh["High"].max())
                        wk_lo = safe_float(sh["Low"].min())

                        c1,c2,c3,c4,c5 = st.columns(5)
                        c1.metric("Price",         f"₹{lp:,.2f}")
                        c2.metric("Change",        f"₹{chg:+.2f}")
                        c3.metric("% Change",      f"{pct:+.2f}%")
                        c4.metric("Period High",   f"₹{wk_hi:,.2f}")
                        c5.metric("Period Low",    f"₹{wk_lo:,.2f}")

                        fig_s = go.Figure()
                        if ch_type == "Candlestick":
                            fig_s.add_trace(go.Candlestick(
                                x=sh.index, open=sh["Open"], high=sh["High"],
                                low=sh["Low"], close=sh["Close"], name=clean,
                                increasing_line_color="#00c853",
                                decreasing_line_color="#ff1744"
                            ))
                        elif ch_type == "Line":
                            fig_s.add_trace(go.Scatter(
                                x=sh.index, y=sh["Close"],
                                mode="lines", name=clean,
                                line=dict(color="#00e5ff", width=2)
                            ))
                        else:  # Area
                            fig_s.add_trace(go.Scatter(
                                x=sh.index, y=sh["Close"],
                                mode="lines", fill="tozeroy", name=clean,
                                line=dict(color="#00e5ff", width=2),
                                fillcolor="rgba(0,229,255,0.15)"
                            ))

                        # Add 20MA overlay
                        sh_copy = sh.copy()
                        sh_copy["MA20"] = sh_copy["Close"].rolling(20).mean()
                        fig_s.add_trace(go.Scatter(
                            x=sh_copy.index, y=sh_copy["MA20"],
                            mode="lines", name="20-Day MA",
                            line=dict(color="#ffd600", width=1.5, dash="dot")
                        ))
                        fig_s.update_layout(
                            title=f"{clean} — {ch_type} Chart ({per_ch})",
                            template="plotly_dark", height=460,
                            xaxis_rangeslider_visible=False
                        )
                        st.plotly_chart(fig_s, use_container_width=True)

                        # Volume
                        if "Volume" in sh.columns:
                            vol = sh[sh["Volume"] > 0]
                            if not vol.empty:
                                fig_v = px.bar(vol, x=vol.index, y="Volume",
                                    title=f"{clean} — Volume",
                                    template="plotly_dark", height=220,
                                    color_discrete_sequence=["#00e5ff"])
                                st.plotly_chart(fig_v, use_container_width=True)
                except Exception as ex:
                    st.error(f"❌ Error: {str(ex)}")
                    st.info("💡 Use NSE CAPS symbols: RELIANCE, HDFCBANK, INFY, TCS, SBIN")

st.markdown("---")
st.markdown("<center>Built with ❤️ using Streamlit &nbsp;|&nbsp; Data: NSE via Yahoo Finance &nbsp;|&nbsp; All 50 Nifty Companies</center>", unsafe_allow_html=True)
