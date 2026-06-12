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

# ============================================================
# CONSTANTS
# ============================================================
NSE_INDICES = [
    {"symbol": "^NSEI",      "name": "Nifty 50",    "color": "#00e5ff"},
    {"symbol": "^NSEBANK",   "name": "Nifty Bank",  "color": "#ffd600"},
    {"symbol": "^CNXIT",     "name": "Nifty IT",    "color": "#69f0ae"},
    {"symbol": "^CNXAUTO",   "name": "Nifty Auto",  "color": "#ff6d00"},
    {"symbol": "^CNXPHARMA", "name": "Nifty Pharma","color": "#ea80fc"},
    {"symbol": "^CNXFMCG",   "name": "Nifty FMCG",  "color": "#80d8ff"},
    {"symbol": "^CNXMETAL",  "name": "Nifty Metal", "color": "#ff6e40"},
    {"symbol": "^CNXREALTY", "name": "Nifty Realty","color": "#b9f6ca"},
]

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
    {"symbol":"M&M.NS",        "name":"Mahindra & Mahindra",    "sector":"Automobile",         "beta":1.05},
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

# ============================================================
# HELPERS
# ============================================================
def safe_float(val, default=0.0):
    """Convert val to float safely; return default on NaN/Inf/error."""
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default

def is_nse_open():
    try:
        ist  = pytz.timezone("Asia/Kolkata")
        now  = datetime.now(ist)
        if now.weekday() >= 5:
            return False, "Weekend — Market Closed"
        mo = now.replace(hour=9,  minute=15, second=0, microsecond=0)
        mc = now.replace(hour=15, minute=30, second=0, microsecond=0)
        if mo <= now <= mc:
            return True, "Open"
        elif now < mo:
            return False, "Pre-Market (Opens 9:15 AM IST)"
        else:
            return False, "Closed (Session ended at 3:30 PM)"
    except Exception:
        return False, "Unknown"

@st.cache_data(ttl=300)
def fetch_ticker(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """Fetch OHLCV history for a single symbol. Always returns a DataFrame."""
    try:
        h = yf.Ticker(symbol).history(period=period)
        return h if (h is not None and not h.empty) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_batch(period: str = "5d") -> pd.DataFrame:
    """Batch-download all 50 Nifty symbols. Returns raw yf DataFrame."""
    syms = [s["symbol"] for s in NIFTY50]
    try:
        raw = yf.download(syms, period=period, auto_adjust=True,
                          progress=False, group_by="ticker")
        return raw if (raw is not None and not raw.empty) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def extract_close_series(raw: pd.DataFrame, sym: str) -> pd.Series:
    """Safely extract the Close series for one symbol from batch download."""
    try:
        if raw.empty:
            return pd.Series(dtype=float)
        if isinstance(raw.columns, pd.MultiIndex):
            lvl0 = raw.columns.get_level_values(0).tolist()
            lvl1 = raw.columns.get_level_values(1).tolist()
            # group_by='ticker' -> (ticker, field)
            if sym in lvl0:
                return raw[sym]["Close"].dropna()
            # fallback: (field, ticker)
            if "Close" in lvl0 and sym in lvl1:
                return raw["Close"][sym].dropna()
        return pd.Series(dtype=float)
    except Exception:
        return pd.Series(dtype=float)

def get_curr_prev(raw: pd.DataFrame, sym: str):
    """Return (current_price, prev_price) or (None, None)."""
    s = extract_close_series(raw, sym)
    if len(s) >= 2:
        return safe_float(s.iloc[-1]), safe_float(s.iloc[-2])
    if len(s) == 1:
        return safe_float(s.iloc[0]), None
    return None, None

def build_stock_rows(raw: pd.DataFrame) -> pd.DataFrame:
    """Build a DataFrame of all 50 stocks with price/change columns."""
    rows = []
    for s in NIFTY50:
        curr, prev = get_curr_prev(raw, s["symbol"])
        chg  = (curr - prev) if (curr is not None and prev is not None) else None
        pct  = (chg / prev * 100) if (chg is not None and prev and prev != 0) else None
        rows.append({
            "Symbol":     s["symbol"].replace(".NS", ""),
            "Company":    s["name"],
            "Sector":     s["sector"],
            "Beta":       s["beta"],
            "Price (₹)":  round(curr, 2)  if curr is not None else "N/A",
            "Change (₹)": round(chg, 2)   if chg  is not None else "N/A",
            "Change (%)": round(pct, 2)   if pct  is not None else "N/A",
            "_curr":      curr,
            "_pct":       pct,
        })
    return pd.DataFrame(rows)

def safe_sort(df: pd.DataFrame, col: str, ascending: bool = True) -> pd.DataFrame:
    """Sort df by a numeric column that may contain None; NaNs go last."""
    numeric = pd.to_numeric(df[col], errors="coerce")
    # reset_index so argsort indices match positional indices
    df2     = df.reset_index(drop=True)
    numeric = numeric.reset_index(drop=True)
    order   = numeric.argsort(kind="stable")
    if not ascending:
        # NaN positions stay at end even when reversed
        n_valid = numeric.notna().sum()
        order   = list(order[:n_valid][::-1]) + list(order[n_valid:])
    return df2.iloc[list(order)]

def calc_impact(nifty_pct, sp, qty, b):
    spct = nifty_pct * b
    pchg = sp * (spct / 100)
    nsp  = sp + pchg
    pl   = pchg * qty
    return spct, pchg, nsp, sp * qty, nsp * qty, pl

def show_pl_badge(pl):
    if pl > 0:   st.success(f"✅ GAIN ₹{pl:,.2f}")
    elif pl < 0: st.error(f"❌ LOSS ₹{abs(pl):,.2f}")
    else:        st.info("⚖️ No Change")

# ============================================================
# SIDEBAR
# ============================================================
try:
    st.sidebar.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/NSE_Logo.svg/200px-NSE_Logo.svg.png",
        width=120
    )
