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
    page_title="NSE & Nifty 50 — Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Theme & top bar ----
try:
    from utils.theme import inject, inject_topbar
    inject()
except Exception:
    pass

# ---- Auth ----
try:
    from utils.supabase_auth import get_current_user, logout, is_guest, login_nudge
except Exception:
    def get_current_user(): return None
    def logout(): pass
    def is_guest(): return True
    def login_nudge(f=""): st.info("💡 Sign in to save your data.")

user     = get_current_user()
name     = user["full_name"] if user else "Guest"
username = user["email"]     if user else ""

# ---- Sticky top navbar ----
try:
    inject_topbar(user=user)
except Exception:
    pass

# ============================================================
# SIDEBAR
# ============================================================
try:
    st.sidebar.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/NSE_Logo.svg/200px-NSE_Logo.svg.png",
        width=110,
    )
except Exception:
    pass

st.sidebar.markdown(
    "<h3 style='color:#fff;margin:0 0 .4rem 0;font-size:1rem;'>NSE + Time Machine</h3>",
    unsafe_allow_html=True,
)

# Account badge
if user:
    st.sidebar.markdown(
        f"<span class='ui-badge badge-live'>👤 {name}</span>",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("🚪 Sign Out", key="sidebar_logout"):
        logout()
        st.rerun()
else:
    st.sidebar.markdown(
        "<span class='ui-badge badge-hist' style='background:rgba(255,255,255,.15);"
        "color:#e0e7ff!important;border-color:rgba(255,255,255,.25);'>👤 Guest</span>",
        unsafe_allow_html=True,
    )

st.sidebar.markdown("---")
st.sidebar.markdown(
    "<p style='color:#94a3b8;font-size:.72rem;letter-spacing:.06em;margin:0 0 .3rem 0;'>ACCOUNT</p>",
    unsafe_allow_html=True,
)
try:
    st.sidebar.page_link("pages/00_👤_Profile_&_Notifications.py", label="👤 Profile & Notifications")
except Exception:
    pass

if not user:
    try:
        st.sidebar.page_link("pages/00_🖐_Login.py", label="🔐 Sign In / Register")
    except Exception:
        pass

st.sidebar.markdown("---")

# Market status
def is_nse_open():
    try:
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
        if now.weekday() >= 5:
            return False, "Weekend"
        mo = now.replace(hour=9,  minute=15, second=0, microsecond=0)
        mc = now.replace(hour=15, minute=30, second=0, microsecond=0)
        if mo <= now <= mc:   return True,  "Open"
        elif now < mo:        return False, "Pre-Market"
        else:                 return False, "Closed"
    except Exception:
        return False, "Unknown"

market_open, market_status = is_nse_open()

try:
    ist_tz  = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist_tz)
    st.sidebar.caption(f"⏰ {now_ist.strftime('%d %b %Y, %I:%M %p')} IST")
except Exception:
    pass

if market_open:
    st.sidebar.markdown(
        "<span class='ui-badge badge-live'>● MARKET OPEN</span>",
        unsafe_allow_html=True,
    )
else:
    st.sidebar.markdown(
        f"<span class='ui-badge badge-red'>● {market_status}</span>",
        unsafe_allow_html=True,
    )

st.sidebar.markdown("---")
st.sidebar.caption("📊 Data: Yahoo Finance")
st.sidebar.caption("⚠️ Educational use only")

# ============================================================
# CONSTANTS
# ============================================================
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
    "Rupee depreciates 5%":   {"desc":"USD/INR rises ~5%",         "proxy":"USDINR=X","lo":0.04, "hi":0.08},
    "Rupee appreciates 3%":   {"desc":"USD/INR falls ~3%",         "proxy":"USDINR=X","lo":-0.05,"hi":-0.02},
    "Crude oil spikes +10%":  {"desc":"WTI crude rises ~10%",       "proxy":"CL=F",    "lo":0.08, "hi":0.15},
    "Crude oil crashes -15%": {"desc":"WTI crude falls ~15%",       "proxy":"CL=F",    "lo":-0.20,"hi":-0.10},
    "Gold rallies +5%":       {"desc":"Gold futures rise ~5%",      "proxy":"GC=F",    "lo":0.04, "hi":0.08},
    "Nifty flash crash -5%":  {"desc":"Nifty 50 falls ~5% in week", "proxy":"^NSEI",   "lo":-0.08,"hi":-0.04},
    "Nifty bull run +5%":     {"desc":"Nifty 50 rises ~5% in week", "proxy":"^NSEI",   "lo":0.04, "hi":0.08},
}

