import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta
import pytz
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="NSE & Nifty 50 — Ultimate Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject shared light theme
from utils.theme import inject
inject()

from utils.supabase_auth import get_current_user, logout, is_guest

user     = get_current_user()
name     = user["full_name"] if user else "Guest"
username = user["email"]     if user else ""

# ── Sidebar branding ──────────────────────────────────────────────────
try:
    st.sidebar.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/NSE_Logo.svg/200px-NSE_Logo.svg.png",
        width=120,
    )
except Exception:
    pass

st.sidebar.markdown("## 📈 NSE + Time Machine")

# User badge
if user:
    st.sidebar.markdown(
        f"<span class='ui-badge badge-live'>👤 {name}</span>",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("🚧 Sign Out", key="sidebar_logout"):
        logout()
        st.rerun()
else:
    st.sidebar.markdown(
        "<span class='ui-badge badge-hist'>👤 Guest — browsing only</span>",
        unsafe_allow_html=True,
    )
    st.sidebar.page_link("pages/00_🔐_Login.py", label="🔐 Sign In / Register")

st.sidebar.markdown("---")

page = st.sidebar.radio("", [
    "🏦 NSE Market Overview",
    "📈 Nifty 50 Index",
    "🏢 All 50 Companies",
    "🏆 Gainers & Losers",
    "🧮 P&L Calculator",
    "🔍 Stock Chart Lookup",
    "─────────────────",
    "⏰ Time Machine",
    "🧪 Scenario Engine",
    "💼 Paper Portfolio",
    "📅 Market Calendar",
], label_visibility="collapsed")

try:
    ist_tz  = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist_tz)
    st.sidebar.markdown(f"⏰ **IST:** {now_ist.strftime('%d %b %Y %I:%M %p')}")
except Exception:
    pass


def is_nse_open():
    try:
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
        if now.weekday() >= 5:
            return False, "Weekend — Market Closed"
        mo = now.replace(hour=9,  minute=15, second=0, microsecond=0)
        mc = now.replace(hour=15, minute=30, second=0, microsecond=0)
        if mo <= now <= mc:   return True,  "Open"
        elif now < mo:        return False, "Pre-Market (Opens 9:15 AM)"
        else:                 return False, "Closed (3:30 PM session ended)"
    except Exception:
        return False, "Unknown"


market_open, market_status = is_nse_open()
if market_open:
    st.sidebar.markdown("<span class='ui-badge badge-live'>● MARKET OPEN</span>", unsafe_allow_html=True)