except Exception:
    pass

st.sidebar.title("📈 NSE & Nifty Tracker")
page = st.sidebar.radio("Navigate", [
    "🏦 NSE Market Overview",
    "📈 Nifty 50 Index",
    "🏢 All 50 Companies",
    "🏆 Gainers & Losers",
    "🧮 P&L Calculator",
    "🔍 Stock Chart Lookup",
])

try:
    ist_tz = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist_tz)
    st.sidebar.markdown(f"⌨️ **IST:** {now_ist.strftime('%d %b %Y %I:%M %p')}")
except Exception:
    pass

market_open, market_status = is_nse_open()
if market_open:
    st.sidebar.markdown('<span class="tag-open">● MARKET OPEN</span>', unsafe_allow_html=True)
else:
    st.sidebar.markdown(f'<span class="tag-closed">● {market_status}</span>', unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.caption("📊 Data: Yahoo Finance (yfinance)")
st.sidebar.caption("⚠️ Educational use only. Not investment advice.")

# ============================================================
# PAGE 1 — NSE MARKET OVERVIEW
# ============================================================
if page == "🏦 NSE Market Overview":
    st.title("🏦 NSE Market Overview")
    st.markdown('<span class="tag-nse">NSE INDIA</span> &nbsp; National Stock Exchange — Live Indices & Market Pulse', unsafe_allow_html=True)
    st.markdown("")

    if market_open:
        st.success("✅ NSE is **OPEN** — Mon–Fri 9:15 AM – 3:30 PM IST")
    else:
        st.error(f"❌ NSE is **CLOSED** — {market_status}")

    st.markdown("---")
    st.subheader("📊 All NSE Indices Snapshot")

    idx_rows = []
    with st.spinner("Fetching NSE indices..."):
        for idx in NSE_INDICES:
            h = fetch_ticker(idx["symbol"], period="5d")
            if not h.empty and len(h) >= 2:
                c  = safe_float(h["Close"].iloc[-1])
                p  = safe_float(h["Close"].iloc[-2], c)
                ch = c - p
                pt = round((ch / p * 100), 2) if p != 0 else 0.0
                hi = safe_float(h["High"].max())
                lo = safe_float(h["Low"].min())
                idx_rows.append({
                    "Index":        idx["name"],
                    "Value":        f"₹{c:,.2f}",
                    "Change (pts)": f"{ch:+.2f}",
                    "Change (%)":   f"{pt:+.2f}%",
                    "High (5d)":    f"₹{hi:,.2f}",
                    "Low (5d)":     f"₹{lo:,.2f}",
                    "_pct":         pt,
                })
            else:
                idx_rows.append({
                    "Index": idx["name"], "Value": "N/A",
                    "Change (pts)": "N/A", "Change (%)": "N/A",
                    "High (5d)": "N/A", "Low (5d)": "N/A", "_pct": None,
                })

    idx_df = pd.DataFrame(idx_rows)
    st.dataframe(idx_df.drop(columns=["_pct"]), use_container_width=True, hide_index=True)

    valid_idx = idx_df[idx_df["_pct"].notna()].copy()
    if not valid_idx.empty:
        try:
            fig_bar = px.bar(
                valid_idx, x="Index", y="_pct",
                color="_pct",
                color_continuous_scale=["#ff1744", "#ffd600", "#00c853"],
                color_continuous_midpoint=0,
                text="Change (%)",
                title="NSE Indices — % Change",
                template="plotly_dark", height=400,
                labels={"_pct": "% Change"},
            )
            fig_bar.update_traces(textposition="outside")
            fig_bar.update_layout(showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_bar, use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ Chart error: {e}")

    st.markdown("---")
    st.subheader("📉 Indices Trend Comparison")
    period_sel = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1, key="idx_period")
    selected_indices = st.multiselect(
        "Select Indices",
        [i["name"] for i in NSE_INDICES],
        default=["Nifty 50", "Nifty Bank", "Nifty IT"],
    )
    sym_map = {i["name"]: i for i in NSE_INDICES}
    if selected_indices:
        fig_multi = go.Figure()
        with st.spinner("Loading trend data..."):
            for name in selected_indices:
                meta = sym_map.get(name)
                if not meta:
                    continue
                h = fetch_ticker(meta["symbol"], period=period_sel)
                if h.empty or len(h) < 2:
                    continue
                base = safe_float(h["Close"].iloc[0], 1)
                norm = (h["Close"] / base * 100) if base != 0 else h["Close"]
                fig_multi.add_trace(go.Scatter(
                    x=h.index, y=norm, mode="lines", name=name,
                    line=dict(color=meta["color"], width=2),
                ))
        if fig_multi.data:
            fig_multi.update_layout(
                title="Normalized Trend (Base = 100)",
                template="plotly_dark", height=450,
                xaxis_title="Date", yaxis_title="Normalized Value",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_multi, use_container_width=True)
        else:
            st.info("No data available for selected indices.")

    st.markdown("---")
    st.subheader("📊 Nifty 50 — Advance / Decline")
    with st.spinner("Computing advance/decline..."):
        try:
            raw_ad = fetch_batch(period="5d")
            advances = declines = unchanged = 0
            for s in NIFTY50:
                curr, prev = get_curr_prev(raw_ad, s["symbol"])
                if curr is None or prev is None:
                    continue
                diff = curr - prev
                if diff > 0:        advances  += 1
                elif diff < 0:      declines  += 1
                else:               unchanged += 1

            ca, cd, cu = st.columns(3)
            ca.metric("🟢 Advances",  advances)
            cd.metric("🔴 Declines",  declines)
            cu.metric("⚪ Unchanged", unchanged)

            total = advances + declines + unchanged
            if total > 0:
                try:
                    fig_ad = go.Figure(go.Pie(
                        labels=["Advances", "Declines", "Unchanged"],
                        values=[advances, declines, max(unchanged, 0)],
                        marker_colors=["#00c853", "#ff1744", "#9e9e9e"],
                        hole=0.5,
                    ))
                    fig_ad.update_layout(
                        title="Advance / Decline",
                        template="plotly_dark", height=320,
                    )
                    st.plotly_chart(fig_ad, use_container_width=True)
                except Exception as e:
                    st.warning(f"⚠️ Pie chart error: {e}")
        except Exception as ex:
            st.warning(f"⚠️ Could not compute advance/decline: {ex}")

# ============================================================
# PAGE 2 — NIFTY 50 INDEX
# ============================================================
elif page == "📈 Nifty 50 Index":
    st.title("📈 Nifty 50 Index")
    st.markdown('<span class="tag-actual">LIVE DATA</span> &nbsp; NSE Nifty 50 Index', unsafe_allow_html=True)
    st.markdown("")

    period_n = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1, key="n50_period")
    hist_n   = fetch_ticker("^NSEI", period=period_n)

    nifty_live_ok = False
    current_price = 22500.0
    pct_change    = 0.0
    change        = 0.0

    if not hist_n.empty and len(hist_n) >= 2:
        try:
            current_price = safe_float(hist_n["Close"].iloc[-1], 22500.0)
            prev_p        = safe_float(hist_n["Close"].iloc[-2], current_price)
            change        = current_price - prev_p
            pct_change    = (change / prev_p * 100) if prev_p != 0 else 0.0
            nifty_live_ok = True

            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("Nifty 50",    f"₹{current_price:,.2f}")
            c2.metric("Points Chg",  f"{change:+.2f}")
            c3.metric("% Change",    f"{pct_change:+.2f}%")
            c4.metric("Period High", f"₹{safe_float(hist_n['High'].max()):,.2f}")
            c5.metric("Period Low",  f"₹{safe_float(hist_n['Low'].min()):,.2f}")

            hn = hist_n.copy()
            hn["MA20"] = hn["Close"].rolling(20).mean()
            hn["MA50"] = hn["Close"].rolling(50).mean()

            fig_n = go.Figure()
            fig_n.add_trace(go.Candlestick(
                x=hn.index, open=hn["Open"], high=hn["High"],
                low=hn["Low"], close=hn["Close"], name="Nifty 50",
                increasing_line_color="#00c853", decreasing_line_color="#ff1744",
            ))
            fig_n.add_trace(go.Scatter(x=hn.index, y=hn["MA20"], mode="lines",
                name="MA20", line=dict(color="#ffd600", width=1.5, dash="dot")))
            fig_n.add_trace(go.Scatter(x=hn.index, y=hn["MA50"], mode="lines",
                name="MA50", line=dict(color="#ea80fc", width=1.5, dash="dash")))
            fig_n.update_layout(title=f"Nifty 50 — {period_n}", template="plotly_dark",
                height=480, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_n, use_container_width=True)

            hn["Daily_Ret_%"] = hn["Close"].pct_change() * 100
            ret_df = hn.dropna(subset=["Daily_Ret_%"])
            if not ret_df.empty:
                try:
                    fig_ret = px.bar(ret_df, x=ret_df.index, y="Daily_Ret_%",
                        color="Daily_Ret_%",
                        color_continuous_scale=["#ff1744", "#ffd600", "#00c853"],
                        title="Daily Returns (%)", template="plotly_dark", height=280)
                    st.plotly_chart(fig_ret, use_container_width=True)
                except Exception as e:
                    st.warning(f"⚠️ Returns chart error: {e}")

            if "Volume" in hn.columns:
                vol_df = hn[hn["Volume"] > 0]
                if not vol_df.empty:
                    try:
                        fig_vol = px.bar(vol_df, x=vol_df.index, y="Volume",
                            title="Volume", template="plotly_dark", height=250,
                            color_discrete_sequence=["#00e5ff"])
                        st.plotly_chart(fig_vol, use_container_width=True)
                    except Exception as e:
                        st.warning(f"⚠️ Volume chart error: {e}")
        except Exception as e:
            st.warning(f"⚠️ Error rendering index: {e}")
    else:
        st.warning("⚠️ Could not fetch Nifty 50 data.")