FAMOUS_DATES = {
    "🟥 COVID Crash — Mar 23 2020":    date(2020,3,23),
    "🟢 COVID Recovery — Apr 7 2020":  date(2020,4,7),
    "💥 Russia-Ukraine — Feb 24 2022": date(2022,2,24),
    "💰 RBI Rate Hike — May 4 2022":   date(2022,5,4),
    "🏆 Union Budget — Feb 1 2023":    date(2023,2,1),
    "⬆️ All-time High — Sep 27 2024": date(2024,9,27),
}

PLT = "plotly_white"
PLT_LAYOUT = dict(
    paper_bgcolor="#ffffff", plot_bgcolor="#fafafa",
    font=dict(color="#1e293b", family="Inter, sans-serif", size=12),
    title_font=dict(size=15, color="#0f172a", family="Inter, sans-serif"),
    margin=dict(l=16, r=16, t=48, b=16),
    legend=dict(
        font=dict(color="#1e293b", size=12),
        bgcolor="rgba(255,255,255,0.85)", bordercolor="#e2e8f0", borderwidth=1,
        orientation="h", yanchor="bottom", y=1.02,
    ),
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


# ============================================================
# HELPERS
# ============================================================
def safe_float(val, default=0.0):
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default


def hero(icon, title, badge_html, sub=""):
    sub_html = (
        f"<div class='hero-sub'>{badge_html}{('&nbsp;&nbsp;' + sub) if sub else ''}</div>"
        if (badge_html or sub) else ""
    )
    st.markdown(
        f"""
        <div class="hero-banner">
          <div class="hero-icon">{icon}</div>
          <div>
            <div class="hero-title">{title}</div>
            {sub_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sec(label):
    st.markdown(f"<p class='sec-label'>{label}</p>", unsafe_allow_html=True)


def divider():
    st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)


@st.cache_data(ttl=300)
def fetch_ticker(symbol, period="3mo"):
    try:
        h = yf.Ticker(symbol).history(period=period, auto_adjust=True)
        if h is not None and not h.empty:
            h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
            return h
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_batch(period="5d"):
    try:
        raw = yf.download(
            SYMBOLS, period=period, auto_adjust=True,
            progress=False, group_by="ticker", threads=True,
        )
        if raw is None or raw.empty:
            return pd.DataFrame()
        if isinstance(raw.index, pd.DatetimeIndex):
            raw.index = raw.index.tz_localize(None).normalize()
        return raw
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def fetch_all_history():
    result = {}
    for sym in SYMBOLS + ["USDINR=X", "CL=F", "GC=F", "^NSEI"]:
        try:
            h = yf.Ticker(sym).history(period="5y", auto_adjust=True)
            if h is not None and not h.empty:
                h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
                result[sym] = h
        except Exception:
            pass
    return result


def _extract_series(raw, sym, col="Close"):
    if raw is None or raw.empty:
        return pd.Series(dtype=float)
    try:
        cols = raw.columns
        if isinstance(cols, pd.MultiIndex):
            if col in cols.get_level_values(0) and sym in cols.get_level_values(1):
                return raw[col][sym].dropna()
            if sym in cols.get_level_values(0) and col in cols.get_level_values(1):
                return raw[sym][col].dropna()
        elif col in raw.columns:
            return raw[col].dropna()
    except Exception:
        pass
    return pd.Series(dtype=float)


def get_curr_prev(raw, sym):
    s = _extract_series(raw, sym)
    if len(s) >= 2: return safe_float(s.iloc[-1]), safe_float(s.iloc[-2])
    if len(s) == 1: return safe_float(s.iloc[0]), None
    return None, None


def build_stock_rows(raw):
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
            "_curr": curr, "_pct": pct,
        })
    return pd.DataFrame(rows)


def safe_sort(df, col, ascending=True):
    try:
        num = pd.to_numeric(df[col], errors="coerce").reset_index(drop=True)
        df2 = df.reset_index(drop=True)
        if num.isna().all(): return df2
        order = num.argsort(kind="stable")
        if not ascending:
            nv = int(num.notna().sum())
            order = list(order[:nv][::-1]) + list(order[nv:])
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
    if   pl > 0: st.success(f"↑ GAIN  ₹{pl:,.2f}")
    elif pl < 0: st.error(f"↓ LOSS  ₹{abs(pl):,.2f}")
    else:        st.info("— No Change")


def _nearest_row(df, target, window=4):
    for delta in range(0, window + 1):
        for sign in ([0] if delta == 0 else [1, -1]):
            cand = target + pd.Timedelta(days=delta * sign)
            mask = df.index.normalize() == cand.normalize()
            if mask.any():
                return df[mask].iloc[0]
    return None


def tm_get_snapshot(all_hist, target):
    ts = pd.Timestamp(target)
    meta_map = {s["symbol"]: s for s in NIFTY50}
    rows = []
    for sym in SYMBOLS:
        if sym not in all_hist: continue
        row = _nearest_row(all_hist[sym], ts)
        if row is None: continue
        meta = meta_map.get(sym, {})
        rows.append({
            "Symbol": sym.replace(".NS", ""), "Name": meta.get("name", sym),
            "Sector": meta.get("sector", "?"),
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
    rows = []; idx_labels = []; total_inv = total_final = 0.0
    for sym in symbols_to_use:
        short = sym.replace(".NS", "")
        if short not in buy.index: continue
        bp = safe_float(buy.loc[short, "Close"])
        if bp <= 0: continue
        shares = alloc / bp
        sp_val = safe_float(sell.loc[short, "Close"]) if short in sell.index else np.nan
        pl  = (sp_val - bp) * shares if pd.notna(sp_val) else np.nan
        ret = (sp_val - bp) / bp * 100 if pd.notna(sp_val) else np.nan
        rows.append({
            "Buy ₹":    round(bp, 2),
            "Shares":   round(shares, 3),
            "Sell ₹":   round(sp_val, 2) if pd.notna(sp_val) else "N/A",
            "P&L ₹":    round(pl, 2)     if pd.notna(pl)     else "N/A",
            "Return %": round(ret, 2)   if pd.notna(ret)    else "N/A",
            "_pl": pl,
        })
        idx_labels.append(short)
        total_inv += alloc
        if pd.notna(sp_val):
            total_final += sp_val * shares
    if not rows: return None
    pf_df   = pd.DataFrame(rows, index=idx_labels)
    abs_pl  = total_final - total_inv
    ret_pct = (abs_pl / total_inv * 100) if total_inv > 0 else 0.0
    days    = (end_date - invest_date).days
    years   = days / 365.25
    cagr    = (
        ((total_final / total_inv) ** (1 / years) - 1) * 100
        if (total_inv > 0 and total_final > 0 and years > 0.02) else 0.0
    )
    dur = f"{days//365}y {days%365}d" if days >= 365 else f"{days} days"
    buy_prices = {}
    for sym in symbols_to_use:
        short = sym.replace(".NS", "")
        if short not in buy.index: continue
        bp = safe_float(buy.loc[short, "Close"])
        if bp > 0: buy_prices[sym] = alloc / bp
    growth = {}
    for dt in pd.date_range(pd.Timestamp(invest_date), pd.Timestamp(end_date), freq="W"):
        val = 0.0
        for sym, sh in buy_prices.items():
            df_s = all_hist.get(sym, pd.DataFrame())
            if df_s.empty: continue
            row = _nearest_row(df_s, dt, window=5)
            if row is not None:
                val += safe_float(row.get("Close", 0)) * sh
        if val > 0: growth[dt] = val
    return {
        "pf_df": pf_df, "growth": pd.Series(growth),
        "invested": total_inv, "final": total_final,
        "abs_pl": abs_pl, "ret_pct": ret_pct, "cagr": cagr, "dur": dur,
    }


def tm_scenario(all_hist, event_key, as_of_date):
    ev = MACRO_EVENTS[event_key]
    cutoff = pd.Timestamp(as_of_date)
    proxy = ev["proxy"]
    if proxy not in all_hist: return pd.DataFrame()
    pxy = all_hist[proxy][all_hist[proxy].index <= cutoff]
    if len(pxy) < 10: return pd.DataFrame()
    try:
        weekly_ret = pxy["Close"].resample("W-FRI").last().dropna().pct_change().dropna()
    except Exception:
        return pd.DataFrame()
    event_wks = weekly_ret[(weekly_ret >= ev["lo"]) & (weekly_ret <= ev["hi"])].index
    event_wks = event_wks[event_wks <= cutoff]
    if len(event_wks) < 1: return pd.DataFrame()
    meta_map = {s["symbol"]: s for s in NIFTY50}
    rows = []
    for sym in SYMBOLS:
        if sym not in all_hist: continue
        df_s = all_hist[sym][all_hist[sym].index <= cutoff]
        if len(df_s) < 5: continue
        try:
            wk_ret = df_s["Close"].resample("W-FRI").last().dropna().pct_change().dropna() * 100
        except Exception:
            continue
        bucket = []
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
            "Name":       meta.get("name", sym),
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


# ============================================================
# MAIN TABS
# ============================================================
TAB_LABELS = [
    "🏦 Market Overview",
    "📈 Nifty 50 Index",
    "🏢 All 50 Companies",
    "🏆 Gainers & Losers",
    "🧮 P&L Calculator",
    "🔍 Stock Chart",
    "⏰ Time Machine",
    "🧪 Scenario Engine",
    "💼 Paper Portfolio",
    "📰 News Sentiment",
    "🤖 ML Predictions",
    "🎮 Paper Trading",
    "📅 Market Calendar",
]

tabs = st.tabs(TAB_LABELS)

# ── 0: Market Overview ──────────────────────────────────────
with tabs[0]:
    hero("🏦", "NSE Market Overview",
         "<span class='ui-badge badge-nse'>NSE INDIA</span>",
         "National Stock Exchange — Live Indices")
    if market_open:
        st.success("✅ NSE is **OPEN** — Mon–Fri 9:15 AM – 3:30 PM IST")
    else:
        st.error(f"❌ NSE is **CLOSED** — {market_status}")
    sec("NSE Indices Snapshot")
    idx_rows = []
    with st.spinner("Fetching indices…"):
        for idx in NSE_INDICES:
            h = fetch_ticker(idx["symbol"], "5d")
            if not h.empty and len(h) >= 2:
                c  = safe_float(h["Close"].iloc[-1])
                p  = safe_float(h["Close"].iloc[-2], c)
                ch = c - p
                pt = round(ch / p * 100, 2) if p != 0 else 0.0
                idx_rows.append({
                    "Index": idx["name"], "Value": f"₹{c:,.2f}",
                    "Change (pts)": f"{ch:+.2f}", "Change (%)": f"{pt:+.2f}%",
                    "High": f"₹{safe_float(h['High'].max()):,.2f}",
                    "Low":  f"₹{safe_float(h['Low'].min()):,.2f}",
                    "_pct": pt,
                })
            else:
                idx_rows.append({"Index": idx["name"], "Value": "N/A",
                    "Change (pts)": "N/A", "Change (%)": "N/A",
                    "High": "N/A", "Low": "N/A", "_pct": None})
    idx_df = pd.DataFrame(idx_rows)
    st.dataframe(idx_df.drop(columns=["_pct"]), use_container_width=True, hide_index=True)
    valid_idx = idx_df[idx_df["_pct"].notna()].copy()
    if not valid_idx.empty:
        try:
            fig_b = px.bar(
                valid_idx, x="Index", y="_pct",
                color="_pct", color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
                color_continuous_midpoint=0, text="Change (%)",
                title="Today's % Change by Index", template=PLT, height=320,
                labels={"_pct": "% Change", "Index": "Index"},
            )
            fig_b.update_traces(textposition="outside", marker_line_width=0,
                                textfont=dict(color="#1e293b", size=11))
            fig_b.update_layout(**PLT_LAYOUT, coloraxis_showscale=False)
            style_fig(fig_b)
            st.plotly_chart(fig_b, use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ Chart error: {e}")
    divider()
    sec("Trend Comparison")
    c_per, c_idx = st.columns([1, 3])
    with c_per:
        p_sel = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1, key="idx_p")
    with c_idx:
        sel_idx = st.multiselect(
            "Indices", [i["name"] for i in NSE_INDICES],
            default=["Nifty 50", "Nifty Bank", "Nifty IT"],
        )
    sym_map = {i["name"]: i for i in NSE_INDICES}
    if sel_idx:
        fig_m = go.Figure()
        for ni in sel_idx:
            meta = sym_map.get(ni)
            if not meta: continue
            h = fetch_ticker(meta["symbol"], p_sel)
            if h.empty: continue
            norm = h["Close"] / h["Close"].iloc[0] * 100
            fig_m.add_trace(go.Scatter(
                x=h.index, y=norm, name=ni,
                mode="lines", line=dict(color=meta["color"], width=2),
            ))
        fig_m.add_hline(y=100, line_dash="dot", line_color="#94a3b8")
        fig_m.update_layout(**PLT_LAYOUT,
            title="Normalised Performance (base=100)", height=380,
            xaxis_title="Date", yaxis_title="Indexed Value",
        )
        style_fig(fig_m)
        st.plotly_chart(fig_m, use_container_width=True)

# ── 1: Nifty 50 Index ────────────────────────────────────────
with tabs[1]:
    hero("📈", "Nifty 50 Index",
         "<span class='ui-badge badge-live'>LIVE</span>", "^NSEI — NSE Flagship Index")
    c1, c2 = st.columns([1, 3])
    with c1:
        n_period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2, key="nf_p")
    with c2:
        chart_type = st.radio("Chart", ["Line", "Candlestick", "Area"], horizontal=True, key="nf_ct")
    with st.spinner("Fetching Nifty 50…"):
        nifty = fetch_ticker("^NSEI", n_period)
    if nifty.empty:
        st.error("❌ Could not fetch Nifty 50 data.")
    else:
        c  = safe_float(nifty["Close"].iloc[-1])
        p  = safe_float(nifty["Close"].iloc[-2]) if len(nifty) > 1 else c
        ch = c - p
        pt = ch / p * 100 if p else 0
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Last",        f"₹{c:,.2f}")
        m2.metric("Change",      f"{ch:+.2f}",  delta=f"{pt:+.2f}%")
        m3.metric("Period High", f"₹{safe_float(nifty['High'].max()):,.2f}")
        m4.metric("Period Low",  f"₹{safe_float(nifty['Low'].min()):,.2f}")
        m5.metric("Avg Volume",  f"{int(nifty['Volume'].mean()):,}")
        divider()
        fig = go.Figure()
        if chart_type == "Candlestick":
            fig.add_trace(go.Candlestick(
                x=nifty.index, open=nifty["Open"], high=nifty["High"],
                low=nifty["Low"], close=nifty["Close"], name="Nifty 50",
                increasing_line_color="#10b981", decreasing_line_color="#ef4444",
            ))
        elif chart_type == "Area":
            fig.add_trace(go.Scatter(
                x=nifty.index, y=nifty["Close"], fill="tozeroy", name="Nifty 50",
                line=dict(color="#6366f1", width=2), fillcolor="rgba(99,102,241,0.12)",
            ))
        else:
            fig.add_trace(go.Scatter(
                x=nifty.index, y=nifty["Close"], name="Nifty 50",
                line=dict(color="#6366f1", width=2.5),
            ))
        fig.update_layout(**PLT_LAYOUT,
            title=f"Nifty 50 — {n_period}", height=460,
            xaxis_title="Date", yaxis_title="Index Value",
        )
        style_fig(fig)
        st.plotly_chart(fig, use_container_width=True)

# ── 2: All 50 Companies ─────────────────────────────────────
with tabs[2]:
    hero("🏢", "All 50 Companies",
         "<span class='ui-badge badge-nse'>NSE</span>", "Live prices for all Nifty 50 stocks")
    sec("Sector Filter")
    sel_sec = st.selectbox("Sector", sectors, key="all_sec")
    with st.spinner("Fetching prices…"):
        raw = fetch_batch("5d")
    df_rows = build_stock_rows(raw)
    if sel_sec != "All":
        df_rows = df_rows[df_rows["Sector"] == sel_sec]
    disp = df_rows.drop(columns=["_curr", "_pct"], errors="ignore")
    st.dataframe(disp, use_container_width=True, hide_index=True)
    if not df_rows.empty:
        valid = df_rows[df_rows["_pct"].notna()].copy()
        if not valid.empty:
            try:
                fig = px.bar(
                    valid, x="Symbol", y="_pct",
                    color="_pct", color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
                    color_continuous_midpoint=0, text="Change (%)",
                    title="1-Day % Change", template=PLT, height=380,
                )
                fig.update_traces(textposition="outside", marker_line_width=0)
                fig.update_layout(**PLT_LAYOUT, coloraxis_showscale=False)
                style_fig(fig)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"⚠️ Chart error: {e}")

# ── 3: Gainers & Losers ─────────────────────────────────────
with tabs[3]:
    hero("🏆", "Gainers & Losers", "<span class='ui-badge badge-live'>TODAY</span>")
    with st.spinner("Fetching…"):
        raw = fetch_batch("5d")
    df_rows = build_stock_rows(raw)
    valid   = df_rows[df_rows["_pct"].notna()].copy()
    top_n   = st.slider("Top N", 3, 10, 5, key="gl_n")
    if valid.empty:
        st.warning("⚠️ No data available.")
    else:
        gainers = safe_sort(valid, "_pct", ascending=False).head(top_n)
        losers  = safe_sort(valid, "_pct", ascending=True).head(top_n)
        cg, cl  = st.columns(2)
        with cg:
            sec("🟢 Top Gainers")
            st.dataframe(gainers[["Symbol", "Company", "Price (₹)", "Change (%)"]], use_container_width=True, hide_index=True)
        with cl:
            sec("🔴 Top Losers")
            st.dataframe(losers[["Symbol", "Company", "Price (₹)", "Change (%)"]], use_container_width=True, hide_index=True)
        try:
            combined = pd.concat([gainers, losers]).drop_duplicates(subset="Symbol")
            combined = combined[combined["_pct"].notna()]
            fig = px.bar(
                combined, x="Symbol", y="_pct",
                color="_pct", color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
                color_continuous_midpoint=0, text="Change (%)",
                title="Gainers vs Losers", template=PLT, height=380,
            )
            fig.update_traces(textposition="outside", marker_line_width=0)
            fig.update_layout(**PLT_LAYOUT, coloraxis_showscale=False)
            style_fig(fig)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ Chart error: {e}")

# ── 4: P&L Calculator ───────────────────────────────────────
with tabs[4]:
    hero("🧮", "P&L Calculator",
         "<span class='ui-badge badge-sim'>SIMULATOR</span>", "Calculate profit / loss")
    with st.spinner("Fetching live prices…"):
        raw = fetch_batch("5d")
    stock_names = [s["name"] for s in NIFTY50]
    c1, c2, c3  = st.columns(3)
    with c1:
        sel_name = st.selectbox("Stock", stock_names, key="pl_s")
    sel_s = next(s for s in NIFTY50 if s["name"] == sel_name)
    curr, _ = get_curr_prev(raw, sel_s["symbol"])
    lp = curr if curr else 0.0
    with c2:
        buy_p = st.number_input(
            "Buy Price (₹)", min_value=0.01,
            value=round(lp, 2) if lp > 0 else 100.0, step=0.5, key="pl_bp",
        )
    with c3:
        qty = st.number_input("Quantity", min_value=1, value=10, step=1, key="pl_q")
    sell_p = st.number_input(
        "Sell / Current Price (₹)", min_value=0.01,
        value=round(lp, 2) if lp > 0 else 100.0, step=0.5, key="pl_sp",
    )
    pl  = (sell_p - buy_p) * qty
    inv = buy_p * qty
    ret = (pl / inv * 100) if inv > 0 else 0
    divider()
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Investment", f"₹{inv:,.2f}")
    mc2.metric("P&L",        f"₹{pl:+,.2f}")
    mc3.metric("Return",     f"{ret:+.2f}%")
    show_pl(pl)
    divider()
    sec("Beta-Adjusted Impact")
    st.caption("Simulate how a Nifty move affects your holding based on beta.")
    ni_col, bv_col = st.columns(2)
    with ni_col:
        nifty_move = st.slider("Nifty Move (%)", -20.0, 20.0, 0.0, 0.5, key="pl_nm")
    with bv_col:
        beta_val = st.number_input("Beta", 0.1, 3.0,
            value=float(sel_s.get("beta", 1.0)), step=0.05, key="pl_bv")
    if nifty_move != 0:
        spct, pchg, nsp, old_val, new_val, pl_beta = calc_impact(
            nifty_move, buy_p, qty, beta_val
        )
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Stock Move",   f"{spct:+.2f}%")
        b2.metric("Price Change", f"₹{pchg:+.2f}")
        b3.metric("New Price",    f"₹{nsp:.2f}")
        b4.metric("P&L Impact",   f"₹{pl_beta:+,.2f}")

# ── 5: Stock Chart ───────────────────────────────────────────
with tabs[5]:
    hero("🔍", "Stock Chart",
         "<span class='ui-badge badge-live'>LIVE</span>", "Detailed chart for any Nifty 50 stock")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        sc_name = st.selectbox("Stock", [s["name"] for s in NIFTY50], key="sc_s")
    with c2:
        sc_per  = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2, key="sc_p")
    with c3:
        sc_ct   = st.radio("Chart", ["Line", "Candlestick", "Area"], horizontal=True, key="sc_ct")
    sc_sym = next(s["symbol"] for s in NIFTY50 if s["name"] == sc_name)
    with st.spinner(f"Fetching {sc_name}…"):
        sc_h = fetch_ticker(sc_sym, sc_per)
    if sc_h.empty:
        st.error("❌ No data found for this stock.")
    else:
        c  = safe_float(sc_h["Close"].iloc[-1])
        p  = safe_float(sc_h["Close"].iloc[-2]) if len(sc_h) > 1 else c
        ch = c - p
        pt = ch / p * 100 if p else 0
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Price",  f"₹{c:,.2f}")
        m2.metric("Change", f"{ch:+.2f}", delta=f"{pt:+.2f}%")
        m3.metric("High",   f"₹{safe_float(sc_h['High'].max()):,.2f}")
        m4.metric("Low",    f"₹{safe_float(sc_h['Low'].min()):,.2f}")
        fig = go.Figure()
        if sc_ct == "Candlestick":
            fig.add_trace(go.Candlestick(
                x=sc_h.index, open=sc_h["Open"], high=sc_h["High"],
                low=sc_h["Low"], close=sc_h["Close"], name=sc_name,
                increasing_line_color="#10b981", decreasing_line_color="#ef4444",
            ))
        elif sc_ct == "Area":
            fig.add_trace(go.Scatter(
                x=sc_h.index, y=sc_h["Close"], fill="tozeroy", name=sc_name,
                line=dict(color="#6366f1", width=2), fillcolor="rgba(99,102,241,0.12)",
            ))
        else:
            fig.add_trace(go.Scatter(
                x=sc_h.index, y=sc_h["Close"], name=sc_name,
                line=dict(color="#6366f1", width=2.5),
            ))
        fig.update_layout(**PLT_LAYOUT,
            title=f"{sc_name} — {sc_per}", height=460,
            xaxis_title="Date", yaxis_title="Price (₹)",
        )
        style_fig(fig)
        st.plotly_chart(fig, use_container_width=True)

# ── 6: Time Machine ──────────────────────────────────────────
with tabs[6]:
    hero("⏰", "Time Machine",
         "<span class='ui-badge badge-hist'>HISTORICAL</span>", "Travel back to any NSE trading day")
    sec("Select Date")
    preset = st.selectbox("Famous dates", ["Custom…"] + list(FAMOUS_DATES.keys()), key="tm_preset")
    if preset == "Custom…":
        tm_date = st.date_input(
            "Date", value=date(2020, 3, 23),
            min_value=date(2010, 1, 1), max_value=date.today(), key="tm_date",
        )
    else:
        tm_date = FAMOUS_DATES[preset]
        st.info(f"📅 Loaded: **{preset}** — {tm_date}")
    if st.button("🚀 Travel to this date", key="tm_go"):
        with st.spinner("Loading historical data…"):
            all_hist = fetch_all_history()
        snap = tm_get_snapshot(all_hist, tm_date)
        if snap.empty:
            st.error("❌ No data for this date. Try a nearby date.")
        else:
            st.success(f"✅ Snapshot for {tm_date}")
            st.dataframe(snap, use_container_width=True)
            try:
                fig = px.bar(
                    snap.reset_index(), x="Symbol", y="Close",
                    color="Close",
                    color_continuous_scale=["#6366f1", "#06b6d4", "#10b981"],
                    title=f"Closing Prices — {tm_date}", template=PLT, height=380,
                )
                fig.update_layout(**PLT_LAYOUT, coloraxis_showscale=False)
                style_fig(fig)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"⚠️ Chart error: {e}")

# ── 7: Scenario Engine ───────────────────────────────────────
with tabs[7]:
    hero("🧪", "Scenario Engine",
         "<span class='ui-badge badge-sim'>SIMULATOR</span>",
         "How do stocks behave during macro events?")
    c1, c2 = st.columns(2)
    with c1:
        ev_key = st.selectbox("Event", list(MACRO_EVENTS.keys()), key="sc_ev")
    with c2:
        sc_asof = st.date_input(
            "As of date", value=date.today(),
            min_value=date(2015, 1, 1), max_value=date.today(), key="sc_asof",
        )
    if st.button("🔍 Analyse", key="sc_run"):
        with st.spinner("Crunching historical data…"):
            all_hist = fetch_all_history()
        sc_df = tm_scenario(all_hist, ev_key, sc_asof)
        if sc_df.empty:
            st.warning("⚠️ Not enough historical data for this scenario.")
        else:
            st.success(f"✅ Found {len(sc_df)} stocks with data for '{ev_key}'")
            st.dataframe(sc_df, use_container_width=True)
            try:
                fig = px.bar(
                    sc_df.reset_index().head(20), x="Symbol", y="Avg Return",
                    color="Avg Return",
                    color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
                    color_continuous_midpoint=0, text="Avg Return",
                    title=f"Avg Weekly Return during '{ev_key}'", template=PLT, height=380,
                )
                fig.update_traces(textposition="outside", texttemplate="%{text:.1f}%")
                fig.update_layout(**PLT_LAYOUT, coloraxis_showscale=False)
                style_fig(fig)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"⚠️ Chart error: {e}")

# ── 8: Paper Portfolio ───────────────────────────────────────
with tabs[8]:
    hero("💼", "Paper Portfolio",
         "<span class='ui-badge badge-sim'>BACKTESTING</span>", "Simulate investing in the past")
    c1, c2, c3 = st.columns(3)
    with c1:
        pp_preset = st.selectbox(
            "Start date preset", ["Custom…"] + list(FAMOUS_DATES.keys()), key="pp_preset",
        )
        if pp_preset == "Custom…":
            pp_start = st.date_input(
                "Buy date", value=date(2020, 3, 23),
                min_value=date(2010, 1, 1),
                max_value=date.today() - timedelta(days=7), key="pp_start",
            )
        else:
            pp_start = FAMOUS_DATES[pp_preset]
    with c2:
        pp_end = st.date_input(
            "Sell date", value=date.today(),
            min_value=date(2010, 1, 8), max_value=date.today(), key="pp_end",
        )
    with c3:
        pp_inv = st.number_input(
            "Investment (₹)", min_value=1000, value=100000, step=5000, key="pp_inv",
        )
    pp_secs = st.multiselect(
        "Sectors to include",
        sorted(nifty50_df["sector"].unique().tolist()),
        default=sorted(nifty50_df["sector"].unique().tolist()),
        key="pp_secs",
    )
    pp_syms = [s["symbol"] for s in NIFTY50 if s["sector"] in pp_secs]
    if st.button("📊 Run Backtest", key="pp_run"):
        if pp_start >= pp_end:
            st.error("❌ Buy date must be before sell date.")
        elif not pp_syms:
            st.warning("⚠️ Select at least one sector.")
        else:
            with st.spinner("Running backtest…"):
                all_hist = fetch_all_history()
            res = tm_paper_portfolio(all_hist, pp_start, pp_end, pp_inv, pp_syms)
            if res is None:
                st.error("❌ Not enough data.")
            else:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Invested",    f"₹{res['invested']:,.0f}")
                m2.metric("Final Value", f"₹{res['final']:,.0f}")
                m3.metric("P&L",         f"₹{res['abs_pl']:+,.0f}", delta=f"{res['ret_pct']:+.1f}%")
                m4.metric("CAGR",        f"{res['cagr']:+.1f}%  ({res['dur']})")
                show_pl(res["abs_pl"])
                divider()
                st.dataframe(res["pf_df"], use_container_width=True)
                if not res["growth"].empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=res["growth"].index, y=res["growth"].values,
                        fill="tozeroy", name="Portfolio Value",
                        line=dict(color="#6366f1", width=2.5),
                        fillcolor="rgba(99,102,241,0.12)",
                    ))
                    fig.add_hline(y=res["invested"], line_dash="dot", line_color="#94a3b8",
                                  annotation_text="Invested")
                    fig.update_layout(**PLT_LAYOUT,
                        title="Portfolio Growth", height=380,
                        xaxis_title="Date", yaxis_title="Value (₹)",
                    )
                    style_fig(fig)
                    st.plotly_chart(fig, use_container_width=True)

# ── 9: News Sentiment ────────────────────────────────────────
with tabs[9]:
    hero("📰", "News Sentiment",
         "<span class='ui-badge badge-nse'>AI POWERED</span>", "Market news sentiment analysis")
    st.info(
        "🚧 **News Sentiment** module coming soon.\n\n"
        "Connect a news API (NewsAPI / Finshots / Moneycontrol) to enable live sentiment scoring."
    )

# ── 10: ML Predictions ───────────────────────────────────────
with tabs[10]:
    hero("🤖", "ML Predictions",
         "<span class='ui-badge badge-sim'>BETA</span>", "Machine learning price predictions")
    st.info("💡 For the full ML Predictions experience, open the dedicated page from the top navigation bar.")
    try:
        st.page_link("pages/04_🤖_ML_Predictions.py", label="🤖 Open ML Predictions Page", icon="🤖")
    except Exception:
        st.markdown("Navigate to **ML Predictions** from the sidebar.")

# ── 11: Paper Trading ────────────────────────────────────────
with tabs[11]:
    hero("🎮", "Paper Trading",
         "<span class='ui-badge badge-sim'>SIMULATOR</span>", "Practice trading without real money")
    st.info("💡 For the full Paper Trading experience, open the dedicated page from the top navigation bar.")
    try:
        st.page_link("pages/06_📝_Paper_Trading.py", label="🎮 Open Paper Trading Page", icon="🎮")
    except Exception:
        st.markdown("Navigate to **Paper Trading** from the sidebar.")

# ── 12: Market Calendar ──────────────────────────────────────
with tabs[12]:
    hero("📅", "Market Calendar",
         "<span class='ui-badge badge-nse'>NSE</span>", "NSE holidays & key market events")
    st.info(
        "🚧 **Market Calendar** module coming soon.\n\n"
        "Will show NSE trading holidays, earnings dates, and RBI policy meeting schedules."
    )
    sec("Known NSE Holidays 2026 (Sample)")
    holidays_2026 = [
        {"Date": "Jan 26", "Day": "Monday",    "Event": "Republic Day"},
        {"Date": "Mar 14", "Day": "Saturday",  "Event": "Holi"},
        {"Date": "Apr 14", "Day": "Tuesday",   "Event": "Dr. Ambedkar Jayanti / Good Friday"},
        {"Date": "May 1",  "Day": "Friday",    "Event": "Maharashtra Day"},
        {"Date": "Aug 15", "Day": "Saturday",  "Event": "Independence Day"},
        {"Date": "Oct 2",  "Day": "Friday",    "Event": "Gandhi Jayanti"},
        {"Date": "Oct 24", "Day": "Saturday",  "Event": "Dussehra"},
        {"Date": "Nov 14", "Day": "Saturday",  "Event": "Diwali Laxmi Pujan"},
        {"Date": "Dec 25", "Day": "Friday",    "Event": "Christmas"},
    ]
    st.dataframe(pd.DataFrame(holidays_2026), use_container_width=True, hide_index=True)