else:
    st.sidebar.markdown(f"<span class='ui-badge' style='background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;'>● {market_status}</span>", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.caption("📊 Data: Yahoo Finance")
st.sidebar.caption("⏰ 5yr history for Time Machine")
st.sidebar.caption("⚠️ Educational use only")

# ================================================================
# CONSTANTS
# ================================================================
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
SYMBOLS    = [s["symbol"] for s in NIFTY50]
sectors    = ["All"] + sorted(nifty50_df["sector"].unique().tolist())

NSE_INDICES = [
    {"symbol": "^NSEI",      "name": "Nifty 50",     "color": "#6366f1"},
    {"symbol": "^NSEBANK",   "name": "Nifty Bank",   "color": "#06b6d4"},
    {"symbol": "^CNXIT",     "name": "Nifty IT",     "color": "#10b981"},
    {"symbol": "^CNXAUTO",   "name": "Nifty Auto",   "color": "#f59e0b"},
    {"symbol": "^CNXPHARMA", "name": "Nifty Pharma", "color": "#8b5cf6"},
    {"symbol": "^CNXFMCG",   "name": "Nifty FMCG",   "color": "#ec4899"},
    {"symbol": "^CNXMETAL",  "name": "Nifty Metal",  "color": "#ef4444"},
    {"symbol": "^CNXREALTY", "name": "Nifty Realty", "color": "#14b8a6"},
]

MACRO_EVENTS = {
    "Rupee depreciates 5%":   {"desc": "USD/INR rises ~5% in a week",         "proxy": "USDINR=X", "lo": 0.04,  "hi": 0.08},
    "Rupee appreciates 3%":   {"desc": "USD/INR falls ~3% in a week",         "proxy": "USDINR=X", "lo": -0.05, "hi": -0.02},
    "Crude oil spikes +10%":  {"desc": "WTI crude futures rise ~10% in week",  "proxy": "CL=F",     "lo": 0.08,  "hi": 0.15},
    "Crude oil crashes -15%": {"desc": "WTI crude futures fall ~15% in week",  "proxy": "CL=F",     "lo": -0.20, "hi": -0.10},
    "Gold rallies +5%":       {"desc": "Gold futures rise ~5% in a week",      "proxy": "GC=F",     "lo": 0.04,  "hi": 0.08},
    "Nifty flash crash -5%":  {"desc": "Nifty 50 itself falls ~5% in week",    "proxy": "^NSEI",    "lo": -0.08, "hi": -0.04},
    "Nifty bull run +5%":     {"desc": "Nifty 50 rises ~5% in a week",         "proxy": "^NSEI",    "lo": 0.04,  "hi": 0.08},
}

FAMOUS_DATES = {
    "🟥 COVID Crash — Mar 23 2020":     date(2020, 3, 23),
    "🟢 COVID Recovery — Apr 7 2020":   date(2020, 4, 7),
    "💥 Russia-Ukraine — Feb 24 2022":  date(2022, 2, 24),
    "💰 RBI Rate Hike — May 4 2022":    date(2022, 5, 4),
    "🏆 Union Budget — Feb 1 2023":     date(2023, 2, 1),
    "⬆️ All-time High — Sep 27 2024":  date(2024, 9, 27),
}

PLT = "plotly_white"   # unified Plotly template
PLT_LAYOUT = dict(paper_bgcolor="#ffffff", plot_bgcolor="#fafafa", font_color="#1a1a2e")

# ================================================================
# HELPERS
# ================================================================
def safe_float(val, default: float = 0.0) -> float:
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default


@st.cache_data(ttl=300)
def fetch_ticker(symbol: str, period: str = "3mo") -> pd.DataFrame:
    try:
        h = yf.Ticker(symbol).history(period=period, auto_adjust=True)
        if h is not None and not h.empty:
            h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
            return h
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_batch(period: str = "5d") -> pd.DataFrame:
    try:
        raw = yf.download(SYMBOLS, period=period, auto_adjust=True,
                          progress=False, group_by="ticker", threads=True)
        if raw is None or raw.empty:
            return pd.DataFrame()
        if isinstance(raw.index, pd.DatetimeIndex):
            raw.index = raw.index.tz_localize(None).normalize()
        return raw
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def fetch_all_history() -> dict:
    result: dict = {}
    extras = ["USDINR=X", "CL=F", "GC=F", "^NSEI"]
    for sym in SYMBOLS + extras:
        try:
            h = yf.Ticker(sym).history(period="5y", auto_adjust=True)
            if h is not None and not h.empty:
                h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
                result[sym] = h
        except Exception:
            pass
    return result


def _extract_series(raw: pd.DataFrame, sym: str, col: str = "Close") -> pd.Series:
    if raw is None or raw.empty:
        return pd.Series(dtype=float)
    try:
        cols = raw.columns
        if isinstance(cols, pd.MultiIndex):
            if col in cols.get_level_values(0) and sym in cols.get_level_values(1):
                return raw[col][sym].dropna()
            if sym in cols.get_level_values(0) and col in cols.get_level_values(1):
                return raw[sym][col].dropna()
        else:
            if col in raw.columns:
                return raw[col].dropna()
    except Exception:
        pass
    return pd.Series(dtype=float)


def get_curr_prev(raw: pd.DataFrame, sym: str):
    s = _extract_series(raw, sym, "Close")
    if len(s) >= 2: return safe_float(s.iloc[-1]), safe_float(s.iloc[-2])
    if len(s) == 1: return safe_float(s.iloc[0]),  None
    return None, None


def build_stock_rows(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for s in NIFTY50:
        curr, prev = get_curr_prev(raw, s["symbol"])
        chg = (curr - prev) if (curr is not None and prev is not None) else None
        pct = (chg / prev * 100) if (chg is not None and prev and prev != 0) else None
        rows.append({
            "Symbol":     s["symbol"].replace(".NS", ""),
            "Company":    s["name"],
            "Sector":     s["sector"],
            "Beta":       s["beta"],
            "Price (₹)": round(curr, 2) if curr is not None else "N/A",
            "Change (₹)": round(chg, 2)  if chg  is not None else "N/A",
            "Change (%)": round(pct, 2)  if pct  is not None else "N/A",
            "_curr": curr,
            "_pct":  pct,
        })
    return pd.DataFrame(rows)


def safe_sort(df: pd.DataFrame, col: str, ascending: bool = True) -> pd.DataFrame:
    try:
        numeric = pd.to_numeric(df[col], errors="coerce").reset_index(drop=True)
        df2     = df.reset_index(drop=True)
        if numeric.isna().all(): return df2
        order = numeric.argsort(kind="stable")
        if not ascending:
            n_valid = int(numeric.notna().sum())
            order   = list(order[:n_valid][::-1]) + list(order[n_valid:])
        return df2.iloc[list(order)].reset_index(drop=True)
    except Exception:
        return df


def calc_impact(nifty_pct, sp, qty, b):
    spct = nifty_pct * b
    pchg = sp * (spct / 100)
    nsp  = sp + pchg
    return spct, pchg, nsp, sp * qty, nsp * qty, pchg * qty


def show_pl(pl):
    pl = safe_float(pl)
    if   pl > 0:  st.success(f"✅ GAIN ₹{pl:,.2f}")
    elif pl < 0:  st.error(f"❌ LOSS ₹{abs(pl):,.2f}")
    else:         st.info("⚖️ No Change")


def _nearest_row(df: pd.DataFrame, target: pd.Timestamp, window: int = 4):
    for delta in range(0, window + 1):
        for sign in ([0] if delta == 0 else [1, -1]):
            cand = target + pd.Timedelta(days=delta * sign)
            mask = df.index.normalize() == cand.normalize()
            if mask.any():
                return df[mask].iloc[0]
    return None


def tm_get_snapshot(all_hist: dict, target: date) -> pd.DataFrame:
    ts       = pd.Timestamp(target)
    meta_map = {s["symbol"]: s for s in NIFTY50}
    rows: list = []
    for sym in SYMBOLS:
        if sym not in all_hist: continue
        row = _nearest_row(all_hist[sym], ts)
        if row is None: continue
        meta = meta_map.get(sym, {})
        rows.append({
            "Symbol": sym.replace(".NS", ""),
            "Name":   meta.get("name",   sym),
            "Sector": meta.get("sector", "Unknown"),
            "Open":   safe_float(row.get("Open",   np.nan)),
            "High":   safe_float(row.get("High",   np.nan)),
            "Low":    safe_float(row.get("Low",    np.nan)),
            "Close":  safe_float(row.get("Close",  np.nan)),
            "Volume": int(safe_float(row.get("Volume", 0))),
        })
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows).set_index("Symbol")


def tm_paper_portfolio(all_hist, invest_date, end_date, investment, symbols_to_use):
    symbols_to_use = [s for s in symbols_to_use if s in all_hist]
    if not symbols_to_use: return None
    alloc = investment / len(symbols_to_use)
    buy   = tm_get_snapshot(all_hist, invest_date)
    sell  = tm_get_snapshot(all_hist, end_date)
    if buy.empty or sell.empty: return None
    rows: list = []; idx_labels: list = []
    total_inv = total_final = 0.0
    for sym in symbols_to_use:
        short = sym.replace(".NS", "")
        if short not in buy.index: continue
        bp = safe_float(buy.loc[short, "Close"])
        if bp <= 0: continue
        shares = alloc / bp
        sp_val = safe_float(sell.loc[short, "Close"]) if short in sell.index else np.nan
        pl  = (sp_val - bp) * shares   if pd.notna(sp_val) else np.nan
        ret = (sp_val - bp) / bp * 100 if pd.notna(sp_val) else np.nan
        rows.append({
            "Buy ₹":   round(bp,     2),
            "Shares":  round(shares, 3),
            "Sell ₹":  round(sp_val, 2) if pd.notna(sp_val) else "N/A",
            "P&L ₹":   round(pl,     2) if pd.notna(pl)     else "N/A",
            "Return %":round(ret,    2) if pd.notna(ret)    else "N/A",
            "_pl":     pl,
        })
        idx_labels.append(short)
        total_inv += alloc
        if pd.notna(sp_val): total_final += sp_val * shares
    if not rows: return None
    pf_df   = pd.DataFrame(rows, index=idx_labels)
    abs_pl  = total_final - total_inv
    ret_pct = (abs_pl / total_inv * 100) if total_inv > 0 else 0.0
    days    = (end_date - invest_date).days
    years   = days / 365.25
    cagr    = ((total_final / total_inv) ** (1 / years) - 1) * 100 \
              if (total_inv > 0 and total_final > 0 and years > 0.02) else 0.0
    dur     = f"{days // 365}y {days % 365}d" if days >= 365 else f"{days} days"
    buy_prices = {}
    for sym in symbols_to_use:
        short = sym.replace(".NS", "")
        if short not in buy.index: continue
        bp = safe_float(buy.loc[short, "Close"])
        if bp > 0: buy_prices[sym] = alloc / bp
    growth: dict = {}
    for dt in pd.date_range(pd.Timestamp(invest_date), pd.Timestamp(end_date), freq="W"):
        val = 0.0
        for sym, sh in buy_prices.items():
            df_sym = all_hist.get(sym, pd.DataFrame())
            if df_sym.empty: continue
            row = _nearest_row(df_sym, dt, window=5)
            if row is not None:
                val += safe_float(row.get("Close", 0)) * sh
        if val > 0: growth[dt] = val
    growth_s = pd.Series(growth)
    return {"pf_df": pf_df, "growth": growth_s, "invested": total_inv,
            "final": total_final, "abs_pl": abs_pl, "ret_pct": ret_pct,
            "cagr": cagr, "dur": dur}


def tm_scenario(all_hist: dict, event_key: str, as_of_date: date) -> pd.DataFrame:
    ev     = MACRO_EVENTS[event_key]
    cutoff = pd.Timestamp(as_of_date)
    proxy  = ev["proxy"]
    if proxy not in all_hist: return pd.DataFrame()
    pxy = all_hist[proxy][all_hist[proxy].index <= cutoff]
    if len(pxy) < 10: return pd.DataFrame()
    try:
        weekly_pxy = pxy["Close"].resample("W-FRI").last().dropna()
        weekly_ret = weekly_pxy.pct_change().dropna()
    except Exception:
        return pd.DataFrame()
    event_wks = weekly_ret[(weekly_ret >= ev["lo"]) & (weekly_ret <= ev["hi"])].index
    event_wks = event_wks[event_wks <= cutoff]
    if len(event_wks) < 1: return pd.DataFrame()
    meta_map = {s["symbol"]: s for s in NIFTY50}
    rows: list = []
    for sym in SYMBOLS:
        if sym not in all_hist: continue
        df_s = all_hist[sym][all_hist[sym].index <= cutoff]
        if len(df_s) < 5: continue
        try:
            wk_ret = df_s["Close"].resample("W-FRI").last().dropna().pct_change().dropna() * 100
        except Exception:
            continue
        bucket: list = []
        for ew in event_wks:
            lo_w = ew - pd.Timedelta(days=7)
            hi_w = ew + pd.Timedelta(days=7)
            w_idx = wk_ret.index[(wk_ret.index >= lo_w) & (wk_ret.index <= hi_w)]
            if not w_idx.empty:
                v = wk_ret.get(w_idx[0], np.nan)
                if pd.notna(v): bucket.append(float(v))
        if not bucket: continue
        arr  = np.array(bucket)
        meta = meta_map.get(sym, {})
        rows.append({
            "Symbol":     sym.replace(".NS", ""),
            "Name":       meta.get("name",   sym),
            "Sector":     meta.get("sector", "?"),
            "Avg Return": round(float(np.mean(arr)), 2),
            "Std Dev":    round(float(np.std(arr)),  2),
            "Best %":     round(float(np.max(arr)),  2),
            "Worst %":    round(float(np.min(arr)),  2),
            "Data Pts":   len(bucket),
            "Confidence": round(max(0.0, 100 - float(np.std(arr)) * 10), 1),
        })
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows).set_index("Symbol").sort_values("Avg Return", ascending=False)