# ============================================================
# PAGE 3 — ALL 50 COMPANIES
# ============================================================
elif page == "🏢 All 50 Companies":
    st.title("🏢 All 50 Nifty Companies")
    st.markdown('<span class="tag-actual">LIVE DATA</span> &nbsp; NSE prices for all 50 companies', unsafe_allow_html=True)
    st.markdown("")

    col_f, col_s = st.columns([2, 1])
    with col_f: sector_filter = st.selectbox("Sector", sectors, key="sec_filter")
    with col_s: sort_by = st.selectbox("Sort by", ["Name","Price ↑","Price ↓","Change % ↑","Change % ↓"], key="sort_by")

    with st.spinner("⏳ Loading live prices..."):
        raw    = fetch_batch(period="5d")
        all_df = build_stock_rows(raw)

    disp = all_df.copy() if sector_filter == "All" else all_df[all_df["Sector"] == sector_filter].copy()

    if sort_by == "Price ↑":      disp = safe_sort(disp, "_curr", ascending=True)
    elif sort_by == "Price ↓":    disp = safe_sort(disp, "_curr", ascending=False)
    elif sort_by == "Change % ↑": disp = safe_sort(disp, "_pct",  ascending=True)
    elif sort_by == "Change % ↓": disp = safe_sort(disp, "_pct",  ascending=False)
    else:                          disp = disp.sort_values("Company").reset_index(drop=True)

    st.dataframe(
        disp[["Symbol","Company","Sector","Beta","Price (₹)","Change (₹)","Change (%)"]],
        use_container_width=True, hide_index=True,
    )
    st.caption(f"Showing {len(disp)} of 50 companies")

# ============================================================
# PAGE 4 — GAINERS & LOSERS
# ============================================================
elif page == "🏆 Gainers & Losers":
    st.title("🏆 Top Gainers & Losers")
    st.markdown('<span class="tag-actual">LIVE DATA</span>', unsafe_allow_html=True)
    st.markdown("")

    with st.spinner("Fetching data..."):
        raw    = fetch_batch(period="5d")
        all_df = build_stock_rows(raw)

    valid = all_df[all_df["_pct"].notna()].copy()

    if not valid.empty:
        top_n = st.slider("Show Top N", 3, 10, 5, key="top_n")
        gainers = valid.nlargest(top_n,  "_pct")[["Company","Sector","Price (₹)","Change (%)"]]
        losers  = valid.nsmallest(top_n, "_pct")[["Company","Sector","Price (₹)","Change (%)"]]

        cg, cl = st.columns(2)
        with cg:
            st.markdown(f"### 🟢 Top {top_n} Gainers")
            st.dataframe(gainers, use_container_width=True, hide_index=True)
        with cl:
            st.markdown(f"### 🔴 Top {top_n} Losers")
            st.dataframe(losers, use_container_width=True, hide_index=True)

        # Treemap — hover_data keys must match actual column names
        valid["_heat"] = valid["_pct"].abs().clip(lower=0.01)
        try:
            fig_h = px.treemap(
                valid,
                path=["Sector", "Company"],
                values="_heat",
                color="_pct",
                color_continuous_scale=["#ff1744", "#ffd600", "#00c853"],
                color_continuous_midpoint=0,
                title="Nifty 50 Heatmap — % Change",
                hover_data={"Price (₹)": True, "Change (%)": True, "_heat": False},
            )
            fig_h.update_layout(template="plotly_dark", height=520)
            st.plotly_chart(fig_h, use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ Heatmap error: {e}")
    else:
        st.info("⚠️ Not enough live data to show gainers/losers.")

# ============================================================
# PAGE 5 — P&L CALCULATOR
# ============================================================
elif page == "🧮 P&L Calculator":
    st.title("🧮 Stock P&L Calculator")
    st.markdown('<span class="tag-assumed">SIMULATED</span> &nbsp; Nifty movement impact on your holdings', unsafe_allow_html=True)
    st.markdown("")

    hist_c = fetch_ticker("^NSEI", period="5d")
    nifty_live_ok = False
    current_price = 22500.0
    pct_change    = 0.0
    change        = 0.0

    if not hist_c.empty and len(hist_c) >= 2:
        try:
            current_price = safe_float(hist_c["Close"].iloc[-1], 22500.0)
            prev_p        = safe_float(hist_c["Close"].iloc[-2], current_price)
            change        = current_price - prev_p
            pct_change    = (change / prev_p * 100) if prev_p != 0 else 0.0
            nifty_live_ok = True
        except Exception:
            pass

    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("📊 Nifty Movement")
        assumed_base   = st.number_input("Base Nifty Value", value=float(round(current_price, 2)),
                                         step=50.0, min_value=1.0, key="ab")
        assumed_change = st.number_input("Change in Points", value=-200.0, step=10.0, key="ac")
        assumed_new    = assumed_base + assumed_change
        assumed_pct    = (assumed_change / assumed_base * 100) if assumed_base != 0 else 0.0
        st.info(f"📌 Assumed: **{assumed_pct:+.2f}%** → **₹{assumed_new:,.2f}**")

        if nifty_live_ok:
            try:
                st.dataframe(pd.DataFrame({
                    "Metric":     ["Base","Change (pts)","Change (%)","New Value"],
                    "🟢 Actual":  [f"₹{current_price:,.2f}",f"{change:+.2f}",f"{pct_change:+.2f}%",f"₹{current_price:,.2f}"],
                    "🟡 Assumed": [f"₹{assumed_base:,.2f}",f"{assumed_change:+.2f}",f"{assumed_pct:+.2f}%",f"₹{assumed_new:,.2f}"],
                }), use_container_width=True, hide_index=True)
            except Exception:
                pass

    with col_r:
        st.subheader("💼 Your Stock")
        company_names = ["-- Custom --"] + nifty50_df["name"].tolist()
        selected_co   = st.selectbox("Company", company_names, key="sel_co")
        if selected_co != "-- Custom --":
            m            = nifty50_df[nifty50_df["name"] == selected_co]
            default_beta = float(m["beta"].iloc[0]) if not m.empty else 1.0
            stock_name   = selected_co
        else:
            default_beta = 1.0
            stock_name   = st.text_input("Stock Name", value="My Stock", key="sn")
        stock_price = st.number_input("Price (₹)", value=100.0, min_value=0.01, step=10.0, key="sp")
        quantity    = st.number_input("Quantity", value=10, min_value=1, step=1, key="qty")
        beta        = st.slider("Beta", 0.0, 3.0, float(round(default_beta, 1)), 0.1, key="beta_sl")
        st.caption(f"💡 Default beta for **{selected_co}**: **{default_beta}**")

    st.markdown("---")
    col_a, col_s2 = st.columns(2)

    with col_a:
        st.markdown("### 🟢 Actual Nifty Impact")
        if nifty_live_ok:
            a = calc_impact(pct_change, stock_price, quantity, beta)
            st.metric("Stock % Change",  f"{a[0]:+.2f}%")
            st.metric("New Price",       f"₹{a[2]:,.2f}", delta=f"₹{a[1]:+.2f}")
            st.metric("P&L",             f"₹{a[5]:+,.2f}")
            show_pl_badge(a[5])
        else:
            st.warning("⚠️ Live Nifty data unavailable.")

    with col_s2:
        st.markdown("### 🟡 Assumed Nifty Impact")
        s2 = calc_impact(assumed_pct, stock_price, quantity, beta)
        st.metric("Stock % Change", f"{s2[0]:+.2f}%")
        st.metric("New Price",      f"₹{s2[2]:,.2f}", delta=f"₹{s2[1]:+.2f}")
        st.metric("P&L",            f"₹{s2[5]:+,.2f}")
        show_pl_badge(s2[5])

    st.markdown("#### 📋 Sensitivity Table")
    sen = []
    for pts in [-500, -300, -200, -100, 0, 100, 200, 300, 500]:
        p   = (pts / assumed_base * 100) if assumed_base != 0 else 0.0
        sp_ = p * beta
        pc  = stock_price * (sp_ / 100)
        sen.append({
            "Nifty Chg (pts)": f"{pts:+}",
            "Nifty %":         f"{p:+.2f}%",
            "Stock %":         f"{sp_:+.2f}%",
            "New Price":       f"₹{stock_price + pc:,.2f}",
            "P&L (₹)":        f"₹{pc * quantity:+,.2f}",
        })
    st.dataframe(pd.DataFrame(sen), use_container_width=True, hide_index=True)

    with st.expander("📘 Formula Reference"):
        st.markdown(f"""
        | Formula | Expression |
        |---------|------------|
        | Nifty % | `pts ÷ base × 100` |
        | Stock % | `Nifty % × Beta ({beta})` |
        | New Price | `Price × (1 + Stock% ÷ 100)` |
        | P&L | `(New − Old) × Qty` |

        > ⚠️ **Disclaimer**: Beta-based estimate only. Not investment advice.
        """)

# ============================================================
# PAGE 6 — STOCK CHART LOOKUP
# ============================================================
elif page == "🔍 Stock Chart Lookup":
    st.title("🔍 NSE Stock Chart Lookup")
    st.markdown('<span class="tag-nse">NSE</span> &nbsp; Chart any NSE-listed stock', unsafe_allow_html=True)
    st.markdown("")

    quick_options = ["-- Type below --"] + [
        f"{s['name']} ({s['symbol'].replace('.NS', '')})"
        for s in NIFTY50
    ]
    quick = st.selectbox("Quick Pick (Nifty 50)", quick_options, key="quick_pick")
    default_sym = "RELIANCE"
    if quick != "-- Type below --":
        try:
            default_sym = quick.split("(")[-1].replace(")", "").strip()
        except Exception:
            default_sym = "RELIANCE"

    col_sym, col_per, col_type = st.columns([2, 1, 1])
    with col_sym:  sym_in  = st.text_input("NSE Symbol (CAPS)", value=default_sym, key="sym_in")
    with col_per:  per_ch  = st.selectbox("Period", ["1wk","1mo","3mo","6mo","1y"], index=1, key="per_ch")
    with col_type: ch_type = st.selectbox("Chart Type", ["Candlestick","Line","Area"], key="ch_type")

    if st.button("🔎 Fetch & Plot", key="fetch_btn"):
        clean = sym_in.strip().upper() if sym_in else ""
        if not clean:
            st.error("❌ Please enter a valid NSE symbol.")
        else:
            with st.spinner(f"Fetching {clean}.NS..."):
                try:
                    sh = yf.Ticker(f"{clean}.NS").history(period=per_ch)
                    if sh is None or sh.empty:
                        st.error(f"No data for **{clean}**. Check: RELIANCE, HDFCBANK, TCS, INFY, SBIN")
                    elif len(sh) < 2:
                        st.warning("Too few data points.")
                        st.metric("Latest Close", f"₹{safe_float(sh['Close'].iloc[-1]):,.2f}")
                    else:
                        lp    = safe_float(sh["Close"].iloc[-1])
                        pp    = safe_float(sh["Close"].iloc[-2])
                        chg   = lp - pp
                        pct   = (chg / pp * 100) if pp != 0 else 0.0
                        wk_hi = safe_float(sh["High"].max())
                        wk_lo = safe_float(sh["Low"].min())

                        c1,c2,c3,c4,c5 = st.columns(5)
                        c1.metric("Price",       f"₹{lp:,.2f}")
                        c2.metric("Change",      f"₹{chg:+.2f}")
                        c3.metric("% Change",    f"{pct:+.2f}%")
                        c4.metric("Period High", f"₹{wk_hi:,.2f}")
                        c5.metric("Period Low",  f"₹{wk_lo:,.2f}")

                        fig_s = go.Figure()
                        if ch_type == "Candlestick":
                            fig_s.add_trace(go.Candlestick(
                                x=sh.index, open=sh["Open"], high=sh["High"],
                                low=sh["Low"], close=sh["Close"], name=clean,
                                increasing_line_color="#00c853",
                                decreasing_line_color="#ff1744",
                            ))
                        elif ch_type == "Line":
                            fig_s.add_trace(go.Scatter(
                                x=sh.index, y=sh["Close"],
                                mode="lines", name=clean,
                                line=dict(color="#00e5ff", width=2),
                            ))
                        else:
                            fig_s.add_trace(go.Scatter(
                                x=sh.index, y=sh["Close"],
                                mode="lines", fill="tozeroy", name=clean,
                                line=dict(color="#00e5ff", width=2),
                                fillcolor="rgba(0,229,255,0.15)",
                            ))

                        sh_ma = sh.copy()
                        sh_ma["MA20"] = sh_ma["Close"].rolling(20).mean()
                        fig_s.add_trace(go.Scatter(
                            x=sh_ma.index, y=sh_ma["MA20"],
                            mode="lines", name="MA20",
                            line=dict(color="#ffd600", width=1.5, dash="dot"),
                        ))
                        fig_s.update_layout(
                            title=f"{clean} — {ch_type} ({per_ch})",
                            template="plotly_dark", height=460,
                            xaxis_rangeslider_visible=False,
                        )
                        st.plotly_chart(fig_s, use_container_width=True)

                        if "Volume" in sh.columns:
                            vol = sh[sh["Volume"] > 0]
                            if not vol.empty:
                                try:
                                    fig_v = px.bar(
                                        vol, x=vol.index, y="Volume",
                                        title=f"{clean} — Volume",
                                        template="plotly_dark", height=220,
                                        color_discrete_sequence=["#00e5ff"],
                                    )
                                    st.plotly_chart(fig_v, use_container_width=True)
                                except Exception as ve:
                                    st.warning(f"⚠️ Volume chart error: {ve}")
                except Exception as ex:
                    st.error(f"❌ Error fetching **{clean}**: {str(ex)}")
                    st.info("💡 Use NSE symbols in CAPS: RELIANCE, HDFCBANK, INFY, TCS, SBIN")

st.markdown("---")
st.markdown(
    "<center>Built with ❤️ using Streamlit &nbsp;| Data: NSE via Yahoo Finance&nbsp;| All 50 Nifty Companies</center>",
    unsafe_allow_html=True,
)