# ================================================================
# PAGE HEADER HELPER
# ================================================================
def page_header(icon: str, title: str, badge: str, badge_class: str = "badge-nse", sub: str = ""):
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:1rem;margin-bottom:.8rem;">
          <div style="font-size:2.2rem;">{icon}</div>
          <div>
            <div class="ui-page-title">{title}</div>
            <div class="ui-caption" style="margin:0;">
              <span class="ui-badge {badge_class}">{badge}</span>
              {'&nbsp;' + sub if sub else ''}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ================================================================
# SEPARATOR
# ================================================================
if page == "─────────────────":
    st.info("💬 Select a page from the sidebar.")
    st.stop()

# ================================================================
# PAGE 1 — NSE MARKET OVERVIEW
# ================================================================
elif page == "🏦 NSE Market Overview":
    page_header("🏦", "NSE Market Overview", "NSE INDIA", "badge-nse",
                "National Stock Exchange — Live Indices")
    if market_open: st.success("✅ NSE is **OPEN** — Mon–Fri 9:15 AM – 3:30 PM IST")
    else:           st.error(f"❌ NSE **CLOSED** — {market_status}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    st.markdown("#### 📊 NSE Indices Snapshot")
    idx_rows: list = []
    with st.spinner("Fetching NSE indices…"):
        for idx in NSE_INDICES:
            h = fetch_ticker(idx["symbol"], period="5d")
            if not h.empty and len(h) >= 2:
                c  = safe_float(h["Close"].iloc[-1])
                p  = safe_float(h["Close"].iloc[-2], c)
                ch = c - p
                pt = round((ch / p * 100), 2) if p != 0 else 0.0
                idx_rows.append({"Index": idx["name"], "Value": f"₹{c:,.2f}",
                    "Change (pts)": f"{ch:+.2f}", "Change (%)": f"{pt:+.2f}%",
                    "High": f"₹{safe_float(h['High'].max()):,.2f}",
                    "Low":  f"₹{safe_float(h['Low'].min()):,.2f}", "_pct": pt})
            else:
                idx_rows.append({"Index": idx["name"], "Value": "N/A",
                    "Change (pts)": "N/A", "Change (%)": "N/A",
                    "High": "N/A", "Low": "N/A", "_pct": None})
    idx_df = pd.DataFrame(idx_rows)
    st.dataframe(idx_df.drop(columns=["_pct"]), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    valid_idx = idx_df[idx_df["_pct"].notna()].copy()
    if not valid_idx.empty:
        try:
            fig_b = px.bar(valid_idx, x="Index", y="_pct",
                color="_pct", color_continuous_scale=["#ef4444","#f59e0b","#10b981"],
                color_continuous_midpoint=0, text="Change (%)",
                title="NSE Indices % Change", template=PLT, height=380,
                labels={"_pct": "% Change"})
            fig_b.update_traces(textposition="outside")
            fig_b.update_layout(**PLT_LAYOUT, coloraxis_showscale=False)
            st.plotly_chart(fig_b, use_container_width=True)
        except Exception as e: st.warning(f"⚠️ {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    st.markdown("#### 📉 Indices Trend Comparison")
    p_sel   = st.selectbox("Period", ["1mo","3mo","6mo","1y"], index=1, key="idx_p")
    sel_idx = st.multiselect("Indices", [i["name"] for i in NSE_INDICES],
                              default=["Nifty 50","Nifty Bank","Nifty IT"])
    sym_map = {i["name"]: i for i in NSE_INDICES}
    if sel_idx:
        fig_m = go.Figure()
        for name_idx in sel_idx:
            meta = sym_map.get(name_idx)
            if not meta: continue
            h = fetch_ticker(meta["symbol"], period=p_sel)
            if h.empty or len(h) < 2: continue
            base = safe_float(h["Close"].iloc[0], 1)
            norm = (h["Close"] / base * 100) if base != 0 else h["Close"]
            fig_m.add_trace(go.Scatter(x=h.index, y=norm, mode="lines", name=name_idx,
                line=dict(color=meta["color"], width=2.5)))
        if fig_m.data:
            fig_m.update_layout(title="Normalized Trend (Base=100)", template=PLT,
                height=420, xaxis_title="Date", yaxis_title="Value",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                **PLT_LAYOUT)
            st.plotly_chart(fig_m, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    st.markdown("#### 📊 Advance / Decline")
    try:
        raw_ad = fetch_batch("5d")
        adv = dec = unc = 0
        for s in NIFTY50:
            curr, prev = get_curr_prev(raw_ad, s["symbol"])
            if curr is None or prev is None: continue
            d = curr - prev
            if d > 0: adv += 1
            elif d < 0: dec += 1
            else: unc += 1
        ca, cd, cu = st.columns(3)
        ca.metric("🟢 Advances", adv); cd.metric("🔴 Declines", dec); cu.metric("⚪ Unchanged", unc)
        if adv + dec > 0:
            fig_ad = go.Figure(go.Pie(
                labels=["Advances","Declines","Unchanged"],
                values=[adv, dec, max(unc,0)],
                marker_colors=["#10b981","#ef4444","#9ca3af"], hole=0.5))
            fig_ad.update_layout(title="Advance/Decline", template=PLT, height=300, **PLT_LAYOUT)
            st.plotly_chart(fig_ad, use_container_width=True)
    except Exception as ex: st.warning(f"⚠️ {ex}")
    st.markdown("</div>", unsafe_allow_html=True)

# ================================================================
# PAGE 2 — NIFTY 50 INDEX
# ================================================================
elif page == "📈 Nifty 50 Index":
    page_header("📈", "Nifty 50 Index", "LIVE", "badge-live", "NSE Nifty 50 Index")
    p_n  = st.selectbox("Period", ["1mo","3mo","6mo","1y"], index=1, key="n50p")
    hist = fetch_ticker("^NSEI", period=p_n)
    if not hist.empty and len(hist) >= 2:
        cp = safe_float(hist["Close"].iloc[-1], 22500.0)
        pp = safe_float(hist["Close"].iloc[-2], cp)
        ch = cp - pp; pt = (ch/pp*100) if pp != 0 else 0.0
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Nifty 50",    f"₹{cp:,.2f}")
        c2.metric("Points",      f"{ch:+.2f}")
        c3.metric("% Change",    f"{pt:+.2f}%")
        c4.metric("Period High", f"₹{safe_float(hist['High'].max()):,.2f}")
        c5.metric("Period Low",  f"₹{safe_float(hist['Low'].min()):,.2f}")
        hn = hist.copy()
        hn["MA20"] = hn["Close"].rolling(20).mean()
        hn["MA50"] = hn["Close"].rolling(50).mean()
        st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
        try:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=hn.index, open=hn["Open"], high=hn["High"],
                low=hn["Low"], close=hn["Close"], name="Nifty 50",
                increasing_line_color="#10b981", decreasing_line_color="#ef4444"))
            fig.add_trace(go.Scatter(x=hn.index, y=hn["MA20"], mode="lines", name="MA20",
                line=dict(color="#f59e0b", width=1.5, dash="dot")))
            fig.add_trace(go.Scatter(x=hn.index, y=hn["MA50"], mode="lines", name="MA50",
                line=dict(color="#6366f1", width=1.5, dash="dash")))
            fig.update_layout(title=f"Nifty 50 — {p_n}", template=PLT,
                height=480, xaxis_rangeslider_visible=False, **PLT_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e: st.warning(f"⚠️ {e}")
        st.markdown("</div>", unsafe_allow_html=True)
        hn["Ret%"] = hn["Close"].pct_change() * 100
        ret_df = hn.dropna(subset=["Ret%"])
        if not ret_df.empty:
            st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
            try:
                fig_r = px.bar(ret_df, x=ret_df.index, y="Ret%",
                    color="Ret%", color_continuous_scale=["#ef4444","#f59e0b","#10b981"],
                    title="Daily Returns (%)", template=PLT, height=260)
                fig_r.update_layout(**PLT_LAYOUT)
                st.plotly_chart(fig_r, use_container_width=True)
            except Exception as e: st.warning(f"⚠️ {e}")
            st.markdown("</div>", unsafe_allow_html=True)
        if "Volume" in hn.columns:
            vd = hn[hn["Volume"] > 0]
            if not vd.empty:
                st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
                try:
                    fig_v = px.bar(vd, x=vd.index, y="Volume", title="Volume",
                        template=PLT, height=230, color_discrete_sequence=["#6366f1"])
                    fig_v.update_layout(**PLT_LAYOUT)
                    st.plotly_chart(fig_v, use_container_width=True)
                except Exception as e: st.warning(f"⚠️ {e}")
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ Could not fetch Nifty 50 data.")

# ================================================================
# PAGE 3 — ALL 50 COMPANIES
# ================================================================
elif page == "🏢 All 50 Companies":
    page_header("🏢", "All 50 Nifty Companies", "LIVE", "badge-live", "Real-time NSE prices")
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    cf, cs = st.columns([2,1])
    with cf: sec_f  = st.selectbox("Sector", sectors, key="sec_f")
    with cs: sort_b = st.selectbox("Sort by", ["Name","Price ↑","Price ↓","Change % ↑","Change % ↓"], key="srt")
    with st.spinner("Loading…"):
        raw    = fetch_batch("5d")
        all_df = build_stock_rows(raw)
    disp = all_df.copy() if sec_f == "All" else all_df[all_df["Sector"] == sec_f].copy()
    if   sort_b == "Price ↑":     disp = safe_sort(disp, "_curr", True)
    elif sort_b == "Price ↓":     disp = safe_sort(disp, "_curr", False)
    elif sort_b == "Change % ↑": disp = safe_sort(disp, "_pct",  True)
    elif sort_b == "Change % ↓": disp = safe_sort(disp, "_pct",  False)
    else: disp = disp.sort_values("Company").reset_index(drop=True)
    st.dataframe(disp[["Symbol","Company","Sector","Beta","Price (₹)","Change (₹)","Change (%)"]],
                 use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(disp)} of 50 companies")
    st.markdown("</div>", unsafe_allow_html=True)

# ================================================================
# PAGE 4 — GAINERS & LOSERS
# ================================================================
elif page == "🏆 Gainers & Losers":
    page_header("🏆", "Top Gainers & Losers", "LIVE", "badge-live")
    with st.spinner("Fetching…"):
        raw    = fetch_batch("5d")
        all_df = build_stock_rows(raw)
    valid = all_df[all_df["_pct"].notna()].copy()
    if not valid.empty:
        top_n = st.slider("Top N", 3, 10, 5)
        g = valid.nlargest(top_n,  "_pct")[["Company","Sector","Price (₹)","Change (%)"]]
        l = valid.nsmallest(top_n, "_pct")[["Company","Sector","Price (₹)","Change (%)"]]
        cg, cl = st.columns(2)
        with cg:
            st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
            st.markdown(f"##### 🟢 Top {top_n} Gainers")
            st.dataframe(g, use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with cl:
            st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
            st.markdown(f"##### 🔴 Top {top_n} Losers")
            st.dataframe(l, use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)
        valid2 = valid.copy()
        valid2["_heat"] = valid2["_pct"].abs().clip(lower=0.01)
        valid2 = valid2[valid2["_heat"] > 0]
        if not valid2.empty:
            try:
                fig_h = px.treemap(valid2, path=["Sector","Company"], values="_heat", color="_pct",
                    color_continuous_scale=["#ef4444","#f59e0b","#10b981"],
                    color_continuous_midpoint=0,
                    title="Heatmap — % Change",
                    hover_data={"Price (₹)": True, "Change (%)": True, "_heat": False})
                fig_h.update_layout(template=PLT, height=500, **PLT_LAYOUT)
                st.plotly_chart(fig_h, use_container_width=True)
            except Exception as e: st.warning(f"⚠️ {e}")
    else: st.info("Not enough live data.")

# ================================================================
# PAGE 5 — P&L CALCULATOR
# ================================================================
elif page == "🧮 P&L Calculator":
    page_header("🧮", "P&L Calculator", "SIMULATED", "badge-sim",
                "Nifty impact on your holdings")
    hist_c  = fetch_ticker("^NSEI", "5d")
    live_ok = False
    cp = 22500.0; ch = 0.0; pt = 0.0
    if not hist_c.empty and len(hist_c) >= 2:
        cp      = safe_float(hist_c["Close"].iloc[-1], 22500.0)
        pp      = safe_float(hist_c["Close"].iloc[-2], cp)
        ch      = cp - pp
        pt      = (ch / pp * 100) if pp != 0 else 0.0
        live_ok = True
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    cl, cr = st.columns(2)
    with cl:
        st.markdown("##### 📊 Nifty Movement")
        ab = st.number_input("Base Nifty",   value=float(round(cp, 2)), step=50.0, min_value=1.0)
        ac = st.number_input("Change (pts)", value=-200.0, step=10.0)
        an = ab + ac
        ap = (ac / ab * 100) if ab != 0 else 0.0
        st.info(f"📌 Assumed: **{ap:+.2f}%** → **₹{an:,.2f}**")
        if live_ok:
            st.dataframe(pd.DataFrame({
                "Metric":    ["Base","Change","% Change","New"],
                "🟢 Actual":  [f"₹{cp:,.2f}",f"{ch:+.2f}",f"{pt:+.2f}%",f"₹{cp:,.2f}"],
                "🟡 Assumed": [f"₹{ab:,.2f}",f"{ac:+.2f}",f"{ap:+.2f}%",f"₹{an:,.2f}"],
            }), use_container_width=True, hide_index=True)
    with cr:
        st.markdown("##### 💼 Your Stock")
        cos = ["-- Custom --"] + nifty50_df["name"].tolist()
        sc  = st.selectbox("Company", cos)
        if sc != "-- Custom --":
            m  = nifty50_df[nifty50_df["name"] == sc]
            db = float(m["beta"].iloc[0]) if not m.empty else 1.0
        else:
            db = 1.0
            sc = st.text_input("Stock Name", "My Stock")
        sp   = st.number_input("Price (₹)", value=100.0, min_value=0.01, step=10.0)
        qty  = st.number_input("Quantity",  value=10, min_value=1)
        beta = st.slider("Beta", 0.0, 3.0, float(round(db, 1)), 0.1)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    ca2, cs2 = st.columns(2)
    with ca2:
        st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
        st.markdown("##### 🟢 Actual Impact")
        if live_ok:
            a = calc_impact(pt, sp, qty, beta)
            st.metric("Stock %",   f"{a[0]:+.2f}%")
            st.metric("New Price", f"₹{a[2]:,.2f}", delta=f"₹{a[1]:+.2f}")
            st.metric("Portfolio", f"₹{a[4]:,.2f}", delta=f"₹{a[5]:+.2f}")
            show_pl(a[5])
        else:
            st.info("Live data unavailable.")
        st.markdown("</div>", unsafe_allow_html=True)
    with cs2:
        st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
        st.markdown("##### 🟡 Assumed Impact")
        b = calc_impact(ap, sp, qty, beta)
        st.metric("Stock %",   f"{b[0]:+.2f}%")
        st.metric("New Price", f"₹{b[2]:,.2f}", delta=f"₹{b[1]:+.2f}")
        st.metric("Portfolio", f"₹{b[4]:,.2f}", delta=f"₹{b[5]:+.2f}")
        show_pl(b[5])
        st.markdown("</div>", unsafe_allow_html=True)

# ================================================================
# PAGE 6 — STOCK CHART LOOKUP
# ================================================================
elif page == "🔍 Stock Chart Lookup":
    page_header("🔍", "Stock Chart Lookup", "LIVE", "badge-live")
    name_map = {s["name"]: s["symbol"] for s in NIFTY50}
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    c_sel, c_per = st.columns([3, 1])
    with c_sel: sel_name = st.selectbox("Select Company", list(name_map.keys()))
    with c_per: p_lk     = st.selectbox("Period", ["1mo","3mo","6mo","1y","2y"], index=2, key="lk_p")
    sel_sym = name_map[sel_name]
    h_lk    = fetch_ticker(sel_sym, period=p_lk)
    st.markdown("</div>", unsafe_allow_html=True)
    if h_lk.empty:
        st.warning("⚠️ Could not fetch data for this stock.")
    else:
        cp = safe_float(h_lk["Close"].iloc[-1])
        pp = safe_float(h_lk["Close"].iloc[-2], cp) if len(h_lk) >= 2 else cp
        ch = cp - pp; pt = (ch/pp*100) if pp != 0 else 0.0
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Price",       f"₹{cp:,.2f}")
        c2.metric("Change",      f"{ch:+.2f}")
        c3.metric("% Change",    f"{pt:+.2f}%")
        c4.metric("Period High", f"₹{safe_float(h_lk['High'].max()):,.2f}")
        c5.metric("Period Low",  f"₹{safe_float(h_lk['Low'].min()):,.2f}")
        h_lk["MA20"] = h_lk["Close"].rolling(20).mean()
        h_lk["MA50"] = h_lk["Close"].rolling(50).mean()
        st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
        try:
            fig_lk = go.Figure()
            fig_lk.add_trace(go.Candlestick(x=h_lk.index, open=h_lk["Open"],
                high=h_lk["High"], low=h_lk["Low"], close=h_lk["Close"], name=sel_name,
                increasing_line_color="#10b981", decreasing_line_color="#ef4444"))
            fig_lk.add_trace(go.Scatter(x=h_lk.index, y=h_lk["MA20"], mode="lines",
                name="MA20", line=dict(color="#f59e0b", width=1.5, dash="dot")))
            fig_lk.add_trace(go.Scatter(x=h_lk.index, y=h_lk["MA50"], mode="lines",
                name="MA50", line=dict(color="#6366f1", width=1.5, dash="dash")))
            fig_lk.update_layout(title=f"{sel_name} — {p_lk}", template=PLT,
                height=500, xaxis_rangeslider_visible=False, **PLT_LAYOUT)
            st.plotly_chart(fig_lk, use_container_width=True)
        except Exception as e: st.warning(f"⚠️ {e}")
        if "Volume" in h_lk.columns:
            vd = h_lk[h_lk["Volume"] > 0]
            if not vd.empty:
                try:
                    fig_v2 = px.bar(vd, x=vd.index, y="Volume", title="Volume",
                        template=PLT, height=220, color_discrete_sequence=["#6366f1"])
                    fig_v2.update_layout(**PLT_LAYOUT)
                    st.plotly_chart(fig_v2, use_container_width=True)
                except Exception as e: st.warning(f"⚠️ {e}")
        st.markdown("</div>", unsafe_allow_html=True)

# ================================================================
# PAGE 7 — TIME MACHINE
# ================================================================
elif page == "⏰ Time Machine":
    page_header("⏰", "Time Machine", "HISTORICAL", "badge-hist",
                "Travel to any past trading date")
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns([2,1])
    with c1:
        presets = list(FAMOUS_DATES.keys())
        preset  = st.selectbox("Quick Select", ["Custom Date"] + presets)
    with c2:
        default_date = FAMOUS_DATES[preset] if preset != "Custom Date" else date(2020, 3, 23)
        target_date  = st.date_input("Travel to date", value=default_date,
            min_value=date(2019,1,1), max_value=date.today())
    st.markdown("</div>", unsafe_allow_html=True)
    with st.spinner("⏳ Loading 5-year history (first load ~30s)…"):
        all_hist = fetch_all_history()
    if not all_hist:
        st.error("❌ Could not fetch historical data.")
    else:
        snap = tm_get_snapshot(all_hist, target_date)
        if snap.empty:
            st.warning("⚠️ No data found near that date. Try a different date.")
        else:
            st.success(f"✅ Snapshot near **{target_date}** ({len(snap)} stocks)")
            st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
            st.dataframe(snap.reset_index(), use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)
            try:
                fig_tm = px.bar(snap.reset_index(), x="Symbol", y="Close",
                    color="Close", color_continuous_scale="Blues",
                    title=f"Closing Prices — {target_date}",
                    template=PLT, height=400)
                fig_tm.update_layout(**PLT_LAYOUT)
                st.plotly_chart(fig_tm, use_container_width=True)
            except Exception as e: st.warning(f"⚠️ {e}")
            try:
                fig_sec = px.box(snap.reset_index(), x="Sector", y="Close",
                    title=f"Sector Distribution — {target_date}",
                    template=PLT, height=380, color="Sector")
                fig_sec.update_layout(**PLT_LAYOUT)
                st.plotly_chart(fig_sec, use_container_width=True)
            except Exception as e: st.warning(f"⚠️ {e}")

# ================================================================
# PAGE 8 — SCENARIO ENGINE
# ================================================================
elif page == "🧪 Scenario Engine":
    page_header("🧪", "Scenario Engine", "HISTORICAL SIM", "badge-sim",
                "How did stocks react to macro events?")
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: event_key = st.selectbox("Macro Event", list(MACRO_EVENTS.keys()))
    with c2: as_of = st.date_input("Use data up to",
            value=date(2024,1,1), min_value=date(2019,1,1), max_value=date.today())
    st.info(f"ℹ️ **{event_key}** — {MACRO_EVENTS[event_key]['desc']}")
    st.markdown("</div>", unsafe_allow_html=True)
    with st.spinner("⏳ Loading history & computing…"):
        all_hist = fetch_all_history()
    if not all_hist:
        st.error("❌ Could not fetch data.")
    else:
        result_df = tm_scenario(all_hist, event_key, as_of)
        if result_df.empty:
            st.warning("⚠️ Not enough historical occurrences. Try a different event or range.")
        else:
            st.success(f"✅ Found {len(result_df)} stocks with data")
            st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
            st.dataframe(result_df.reset_index(), use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)
            try:
                top10 = result_df.head(10).reset_index()
                bot10 = result_df.tail(10).reset_index()
                comb  = pd.concat([top10, bot10]).drop_duplicates(subset=["Symbol"])
                fig_sc = px.bar(comb, x="Symbol", y="Avg Return",
                    color="Avg Return",
                    color_continuous_scale=["#ef4444","#f59e0b","#10b981"],
                    color_continuous_midpoint=0, error_y="Std Dev",
                    title=f"Top & Bottom Reactors — {event_key}",
                    template=PLT, height=420,
                    hover_data=["Name","Sector","Best %","Worst %","Data Pts"])
                fig_sc.update_layout(**PLT_LAYOUT)
                st.plotly_chart(fig_sc, use_container_width=True)
            except Exception as e: st.warning(f"⚠️ {e}")

# ================================================================
# PAGE 9 — PAPER PORTFOLIO (backtest)
# ================================================================
elif page == "💼 Paper Portfolio":
    page_header("💼", "Paper Portfolio", "BACKTESTING", "badge-sim",
                "Hypothetical past investment")
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: invest_date = st.date_input("Invest Date", value=date(2020,4,1),
            min_value=date(2019,1,1), max_value=date.today() - timedelta(days=7))
    with c2: end_date = st.date_input("Exit Date", value=date(2024,1,1),
            min_value=date(2019,1,2), max_value=date.today())
    with c3: investment = st.number_input("Total Investment (₹)", value=100000, step=10000, min_value=1000)
    st.markdown("</div>", unsafe_allow_html=True)
    if end_date <= invest_date:
        st.error("❌ Exit date must be after invest date.")
    else:
        st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
        all_names  = [s["name"] for s in NIFTY50]
        selected   = st.multiselect("Stocks (equal allocation)", all_names, default=all_names[:10])
        sym_lookup = {s["name"]: s["symbol"] for s in NIFTY50}
        sel_syms   = [sym_lookup[n] for n in selected if n in sym_lookup]
        st.markdown("</div>", unsafe_allow_html=True)
        if not sel_syms:
            st.warning("Select at least one stock.")
        else:
            with st.spinner("⏳ Computing portfolio…"):
                all_hist = fetch_all_history()
                result   = tm_paper_portfolio(all_hist, invest_date, end_date, float(investment), sel_syms)
            if result is None:
                st.error("❌ Could not compute. Check dates or data availability.")
            else:
                c1m,c2m,c3m,c4m = st.columns(4)
                c1m.metric("Invested",  f"₹{result['invested']:,.0f}")
                c2m.metric("Final",     f"₹{result['final']:,.0f}", delta=f"₹{result['abs_pl']:+,.0f}")
                c3m.metric("Return",    f"{result['ret_pct']:+.2f}%")
                c4m.metric("CAGR",      f"{result['cagr']:+.2f}%")
                st.caption(f"⏱️ Duration: {result['dur']}")
                show_pl(result["abs_pl"])
                st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
                disp_pf = result["pf_df"].drop(columns=["_pl"], errors="ignore")
                st.dataframe(disp_pf, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
                if not result["growth"].empty:
                    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
                    try:
                        fig_g = go.Figure()
                        fig_g.add_trace(go.Scatter(
                            x=result["growth"].index, y=result["growth"].values,
                            mode="lines", fill="tozeroy", name="Portfolio Value",
                            line=dict(color="#10b981", width=2.5),
                            fillcolor="rgba(16,185,129,0.1)"))
                        fig_g.add_hline(y=result["invested"],
                            line_dash="dash", line_color="#f59e0b",
                            annotation_text=f"Invested ₹{result['invested']:,.0f}")
                        fig_g.update_layout(title="Portfolio Growth", template=PLT,
                            height=420, xaxis_title="Date", yaxis_title="Value (₹)",
                            **PLT_LAYOUT)
                        st.plotly_chart(fig_g, use_container_width=True)
                    except Exception as e: st.warning(f"⚠️ {e}")
                    st.markdown("</div>", unsafe_allow_html=True)

# ================================================================
# PAGE 10 — MARKET CALENDAR
# ================================================================
elif page == "📅 Market Calendar":
    page_header("📅", "Market Calendar", "NSE", "badge-nse",
                "NSE Trading Calendar & Key Events")
    yr = st.selectbox("Year", [2023, 2024, 2025, 2026], index=3)
    NSE_HOLIDAYS = {
        2023: ["Jan 26","Mar 7","Mar 30","Apr 4","Apr 7","Apr 14","May 1",
               "Jun 28","Aug 15","Oct 2","Oct 24","Nov 14","Nov 27","Dec 25"],
        2024: ["Jan 22","Jan 26","Mar 25","Mar 29","Apr 11","Apr 14","Apr 17",
               "May 1","May 23","Jun 17","Jul 17","Aug 15","Oct 2","Nov 1",
               "Nov 15","Dec 25"],
        2025: ["Jan 26","Feb 26","Mar 14","Apr 10","Apr 14","Apr 18","May 1",
               "Aug 15","Aug 27","Oct 2","Oct 20","Oct 21","Nov 5","Dec 25"],
        2026: ["Jan 26","Mar 20","Apr 2","Apr 3","Apr 10","Apr 14","May 1",
               "Aug 15","Oct 2","Oct 28","Nov 16","Nov 17","Dec 25"],
    }
    holidays = NSE_HOLIDAYS.get(yr, [])
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    st.markdown(f"#### 🗓️ NSE Holidays {yr}")
    if holidays:
        h_cols = st.columns(4)
        for i, h in enumerate(holidays):
            h_cols[i % 4].markdown(f"🔴 {h}")
    else:
        st.info("No holiday data for this year.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    st.markdown("#### 📊 Trading Days Stats")
    import calendar as cal_mod
    total_days   = sum(1 for m in range(1,13)
                       for d in range(1, cal_mod.monthrange(yr,m)[1]+1)
                       if date(yr,m,d).weekday() < 5)
    trading_days = total_days - len(holidays)
    tc1,tc2,tc3  = st.columns(3)
    tc1.metric("Weekdays",     total_days)
    tc2.metric("Holidays",     len(holidays))
    tc3.metric("Trading Days", trading_days)
    st.markdown("</div>", unsafe_allow_html=True)
