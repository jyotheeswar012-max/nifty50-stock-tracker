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

from utils.theme import inject
inject()

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

st.sidebar.markdown("<h3 style='color:#fff;margin:0 0 .4rem 0;font-size:1rem;'>NSE + Time Machine</h3>",
                    unsafe_allow_html=True)

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
        "<span class='ui-badge badge-hist' style='background:rgba(255,255,255,.15);color:#e0e7ff!important;border-color:rgba(255,255,255,.25);'>👤 Guest</span>",
        unsafe_allow_html=True,
    )
    try:
        st.sidebar.page_link("pages/00_🔐_Login.py", label="🔐 Sign In / Register")
    except Exception:
        pass

st.sidebar.markdown("---")

page = st.sidebar.radio("", [
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
], label_visibility="collapsed")

try:
    ist_tz  = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist_tz)
    st.sidebar.caption(f"⏰ {now_ist.strftime('%d %b %Y, %I:%M %p')} IST")
except Exception:
    pass


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
if market_open:
    st.sidebar.markdown("<span class='ui-badge badge-live'>● MARKET OPEN</span>",
                        unsafe_allow_html=True)
else:
    st.sidebar.markdown(
        f"<span class='ui-badge badge-red'>● {market_status}</span>",
        unsafe_allow_html=True)

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
    paper_bgcolor="#ffffff",
    plot_bgcolor="#fafafa",
    font=dict(color="#1e293b", family="Inter, sans-serif", size=12),
    title_font=dict(size=15, color="#0f172a", family="Inter, sans-serif"),
    margin=dict(l=16, r=16, t=48, b=16),
    legend=dict(
        font=dict(color="#1e293b", size=12),
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#e2e8f0",
        borderwidth=1,
    ),
)

AXIS_STYLE = dict(
    tickfont=dict(color="#1e293b", size=11, family="Inter, sans-serif"),
    title_font=dict(color="#0f172a", size=12, family="Inter, sans-serif"),
    linecolor="#cbd5e1",
    gridcolor="#f1f5f9",
    zerolinecolor="#cbd5e1",
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
    sub_html = f"<div class='hero-sub'>{badge_html}{('&nbsp;&nbsp;' + sub) if sub else ''}</div>" if (badge_html or sub) else ""
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
        raw = yf.download(SYMBOLS, period=period, auto_adjust=True,
                          progress=False, group_by="ticker", threads=True)
        if raw is None or raw.empty: return pd.DataFrame()
        if isinstance(raw.index, pd.DatetimeIndex):
            raw.index = raw.index.tz_localize(None).normalize()
        return raw
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def fetch_all_history():
    result = {}
    for sym in SYMBOLS + ["USDINR=X","CL=F","GC=F","^NSEI"]:
        try:
            h = yf.Ticker(sym).history(period="5y", auto_adjust=True)
            if h is not None and not h.empty:
                h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
                result[sym] = h
        except Exception:
            pass
    return result


def _extract_series(raw, sym, col="Close"):
    if raw is None or raw.empty: return pd.Series(dtype=float)
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
        pct = (chg/prev*100) if (chg is not None and prev and prev != 0) else None
        rows.append({
            "Symbol":     s["symbol"].replace(".NS",""),
            "Company":    s["name"],
            "Sector":     s["sector"],
            "Beta":       s["beta"],
            "Price (₹)": round(curr,2) if curr is not None else "N/A",
            "Change (₹)": round(chg,2)  if chg  is not None else "N/A",
            "Change (%)": round(pct,2)  if pct  is not None else "N/A",
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
    pchg = sp * (spct/100)
    nsp  = sp + pchg
    return spct, pchg, nsp, sp*qty, nsp*qty, pchg*qty


def show_pl(pl):
    pl = safe_float(pl)
    if   pl > 0: st.success(f"↑ GAIN  ₹{pl:,.2f}")
    elif pl < 0: st.error(f"↓ LOSS  ₹{abs(pl):,.2f}")
    else:        st.info("— No Change")


def _nearest_row(df, target, window=4):
    for delta in range(0, window+1):
        for sign in ([0] if delta == 0 else [1,-1]):
            cand = target + pd.Timedelta(days=delta*sign)
            mask = df.index.normalize() == cand.normalize()
            if mask.any(): return df[mask].iloc[0]
    return None


def tm_get_snapshot(all_hist, target):
    ts = pd.Timestamp(target)
    meta_map = {s["symbol"]: s for s in NIFTY50}
    rows = []
    for sym in SYMBOLS:
        if sym not in all_hist: continue
        row = _nearest_row(all_hist[sym], ts)
        if row is None: continue
        meta = meta_map.get(sym,{})
        rows.append({
            "Symbol": sym.replace(".NS",""), "Name": meta.get("name",sym),
            "Sector": meta.get("sector","?"),
            "Open":  safe_float(row.get("Open",  np.nan)),
            "High":  safe_float(row.get("High",  np.nan)),
            "Low":   safe_float(row.get("Low",   np.nan)),
            "Close": safe_float(row.get("Close", np.nan)),
            "Volume":int(safe_float(row.get("Volume",0))),
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
    rows=[]; idx_labels=[]; total_inv=total_final=0.0
    for sym in symbols_to_use:
        short = sym.replace(".NS","")
        if short not in buy.index: continue
        bp = safe_float(buy.loc[short,"Close"])
        if bp <= 0: continue
        shares = alloc/bp
        sp_val = safe_float(sell.loc[short,"Close"]) if short in sell.index else np.nan
        pl  = (sp_val-bp)*shares   if pd.notna(sp_val) else np.nan
        ret = (sp_val-bp)/bp*100   if pd.notna(sp_val) else np.nan
        rows.append({"Buy ₹":round(bp,2),"Shares":round(shares,3),
                     "Sell ₹":round(sp_val,2) if pd.notna(sp_val) else "N/A",
                     "P&L ₹": round(pl,2)     if pd.notna(pl)     else "N/A",
                     "Return %":round(ret,2)   if pd.notna(ret)    else "N/A",
                     "_pl":pl})
        idx_labels.append(short)
        total_inv += alloc
        if pd.notna(sp_val): total_final += sp_val*shares
    if not rows: return None
    pf_df  = pd.DataFrame(rows, index=idx_labels)
    abs_pl = total_final - total_inv
    ret_pct= (abs_pl/total_inv*100) if total_inv > 0 else 0.0
    days   = (end_date - invest_date).days
    years  = days/365.25
    cagr   = ((total_final/total_inv)**(1/years)-1)*100 \
             if (total_inv>0 and total_final>0 and years>0.02) else 0.0
    dur    = f"{days//365}y {days%365}d" if days>=365 else f"{days} days"
    buy_prices={}
    for sym in symbols_to_use:
        short=sym.replace(".NS","")
        if short not in buy.index: continue
        bp=safe_float(buy.loc[short,"Close"])
        if bp>0: buy_prices[sym]=alloc/bp
    growth={}
    for dt in pd.date_range(pd.Timestamp(invest_date),pd.Timestamp(end_date),freq="W"):
        val=0.0
        for sym,sh in buy_prices.items():
            df_s=all_hist.get(sym,pd.DataFrame())
            if df_s.empty: continue
            row=_nearest_row(df_s,dt,window=5)
            if row is not None: val+=safe_float(row.get("Close",0))*sh
        if val>0: growth[dt]=val
    return {"pf_df":pf_df,"growth":pd.Series(growth),"invested":total_inv,
            "final":total_final,"abs_pl":abs_pl,"ret_pct":ret_pct,
            "cagr":cagr,"dur":dur}


def tm_scenario(all_hist, event_key, as_of_date):
    ev=MACRO_EVENTS[event_key]; cutoff=pd.Timestamp(as_of_date)
    proxy=ev["proxy"]
    if proxy not in all_hist: return pd.DataFrame()
    pxy=all_hist[proxy][all_hist[proxy].index<=cutoff]
    if len(pxy)<10: return pd.DataFrame()
    try:
        weekly_ret=pxy["Close"].resample("W-FRI").last().dropna().pct_change().dropna()
    except Exception: return pd.DataFrame()
    event_wks=weekly_ret[(weekly_ret>=ev["lo"])&(weekly_ret<=ev["hi"])].index
    event_wks=event_wks[event_wks<=cutoff]
    if len(event_wks)<1: return pd.DataFrame()
    meta_map={s["symbol"]:s for s in NIFTY50}
    rows=[]
    for sym in SYMBOLS:
        if sym not in all_hist: continue
        df_s=all_hist[sym][all_hist[sym].index<=cutoff]
        if len(df_s)<5: continue
        try: wk_ret=df_s["Close"].resample("W-FRI").last().dropna().pct_change().dropna()*100
        except Exception: continue
        bucket=[]
        for ew in event_wks:
            lo_w=ew-pd.Timedelta(days=7); hi_w=ew+pd.Timedelta(days=7)
            w_idx=wk_ret.index[(wk_ret.index>=lo_w)&(wk_ret.index<=hi_w)]
            if not w_idx.empty:
                v=wk_ret.get(w_idx[0],np.nan)
                if pd.notna(v): bucket.append(float(v))
        if not bucket: continue
        arr=np.array(bucket); meta=meta_map.get(sym,{})
        rows.append({"Symbol":sym.replace(".NS",""),"Name":meta.get("name",sym),
                     "Sector":meta.get("sector","?"),
                     "Avg Return":round(float(np.mean(arr)),2),
                     "Std Dev":   round(float(np.std(arr)), 2),
                     "Best %":    round(float(np.max(arr)), 2),
                     "Worst %":   round(float(np.min(arr)), 2),
                     "Data Pts":  len(bucket),
                     "Confidence":round(max(0.0,100-float(np.std(arr))*10),1)})
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows).set_index("Symbol").sort_values("Avg Return",ascending=False)


# ============================================================
# PAGE ROUTING
# ============================================================
if page == "🏦 Market Overview":
    hero("🏦", "NSE Market Overview",
         "<span class='ui-badge badge-nse'>NSE INDIA</span>",
         "National Stock Exchange — Live Indices")

    if market_open: st.success("✅ NSE is **OPEN** — Mon–Fri 9:15 AM – 3:30 PM IST")
    else:           st.error(f"❌ NSE is **CLOSED** — {market_status}")

    sec("NSE Indices Snapshot")
    idx_rows = []
    with st.spinner("Fetching indices…"):
        for idx in NSE_INDICES:
            h = fetch_ticker(idx["symbol"],"5d")
            if not h.empty and len(h)>=2:
                c=safe_float(h["Close"].iloc[-1]); p=safe_float(h["Close"].iloc[-2],c)
                ch=c-p; pt=round(ch/p*100,2) if p!=0 else 0.0
                idx_rows.append({"Index":idx["name"],"Value":f"₹{c:,.2f}",
                    "Change (pts)":f"{ch:+.2f}","Change (%)":f"{pt:+.2f}%",
                    "High":f"₹{safe_float(h['High'].max()):,.2f}",
                    "Low":f"₹{safe_float(h['Low'].min()):,.2f}","_pct":pt})
            else:
                idx_rows.append({"Index":idx["name"],"Value":"N/A",
                    "Change (pts)":"N/A","Change (%)":"N/A",
                    "High":"N/A","Low":"N/A","_pct":None})
    idx_df=pd.DataFrame(idx_rows)
    st.dataframe(idx_df.drop(columns=["_pct"]),use_container_width=True,hide_index=True)

    valid_idx=idx_df[idx_df["_pct"].notna()].copy()
    if not valid_idx.empty:
        try:
            fig_b=px.bar(valid_idx,x="Index",y="_pct",
                color="_pct",color_continuous_scale=["#ef4444","#f59e0b","#10b981"],
                color_continuous_midpoint=0,text="Change (%)",
                title="Today's % Change by Index",template=PLT,height=320,
                labels={"_pct":"% Change","Index":"Index"})
            fig_b.update_traces(textposition="outside",marker_line_width=0,
                                textfont=dict(color="#1e293b",size=11))
            fig_b.update_layout(**PLT_LAYOUT,coloraxis_showscale=False)
            style_fig(fig_b)
            st.plotly_chart(fig_b,use_container_width=True)
        except Exception as e: st.warning(f"⚠️ {e}")

    divider()
    sec("Trend Comparison")
    c_per,c_idx=st.columns([1,3])
    with c_per: p_sel=st.selectbox("Period",["1mo","3mo","6mo","1y"],index=1,key="idx_p")
    with c_idx: sel_idx=st.multiselect("Indices",[i["name"] for i in NSE_INDICES],
                                        default=["Nifty 50","Nifty Bank","Nifty IT"])
    sym_map={i["name"]:i for i in NSE_INDICES}
    if sel_idx:
        fig_m=go.Figure()
        for ni in sel_idx:
            meta=sym_map.get(ni)
            if not meta: continue
            h=fetch_ticker(meta["symbol"],p_sel)
            if h.empty: continue
            norm=(h["Close"]/h["Close"].iloc[0]*100)
            fig_m.add_trace(go.Scatter(x=h.index,y=norm,name=ni,
                mode="lines",line=dict(color=meta["color"],width=2)))
        fig_m.add_hline(y=100,line_dash="dot",line_color="#94a3b8")
        fig_m.update_layout(**PLT_LAYOUT,title="Normalised Performance (base=100)",
                            height=380,xaxis_title="Date",yaxis_title="Indexed Value")
        style_fig(fig_m)
        st.plotly_chart(fig_m,use_container_width=True)

elif page == "📈 Nifty 50 Index":
    hero("📈","Nifty 50 Index","<span class='ui-badge badge-live'>LIVE</span>","^NSEI — NSE Flagship Index")
    c1,c2=st.columns([1,3])
    with c1: n_period=st.selectbox("Period",["1mo","3mo","6mo","1y","2y","5y"],index=2,key="nf_p")
    with c2: chart_type=st.radio("Chart", ["Line","Candlestick","Area"],horizontal=True,key="nf_ct")
    with st.spinner("Fetching Nifty 50…"):
        nifty=fetch_ticker("^NSEI",n_period)
    if nifty.empty:
        st.error("❌ Could not fetch Nifty 50 data.")
    else:
        c=safe_float(nifty["Close"].iloc[-1])
        p=safe_float(nifty["Close"].iloc[-2]) if len(nifty)>1 else c
        ch=c-p; pt=ch/p*100 if p else 0
        m1,m2,m3,m4,m5=st.columns(5)
        m1.metric("Last",f"₹{c:,.2f}")
        m2.metric("Change",f"{ch:+.2f}",delta=f"{pt:+.2f}%")
        m3.metric("Period High",f"₹{safe_float(nifty['High'].max()):,.2f}")
        m4.metric("Period Low",f"₹{safe_float(nifty['Low'].min()):,.2f}")
        m5.metric("Avg Volume",f"{int(nifty['Volume'].mean()):,}")
        divider()
        fig=go.Figure()
        if chart_type=="Candlestick":
            fig.add_trace(go.Candlestick(x=nifty.index,open=nifty["Open"],high=nifty["High"],
                low=nifty["Low"],close=nifty["Close"],name="Nifty 50",
                increasing_line_color="#10b981",decreasing_line_color="#ef4444"))
        elif chart_type=="Area":
            fig.add_trace(go.Scatter(x=nifty.index,y=nifty["Close"],fill="tozeroy",
                name="Nifty 50",line=dict(color="#6366f1",width=2),
                fillcolor="rgba(99,102,241,0.12)"))
        else:
            fig.add_trace(go.Scatter(x=nifty.index,y=nifty["Close"],name="Nifty 50",
                line=dict(color="#6366f1",width=2.5)))
        fig.update_layout(**PLT_LAYOUT,title=f"Nifty 50 — {n_period}",height=460,
                          xaxis_title="Date",yaxis_title="Index Value")
        style_fig(fig)
        st.plotly_chart(fig,use_container_width=True)

elif page == "🏢 All 50 Companies":
    hero("🏢","All 50 Companies","<span class='ui-badge badge-nse'>NSE</span>","Live prices for all Nifty 50 stocks")
    sec("Sector Filter")
    sel_sec=st.selectbox("Sector",sectors,key="all_sec")
    with st.spinner("Fetching prices…"):
        raw=fetch_batch("5d")
    df_rows=build_stock_rows(raw)
    if sel_sec!="All":
        df_rows=df_rows[df_rows["Sector"]==sel_sec]
    disp=df_rows.drop(columns=["_curr","_pct"],errors="ignore")
    st.dataframe(disp,use_container_width=True,hide_index=True)
    if not df_rows.empty:
        valid=df_rows[df_rows["_pct"].notna()].copy()
        if not valid.empty:
            try:
                fig=px.bar(valid,x="Symbol",y="_pct",
                    color="_pct",color_continuous_scale=["#ef4444","#f59e0b","#10b981"],
                    color_continuous_midpoint=0,text="Change (%)",
                    title="1-Day % Change",template=PLT,height=380)
                fig.update_traces(textposition="outside",marker_line_width=0)
                fig.update_layout(**PLT_LAYOUT,coloraxis_showscale=False)
                style_fig(fig)
                st.plotly_chart(fig,use_container_width=True)
            except Exception as e: st.warning(f"⚠️ {e}")

elif page == "🏆 Gainers & Losers":
    hero("🏆","Gainers & Losers","<span class='ui-badge badge-live'>TODAY</span>")
    with st.spinner("Fetching…"):
        raw=fetch_batch("5d")
    df_rows=build_stock_rows(raw)
    valid=df_rows[df_rows["_pct"].notna()].copy()
    top_n=st.slider("Top N",3,10,5,key="gl_n")
    if valid.empty:
        st.warning("⚠️ No data available.")
    else:
        gainers=safe_sort(valid,"_pct",ascending=False).head(top_n)
        losers =safe_sort(valid,"_pct",ascending=True ).head(top_n)
        cg,cl=st.columns(2)
        with cg:
            sec("🟢 Top Gainers")
            st.dataframe(gainers[["Symbol","Company","Price (₹)","Change (%)"]],
                         use_container_width=True,hide_index=True)
        with cl:
            sec("🔴 Top Losers")
            st.dataframe(losers[["Symbol","Company","Price (₹)","Change (%)"]],
                         use_container_width=True,hide_index=True)
        try:
            combined=pd.concat([gainers,losers]).drop_duplicates(subset="Symbol")
            combined=combined[combined["_pct"].notna()]
            fig=px.bar(combined,x="Symbol",y="_pct",
                color="_pct",color_continuous_scale=["#ef4444","#f59e0b","#10b981"],
                color_continuous_midpoint=0,text="Change (%)",
                title="Gainers vs Losers",template=PLT,height=380)
            fig.update_traces(textposition="outside",marker_line_width=0)
            fig.update_layout(**PLT_LAYOUT,coloraxis_showscale=False)
            style_fig(fig)
            st.plotly_chart(fig,use_container_width=True)
        except Exception as e: st.warning(f"⚠️ {e}")

elif page == "🧮 P&L Calculator":
    hero("🧮","P&L Calculator","<span class='ui-badge badge-sim'>SIMULATOR</span>","Calculate profit / loss")
    with st.spinner("Fetching live prices…"):
        raw=fetch_batch("5d")
    c1,c2,c3=st.columns(3)
    stock_names=[s["name"] for s in NIFTY50]
    with c1: sel_name=st.selectbox("Stock",stock_names,key="pl_s")
    sel_s=next(s for s in NIFTY50 if s["name"]==sel_name)
    curr,_=get_curr_prev(raw,sel_s["symbol"])
    lp=curr if curr else 0.0
    with c2: buy_p=st.number_input("Buy Price (₹)",min_value=0.01,value=round(lp,2) if lp>0 else 100.0,step=0.5,key="pl_bp")
    with c3: qty  =st.number_input("Quantity",    min_value=1,   value=10,           step=1,   key="pl_q")
    sell_p=st.number_input("Sell / Current Price (₹)",min_value=0.01,value=round(lp,2) if lp>0 else 100.0,step=0.5,key="pl_sp")
    pl=(sell_p-buy_p)*qty
    inv=buy_p*qty; ret=(pl/inv*100) if inv>0 else 0
    divider()
    mc1,mc2,mc3=st.columns(3)
    mc1.metric("Investment",f"₹{inv:,.2f}")
    mc2.metric("Current Value",f"₹{sell_p*qty:,.2f}")
    mc3.metric("Return",f"{ret:+.2f}%")
    show_pl(pl)

elif page == "🔍 Stock Chart":
    hero("🔍","Stock Chart","<span class='ui-badge badge-live'>LIVE</span>","Deep-dive into any Nifty 50 stock")
    stock_names=[s["name"] for s in NIFTY50]
    c1,c2,c3=st.columns([2,1,1])
    with c1: sel_name=st.selectbox("Company",stock_names,key="sc_n")
    with c2: sc_period=st.selectbox("Period",["1mo","3mo","6mo","1y","2y"],index=2,key="sc_p")
    with c3: sc_ct=st.radio("Chart",["Area","Candlestick","Line"],key="sc_ct",horizontal=True)
    sel_s=next(s for s in NIFTY50 if s["name"]==sel_name)
    with st.spinner(f"Loading {sel_name}…"):
        h=fetch_ticker(sel_s["symbol"],sc_period)
    if h.empty:
        st.warning("⚠️ No data.")
    else:
        c=safe_float(h["Close"].iloc[-1])
        p=safe_float(h["Close"].iloc[-2]) if len(h)>1 else c
        ch=c-p; pt=ch/p*100 if p else 0
        m1,m2,m3,m4=st.columns(4)
        m1.metric("Price",f"₹{c:,.2f}",delta=f"{pt:+.2f}%")
        m2.metric("High",f"₹{safe_float(h['High'].max()):,.2f}")
        m3.metric("Low",f"₹{safe_float(h['Low'].min()):,.2f}")
        m4.metric("Beta",str(sel_s['beta']))
        fig=go.Figure()
        if sc_ct=="Candlestick":
            fig.add_trace(go.Candlestick(x=h.index,open=h["Open"],high=h["High"],
                low=h["Low"],close=h["Close"],name=sel_name,
                increasing_line_color="#10b981",decreasing_line_color="#ef4444"))
        elif sc_ct=="Area":
            fig.add_trace(go.Scatter(x=h.index,y=h["Close"],fill="tozeroy",name=sel_name,
                line=dict(color="#6366f1",width=2),fillcolor="rgba(99,102,241,0.12)"))
        else:
            fig.add_trace(go.Scatter(x=h.index,y=h["Close"],name=sel_name,
                line=dict(color="#6366f1",width=2.5)))
        ma20=h["Close"].rolling(20).mean()
        ma50=h["Close"].rolling(50).mean()
        fig.add_trace(go.Scatter(x=h.index,y=ma20,name="MA20",
            line=dict(color="#f59e0b",width=1.5,dash="dot")))
        fig.add_trace(go.Scatter(x=h.index,y=ma50,name="MA50",
            line=dict(color="#06b6d4",width=1.5,dash="dash")))
        fig.update_layout(**PLT_LAYOUT,title=f"{sel_name} — {sc_period}",
                          height=460,xaxis_title="Date",yaxis_title="Price (₹)")
        style_fig(fig)
        st.plotly_chart(fig,use_container_width=True)

elif page == "⏰ Time Machine":
    hero("⏰","Time Machine","<span class='ui-badge badge-hist'>HISTORICAL</span>",
         "Go back to any date and see what the market looked like")
    with st.spinner("Loading 5-year history (first load may take ~30s)…"):
        all_hist=fetch_all_history()
    tab_snap,tab_port,tab_compare=st.tabs(["📸 Market Snapshot","💼 Paper Portfolio","📊 Compare Stocks"])
    with tab_snap:
        sec("Pick a Date")
        preset=st.selectbox("Famous Dates",[""] + list(FAMOUS_DATES.keys()),key="tm_preset")
        if preset:
            snap_date=FAMOUS_DATES[preset]
        else:
            snap_date=st.date_input("Custom Date",value=date(2023,1,2),
                min_value=date(2018,1,1),max_value=date.today(),key="tm_date")
        if st.button("📸 Show Snapshot",key="tm_snap_btn"):
            with st.spinner("Building snapshot…"):
                snap=tm_get_snapshot(all_hist,snap_date)
            if snap.empty:
                st.warning(f"⚠️ No data for {snap_date}. Try an adjacent trading day.")
            else:
                st.success(f"✅ Snapshot for {snap_date}")
                st.dataframe(snap,use_container_width=True)
    with tab_port:
        sec("Virtual Portfolio")
        pc1,pc2,pc3=st.columns(3)
        with pc1: inv_date=st.date_input("Invest Date",date(2020,4,1),
                    min_value=date(2018,1,1),max_value=date.today()-timedelta(days=5),key="tm_inv")
        with pc2: end_date=st.date_input("Exit Date",date(2021,4,1),
                    min_value=date(2018,1,2),max_value=date.today(),key="tm_end")
        with pc3: invest=st.number_input("Investment (₹)",10000,10000000,100000,step=10000,key="tm_inv_amt")
        sel_stocks=st.multiselect("Stocks",[s["name"] for s in NIFTY50],
                                   default=[s["name"] for s in NIFTY50[:5]],key="tm_stocks")
        syms_sel=[next(s["symbol"] for s in NIFTY50 if s["name"]==n) for n in sel_stocks]
        if st.button("🚀 Run Portfolio",key="tm_port_btn"):
            if inv_date>=end_date:
                st.error("Invest date must be before exit date.")
            elif not sel_stocks:
                st.warning("Select at least one stock.")
            else:
                with st.spinner("Simulating…"):
                    res=tm_paper_portfolio(all_hist,inv_date,end_date,invest,syms_sel)
                if res is None:
                    st.warning("⚠️ Could not simulate. Try different dates/stocks.")
                else:
                    st.success(f"✅ Duration: {res['dur']} | Invested: ₹{res['invested']:,.0f}")
                    pa,pb,pc_m,pd_m=st.columns(4)
                    pa.metric("Final Value",f"₹{res['final']:,.0f}")
                    pb.metric("Abs P&L",f"₹{res['abs_pl']:+,.0f}")
                    pc_m.metric("Return",f"{res['ret_pct']:+.2f}%")
                    pd_m.metric("CAGR",f"{res['cagr']:+.2f}%")
                    st.dataframe(res["pf_df"].drop(columns=["_pl"],errors="ignore"),
                                 use_container_width=True)
                    if len(res["growth"])>1:
                        fig_g=go.Figure()
                        fig_g.add_trace(go.Scatter(x=res["growth"].index,y=res["growth"].values,
                            fill="tozeroy",mode="lines",name="Portfolio Value",
                            line=dict(color="#6366f1",width=2),
                            fillcolor="rgba(99,102,241,0.1)"))
                        fig_g.add_hline(y=invest,line_dash="dash",line_color="#f59e0b",
                                        annotation_text=f"Invested ₹{invest:,.0f}")
                        fig_g.update_layout(**PLT_LAYOUT,title="Portfolio Growth",height=360)
                        style_fig(fig_g)
                        st.plotly_chart(fig_g,use_container_width=True)
    with tab_compare:
        sec("Compare Two Stocks Over Time")
        cc1,cc2,cc3=st.columns(3)
        with cc1: s1=st.selectbox("Stock A",[s["name"] for s in NIFTY50],index=0,key="tm_s1")
        with cc2: s2=st.selectbox("Stock B",[s["name"] for s in NIFTY50],index=1,key="tm_s2")
        with cc3: cmp_p=st.selectbox("Period",["6mo","1y","2y","5y"],index=2,key="tm_cp")
        sym1=next(s["symbol"] for s in NIFTY50 if s["name"]==s1)
        sym2=next(s["symbol"] for s in NIFTY50 if s["name"]==s2)
        h1=fetch_ticker(sym1,cmp_p); h2=fetch_ticker(sym2,cmp_p)
        if h1.empty or h2.empty:
            st.warning("⚠️ Could not fetch data for comparison.")
        else:
            n1=h1["Close"]/h1["Close"].iloc[0]*100
            n2=h2["Close"]/h2["Close"].iloc[0]*100
            fig_c=go.Figure()
            fig_c.add_trace(go.Scatter(x=h1.index,y=n1,name=s1,line=dict(color="#6366f1",width=2)))
            fig_c.add_trace(go.Scatter(x=h2.index,y=n2,name=s2,line=dict(color="#10b981",width=2)))
            fig_c.add_hline(y=100,line_dash="dot",line_color="#94a3b8")
            fig_c.update_layout(**PLT_LAYOUT,title="Normalised Performance (base=100)",
                                height=420,xaxis_title="Date",yaxis_title="Indexed Value")
            style_fig(fig_c)
            st.plotly_chart(fig_c,use_container_width=True)

elif page == "🧪 Scenario Engine":
    hero("🧪","Scenario Engine","<span class='ui-badge badge-sim'>SIMULATION</span>",
         "How did stocks perform during macro events?")
    with st.spinner("Loading history…"):
        all_hist=fetch_all_history()
    c1,c2=st.columns([2,1])
    with c1: event=st.selectbox("Macro Event",list(MACRO_EVENTS.keys()),key="sc_ev")
    with c2: as_of=st.date_input("As of Date",date.today(),
                min_value=date(2018,1,1),max_value=date.today(),key="sc_as")
    if st.button("⚡ Run Scenario",key="sc_btn"):
        with st.spinner("Analysing…"):
            sc_df=tm_scenario(all_hist,event,as_of)
        if sc_df.empty:
            st.warning("⚠️ Not enough historical events matching this scenario.")
        else:
            st.success(f"✅ Found {len(sc_df)} stocks with data for '{event}'")
            st.dataframe(sc_df,use_container_width=True)
            top5=sc_df.head(5); bot5=sc_df.tail(5)
            try:
                combined=pd.concat([top5,bot5]).drop_duplicates()
                fig=px.bar(combined.reset_index(),x="Symbol",y="Avg Return",
                    color="Avg Return",color_continuous_scale=["#ef4444","#f59e0b","#10b981"],
                    color_continuous_midpoint=0,text="Avg Return",
                    title=f"Top & Bottom 5 — '{event}'",template=PLT,height=380)
                fig.update_traces(textposition="outside",marker_line_width=0,
                                  texttemplate="%{text:.1f}%")
                fig.update_layout(**PLT_LAYOUT,coloraxis_showscale=False)
                style_fig(fig)
                st.plotly_chart(fig,use_container_width=True)
            except Exception as e: st.warning(f"⚠️ {e}")

elif page == "💼 Paper Portfolio":
    hero("💼","Paper Portfolio","<span class='ui-badge badge-sim'>VIRTUAL</span>",
         "Build a hypothetical portfolio")
    with st.spinner("Fetching prices…"):
        raw=fetch_batch("5d")
    df_rows=build_stock_rows(raw)
    price_map={r["Symbol"]:r["_curr"] for _,r in df_rows.iterrows() if r["_curr"] is not None}
    if "pp_holdings" not in st.session_state:
        st.session_state["pp_holdings"]={}
    holdings=st.session_state["pp_holdings"]
    sec("Add Position")
    stock_names=[s["name"] for s in NIFTY50]
    ac1,ac2,ac3,ac4=st.columns(4)
    with ac1: pp_name=st.selectbox("Stock",stock_names,key="pp_s")
    pp_sym=next(s["symbol"] for s in NIFTY50 if s["name"]==pp_name)
    pp_short=pp_sym.replace(".NS","")
    lp=price_map.get(pp_short,100.0) or 100.0
    with ac2: pp_qty =st.number_input("Qty",min_value=1,value=10,step=1,key="pp_q")
    with ac3: pp_buy =st.number_input("Buy Price (₹)",min_value=0.01,value=round(lp,2),step=0.5,key="pp_bp")
    with ac4:
        st.markdown("<br>",unsafe_allow_html=True)
        if st.button("➕ Add",key="pp_add",use_container_width=True):
            if pp_short in holdings:
                old=holdings[pp_short]
                tq=old["qty"]+pp_qty
                avg=(old["buy"]*old["qty"]+pp_buy*pp_qty)/tq
                holdings[pp_short]={"name":pp_name,"qty":tq,"buy":round(avg,2)}
            else:
                holdings[pp_short]={"name":pp_name,"qty":pp_qty,"buy":round(pp_buy,2)}
            st.success(f"✅ Added {pp_qty} × {pp_name}")
            st.rerun()
    divider()
    if not holdings:
        st.info("💡 Add stocks above to build your portfolio.")
    else:
        rows=[]
        total_inv=total_cur=0.0
        for sym,h in holdings.items():
            cp=price_map.get(sym) or h["buy"]
            val=cp*h["qty"]; inv_v=h["buy"]*h["qty"]
            pl=val-inv_v; ret=(pl/inv_v*100) if inv_v else 0
            rows.append({"Symbol":sym,"Company":h["name"],"Qty":h["qty"],
                         "Buy (₹)":h["buy"],"Live (₹)":round(cp,2),
                         "Value (₹)":round(val,2),"P&L (₹)":round(pl,2),
                         "Return %":round(ret,2)})
            total_inv+=inv_v; total_cur+=val
        pf_df=pd.DataFrame(rows)
        total_pl=total_cur-total_inv
        total_ret=(total_pl/total_inv*100) if total_inv>0 else 0
        pm1,pm2,pm3,pm4=st.columns(4)
        pm1.metric("Invested",f"₹{total_inv:,.0f}")
        pm2.metric("Current Value",f"₹{total_cur:,.0f}")
        pm3.metric("Total P&L",f"₹{total_pl:+,.0f}")
        pm4.metric("Return",f"{total_ret:+.2f}%")
        st.dataframe(pf_df,use_container_width=True,hide_index=True)
        if st.button("🗑️ Clear Portfolio",key="pp_clear"):
            st.session_state["pp_holdings"]={}
            st.rerun()
        if len(rows)>0:
            try:
                fig_pie=px.pie(pf_df,values="Value (₹)",names="Symbol",
                    title="Portfolio Allocation",template=PLT,height=350)
                fig_pie.update_layout(**PLT_LAYOUT)
                st.plotly_chart(fig_pie,use_container_width=True)
            except Exception as e: st.warning(f"⚠️ {e}")

# ── NEWS SENTIMENT ──────────────────────────────────────────────────────
elif page == "📰 News Sentiment":
    try:
        from textblob import TextBlob
        TEXTBLOB_OK = True
    except ImportError:
        TEXTBLOB_OK = False

    hero("📰", "News Sentiment",
         "<span class='ui-badge badge-live'>LIVE</span>",
         "Analyse market mood from recent headlines")

    if not TEXTBLOB_OK:
        st.error("❌ `textblob` not installed. Add it to requirements.txt and redeploy.")
        st.stop()

    NS_NAMES = [s["name"] for s in NIFTY50]
    NS_N2S   = {s["name"]: s["symbol"] for s in NIFTY50}

    c1, c2 = st.columns([3, 1])
    with c1: ns_stock  = st.selectbox("🏛️ Select Company", NS_NAMES, key="ns_stock")
    with c2: ns_period = st.selectbox("📅 Period", ["1mo","3mo","6mo"], key="ns_period")

    @st.cache_data(ttl=600)
    def _ns_fetch(sym, period):
        try:
            t = yf.Ticker(sym)
            h = t.history(period=period, auto_adjust=True)
            try:
                n = t.news or []
            except Exception:
                n = []
            return h, n
        except Exception:
            return pd.DataFrame(), []

    with st.spinner("🔍 Fetching data…"):
        ns_hist, ns_news = _ns_fetch(NS_N2S[ns_stock], ns_period)

    if not ns_hist.empty:
        try:
            cp = safe_float(ns_hist["Close"].iloc[-1])
            pp2 = safe_float(ns_hist["Close"].iloc[-2]) if len(ns_hist) > 1 else cp
            ch = cp - pp2; pt = (ch / pp2 * 100) if pp2 else 0
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Price",        f"₹{cp:,.2f}")
            m2.metric("Change",       f"{ch:+.2f}")
            m3.metric("% Change",     f"{pt:+.2f}%")
            m4.metric("Period High",  f"₹{safe_float(ns_hist['High'].max()):,.2f}")
            divider()
            df_plot = ns_hist.reset_index()
            date_col = "Date" if "Date" in df_plot.columns else df_plot.columns[0]
            fig_ns = px.area(df_plot, x=date_col, y="Close",
                title=f"{ns_stock} — Price History", template=PLT, height=300,
                color_discrete_sequence=["#6366f1"])
            fig_ns.update_traces(line_color="#6366f1", fillcolor="rgba(99,102,241,0.1)")
            fig_ns.update_layout(**PLT_LAYOUT)
            style_fig(fig_ns)
            st.plotly_chart(fig_ns, use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ Chart error: {e}")

    divider()
    sec("🧠 Headline Sentiment Analysis")
    if not ns_news:
        st.info("💬 No recent news found for this stock via Yahoo Finance API.")
    else:
        rows_ns = []
        for item in ns_news[:20]:
            try:
                title = (
                    item.get("title")
                    or (item.get("content", {}) or {}).get("title", "")
                    if isinstance(item, dict) else ""
                )
                if not title: continue
                blob  = TextBlob(str(title))
                pol   = blob.sentiment.polarity
                sub   = blob.sentiment.subjectivity
                label = "🟢 Positive" if pol > 0.1 else ("🔴 Negative" if pol < -0.1 else "⚪ Neutral")
                rows_ns.append({"Headline": title, "Sentiment": label,
                                 "Polarity": round(pol, 3), "Subjectivity": round(sub, 3)})
            except Exception:
                continue
        if rows_ns:
            df_ns = pd.DataFrame(rows_ns)
            pos_n = len(df_ns[df_ns["Sentiment"] == "🟢 Positive"])
            neg_n = len(df_ns[df_ns["Sentiment"] == "🔴 Negative"])
            neu_n = len(df_ns[df_ns["Sentiment"] == "⚪ Neutral"])
            ma, mb, mc2 = st.columns(3)
            ma.metric("🟢 Positive", pos_n)
            mb.metric("🔴 Negative", neg_n)
            mc2.metric("⚪ Neutral",  neu_n)
            if pos_n + neg_n + neu_n > 0:
                try:
                    fig_pie_ns = px.pie(
                        values=[pos_n, neg_n, neu_n],
                        names=["🟢 Positive", "🔴 Negative", "⚪ Neutral"],
                        color_discrete_sequence=["#10b981", "#ef4444", "#9ca3af"],
                        title="Sentiment Distribution", template=PLT, height=300)
                    fig_pie_ns.update_layout(**PLT_LAYOUT)
                    st.plotly_chart(fig_pie_ns, use_container_width=True)
                except Exception as e:
                    st.warning(f"⚠️ {e}")
            st.dataframe(df_ns, use_container_width=True, hide_index=True)
        else:
            st.info("💬 No headlines with text found.")

# ── ML PREDICTIONS ──────────────────────────────────────────────────────
elif page == "🤖 ML Predictions":
    try:
        from sklearn.linear_model import LinearRegression
        from sklearn.preprocessing import PolynomialFeatures
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.metrics import mean_absolute_error, r2_score
        SK_OK = True
    except ImportError:
        SK_OK = False

    hero("🤖", "ML Predictions",
         "<span class='ui-badge badge-sim'>⚠️ Educational</span>",
         "Linear, Polynomial & Random Forest forecasting")

    if not SK_OK:
        st.error("❌ `scikit-learn` not installed. Add it to requirements.txt and redeploy.")
        st.stop()

    ML_NAMES = [s["name"] for s in NIFTY50]
    ML_N2S   = {s["name"]: s["symbol"] for s in NIFTY50}

    mc1, mc2, mc3 = st.columns(3)
    with mc1: ml_stock   = st.selectbox("🏛️ Company",       ML_NAMES,          key="ml_stock")
    with mc2: ml_period  = st.selectbox("📅 History",       ["6mo","1y","2y"], key="ml_period")
    with mc3: ml_horizon = st.slider(  "📆 Forecast days", 5, 30, 10,          key="ml_horizon")

    @st.cache_data(ttl=300)
    def _ml_load(sym, period):
        try:
            h = yf.Ticker(sym).history(period=period, auto_adjust=True)
            if h is not None and not h.empty:
                h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
                return h
        except Exception:
            pass
        return pd.DataFrame()

    with st.spinner("🔮 Fetching & training…"):
        ml_hist = _ml_load(ML_N2S[ml_stock], ml_period)

    if ml_hist.empty or len(ml_hist) < 30:
        st.warning("⚠️ Not enough data. Try a longer period.")
    else:
        try:
            # ── Safely extract Close as a flat 1-D numpy array ──────────
            _close_col = ml_hist["Close"]
            # yfinance may return a DataFrame with ticker as column level
            if isinstance(_close_col, pd.DataFrame):
                _close_col = _close_col.iloc[:, 0]
            close = _close_col.dropna().astype(float).values.flatten()

            if len(close) < 30:
                st.warning("⚠️ Not enough clean price data. Try a longer period.")
                st.stop()

            X  = np.arange(len(close)).reshape(-1, 1)
            y  = close

            lr   = LinearRegression().fit(X, y)
            poly = PolynomialFeatures(degree=2)
            Xp   = poly.fit_transform(X)
            plr  = LinearRegression().fit(Xp, y)
            rf   = RandomForestRegressor(n_estimators=100, random_state=42).fit(X, y)

            future_X  = np.arange(len(close), len(close) + ml_horizon).reshape(-1, 1)
            future_Xp = poly.transform(future_X)

            lr_pred   = lr.predict(future_X)
            poly_pred = np.clip(plr.predict(future_Xp), close[-1] * 0.5, close[-1] * 1.5)
            rf_pred   = rf.predict(future_X)

            # ── Generate weekday-only forecast dates ────────────────────
            last_date = pd.Timestamp(ml_hist.index[-1])
            fut_dates = []
            _d = last_date
            while len(fut_dates) < ml_horizon:
                _d += pd.Timedelta(days=1)
                if _d.weekday() < 5:   # Mon–Fri only
                    fut_dates.append(_d)

            lr_mae = mean_absolute_error(y, lr.predict(X))
            rf_mae = mean_absolute_error(y, rf.predict(X))
            lr_r2  = r2_score(y, lr.predict(X))
            rf_r2  = r2_score(y, rf.predict(X))

            sec("📊 Model Performance")
            mm1, mm2, mm3, mm4 = st.columns(4)
            mm1.metric("Linear MAE",       f"₹{lr_mae:.2f}")
            mm2.metric("Random Forest MAE", f"₹{rf_mae:.2f}")
            mm3.metric("Linear R²",        f"{lr_r2:.3f}")
            mm4.metric("Random Forest R²",  f"{rf_r2:.3f}")

            divider()
            fig_ml = go.Figure()
            fig_ml.add_trace(go.Scatter(
                x=ml_hist.index, y=close, mode="lines",
                name="Actual", line=dict(color="#1a1a2e", width=2)))
            fig_ml.add_trace(go.Scatter(
                x=fut_dates, y=lr_pred, mode="lines+markers",
                name="Linear", line=dict(color="#6366f1", width=2, dash="dot"),
                marker=dict(size=5)))
            fig_ml.add_trace(go.Scatter(
                x=fut_dates, y=poly_pred, mode="lines+markers",
                name="Polynomial", line=dict(color="#f59e0b", width=2, dash="dash"),
                marker=dict(size=5)))
            fig_ml.add_trace(go.Scatter(
                x=fut_dates, y=rf_pred, mode="lines+markers",
                name="Random Forest", line=dict(color="#10b981", width=2),
                marker=dict(size=5)))

            # ── Safe vrect: only add if we have at least 2 forecast dates ──
            if len(fut_dates) >= 2:
                try:
                    fig_ml.add_vrect(
                        x0=str(fut_dates[0].date()),
                        x1=str(fut_dates[-1].date()),
                        fillcolor="rgba(99,102,241,0.06)", line_width=0,
                        annotation_text="Forecast Zone",
                        annotation_position="top left")
                except Exception:
                    pass

            fig_ml.update_layout(
                **PLT_LAYOUT,
                title=f"{ml_stock} — {ml_horizon}-Day Forecast",
                height=460,
                xaxis_title="Date",
                yaxis_title="Price (₹)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02))
            style_fig(fig_ml)
            st.plotly_chart(fig_ml, use_container_width=True)

            divider()
            sec("📅 Forecast Table")
            fore_df = pd.DataFrame({
                "Date":              [d.strftime("%d %b %Y") for d in fut_dates],
                "Linear (₹)":        [f"₹{v:,.2f}" for v in lr_pred],
                "Polynomial (₹)":    [f"₹{v:,.2f}" for v in poly_pred],
                "Random Forest (₹)": [f"₹{v:,.2f}" for v in rf_pred],
            })
            st.dataframe(fore_df, use_container_width=True, hide_index=True)
            st.caption("⚠️ Statistical projections for educational purposes only — not investment advice.")
        except Exception as e:
            st.error(f"❌ Model error: {e}")

# ── PAPER TRADING ──────────────────────────────────────────────────────
elif page == "🎮 Paper Trading":
    IST_TZ = pytz.timezone("Asia/Kolkata")
    STARTING_CAPITAL = 1_000_000.0

    def _pt_safe_float(v, d=0.0):
        try:
            f = float(v)
            return d if (np.isnan(f) or np.isinf(f)) else f
        except Exception:
            return d

    @st.cache_data(ttl=60)
    def _pt_price(sym: str):
        try:
            h = yf.Ticker(sym).history(period="1d", interval="1m")
            if h is not None and not h.empty:
                p = _pt_safe_float(h["Close"].iloc[-1])
                if p > 0: return p
        except Exception:
            pass
        try:
            h = yf.Ticker(sym).history(period="5d")
            if h is not None and not h.empty:
                p = _pt_safe_float(h["Close"].iloc[-1])
                if p > 0: return p
        except Exception:
            pass
        return None

    for k, v in [("pt_balance", STARTING_CAPITAL), ("pt_holdings", {}),
                 ("pt_trades", []), ("pt_equity", [])]:
        if k not in st.session_state:
            st.session_state[k] = v

    def _pt_snapshot():
        try:
            pv = sum(
                _pt_safe_float(_pt_price(s) or hd["avg_price"]) * _pt_safe_float(hd["qty"])
                for s, hd in st.session_state.pt_holdings.items()
            )
            st.session_state.pt_equity.append({
                "time":   datetime.now(IST_TZ).strftime("%H:%M:%S"),
                "equity": round(st.session_state.pt_balance + pv, 2),
            })
        except Exception:
            pass

    PT_NAMES = [s["name"] for s in NIFTY50]
    PT_N2S   = {s["name"]: s["symbol"] for s in NIFTY50}

    hero("🎮", "Paper Trading",
         f"<span class='ui-badge {'badge-live' if not is_guest() else 'badge-hist'}'>{'✅ ' + name if not is_guest() else '👤 Guest'}</span>",
         "Virtual ₹10,00,000 — zero risk, real prices")

    if is_guest():
        login_nudge("save your paper trading progress")

    try:
        port_val_pt = sum(
            _pt_safe_float(_pt_price(s) or hd["avg_price"]) * _pt_safe_float(hd["qty"])
            for s, hd in st.session_state.pt_holdings.items()
        )
    except Exception:
        port_val_pt = 0.0

    total_eq_pt = st.session_state.pt_balance + port_val_pt
    pnl_pt      = total_eq_pt - STARTING_CAPITAL
    pnl_pct_pt  = pnl_pt / STARTING_CAPITAL * 100

    sec("💰 Account Summary")
    pa, pb, pc3, pd3, pe3 = st.columns(5)
    pa.metric("Cash",          f"₹{st.session_state.pt_balance:,.0f}")
    pb.metric("Portfolio",     f"₹{port_val_pt:,.0f}")
    pc3.metric("Total Equity", f"₹{total_eq_pt:,.0f}")
    pd3.metric("Net P&L",      f"₹{pnl_pt:+,.0f}", delta=f"{pnl_pct_pt:+.2f}%")
    pe3.metric("Trades",       str(len(st.session_state.pt_trades)))

    col_r, col_pdf = st.columns([3, 1])
    with col_r:
        if st.button("🔄 Reset Account", key="pt_reset"):
            for k, v in [("pt_balance", STARTING_CAPITAL), ("pt_holdings", {}),
                         ("pt_trades", []), ("pt_equity", [])]:
                st.session_state[k] = v
            st.success("✅ Account reset to ₹10,00,000")
            st.rerun()
    with col_pdf:
        if st.button("📄 PDF Report", type="primary", use_container_width=True, key="pt_pdf"):
            try:
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 16)
                pdf.cell(0, 10, "Nifty50 Tracker - Paper Trading Report", ln=True, align="C")
                pdf.set_font("Helvetica", "", 10)
                pdf.cell(0, 8, f"Generated: {datetime.now(IST_TZ).strftime('%Y-%m-%d %H:%M IST')}", ln=True, align="C")
                pdf.cell(0, 8, f"User: {name}", ln=True, align="C")
                pdf.ln(4)
                pdf.set_font("Helvetica", "B", 13)
                pdf.cell(0, 10, "Account Summary", ln=True)
                pdf.set_font("Helvetica", "", 11)
                for lbl, val in [
                    ("Starting Capital", f"Rs.{STARTING_CAPITAL:,.2f}"),
                    ("Cash Balance",     f"Rs.{st.session_state.pt_balance:,.2f}"),
                    ("Portfolio Value",  f"Rs.{port_val_pt:,.2f}"),
                    ("Total Equity",     f"Rs.{total_eq_pt:,.2f}"),
                    ("Net P&L",          f"Rs.{pnl_pt:+,.2f}"),
                    ("Total Trades",     str(len(st.session_state.pt_trades))),
                ]:
                    pdf.cell(60, 8, lbl + ":", border=0)
                    pdf.cell(0, 8, val, ln=True)
                pdf_bytes = bytes(pdf.output())
                st.download_button("⬇️ Download PDF", data=pdf_bytes,
                    file_name=f"paper_trading_{datetime.now(IST_TZ).strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf", key="pt_dl")
            except Exception as e:
                st.warning(f"⚠️ PDF error: {e}")

    divider()
    tab_buy, tab_sell, tab_port, tab_log, tab_chart = st.tabs([
        "🟢  Buy", "🔴  Sell", "💼  Portfolio", "📜  Trade Log", "📈  Equity Chart"
    ])

    with tab_buy:
        sec("🟢 Place a Buy Order")
        bc1, bc2, bc3 = st.columns(3)
        with bc1: buy_stock = st.selectbox("Stock", PT_NAMES, key="pt_buy_stock")
        with bc2: buy_qty   = st.number_input("Qty", min_value=1, value=1, step=1, key="pt_buy_qty")
        with bc3:
            buy_sym   = PT_N2S[buy_stock]
            buy_price = _pt_price(buy_sym)
            if buy_price and buy_price > 0:
                st.metric("Live Price", f"₹{buy_price:,.2f}")
            else:
                st.warning("⏳ Price unavailable")
                buy_price = 0.0
        buy_cost = _pt_safe_float(buy_price) * int(buy_qty)
        st.markdown(f"💰 **Order Value:** ₹{buy_cost:,.2f} &nbsp;|&nbsp; 💵 **Cash:** ₹{st.session_state.pt_balance:,.2f}",
                    unsafe_allow_html=True)
        if st.button("🟢 Execute Buy", type="primary", key="pt_exec_buy"):
            if buy_price <= 0:
                st.error("❌ Cannot fetch live price. Try again.")
            elif buy_cost > st.session_state.pt_balance:
                st.error(f"❌ Insufficient balance. Need ₹{buy_cost:,.2f}")
            else:
                hh = st.session_state.pt_holdings
                if buy_sym in hh:
                    old = hh[buy_sym]
                    tq  = old["qty"] + buy_qty
                    avg = (old["avg_price"] * old["qty"] + buy_price * buy_qty) / tq
                    hh[buy_sym] = {"qty": tq, "avg_price": round(avg, 4), "name": buy_stock}
                else:
                    hh[buy_sym] = {"qty": buy_qty, "avg_price": round(buy_price, 4), "name": buy_stock}
                st.session_state.pt_balance -= buy_cost
                st.session_state.pt_trades.append({
                    "time": datetime.now(IST_TZ).strftime("%H:%M:%S"),
                    "stock": buy_stock, "type": "BUY",
                    "qty": buy_qty, "price": round(buy_price, 2), "value": round(buy_cost, 2),
                })
                _pt_snapshot()
                st.success(f"✅ Bought {buy_qty} × {buy_stock} @ ₹{buy_price:,.2f}")
                st.rerun()

    with tab_sell:
        sec("🔴 Place a Sell Order")
        pt_holdings = st.session_state.pt_holdings
        if not pt_holdings:
            st.info("💡 No holdings yet. Buy some stocks first.")
        else:
            held_names = [pt_holdings[s]["name"] for s in pt_holdings]
            held_syms  = list(pt_holdings.keys())
            sc1, sc2, sc3 = st.columns(3)
            with sc1: sell_name = st.selectbox("Stock", held_names, key="pt_sell_stock")
            sell_sym  = held_syms[held_names.index(sell_name)]
            held_qty  = pt_holdings[sell_sym]["qty"]
            with sc2: sell_qty = st.number_input("Qty", min_value=1, max_value=held_qty, value=1, key="pt_sell_qty")
            with sc3:
                sell_price = _pt_price(sell_sym)
                if sell_price and sell_price > 0:
                    st.metric("Live Price", f"₹{sell_price:,.2f}")
                else:
                    st.warning("⏳ Price unavailable")
                    sell_price = 0.0
            sell_value = _pt_safe_float(sell_price) * int(sell_qty)
            avg_pr     = pt_holdings[sell_sym]["avg_price"]
            est_pnl    = (_pt_safe_float(sell_price) - avg_pr) * sell_qty
            st.markdown(f"💰 **Value:** ₹{sell_value:,.2f} &nbsp;|&nbsp; 📊 **Avg:** ₹{avg_pr:,.2f} &nbsp;|&nbsp; 📈 **P&L:** ₹{est_pnl:+,.2f}",
                        unsafe_allow_html=True)
            if st.button("🔴 Execute Sell", type="primary", key="pt_exec_sell"):
                if sell_price <= 0:
                    st.error("❌ Cannot fetch live price.")
                else:
                    hh = st.session_state.pt_holdings
                    if sell_qty >= held_qty: del hh[sell_sym]
                    else: hh[sell_sym]["qty"] -= sell_qty
                    st.session_state.pt_balance += sell_value
                    st.session_state.pt_trades.append({
                        "time": datetime.now(IST_TZ).strftime("%H:%M:%S"),
                        "stock": sell_name, "type": "SELL",
                        "qty": sell_qty, "price": round(sell_price, 2), "value": round(sell_value, 2),
                    })
                    _pt_snapshot()
                    st.success(f"✅ Sold {sell_qty} × {sell_name} @ ₹{sell_price:,.2f} | P&L: ₹{est_pnl:+,.2f}")
                    st.rerun()

    with tab_port:
        sec("💼 Current Holdings")
        if not st.session_state.pt_holdings:
            st.info("💡 No open positions.")
        else:
            rows_pt = []
            for sym, hd in st.session_state.pt_holdings.items():
                try:
                    lp2  = _pt_safe_float(_pt_price(sym) or hd["avg_price"])
                    val2 = lp2 * hd["qty"]
                    pl2  = (lp2 - hd["avg_price"]) * hd["qty"]
                    pct2 = ((lp2 - hd["avg_price"]) / hd["avg_price"] * 100) if hd["avg_price"] else 0
                    rows_pt.append({
                        "Stock":         hd["name"],
                        "Qty":           hd["qty"],
                        "Avg Buy (₹)":   f"₹{hd['avg_price']:,.2f}",
                        "Live (₹)":      f"₹{lp2:,.2f}",
                        "Value (₹)":     f"₹{val2:,.2f}",
                        "P&L (₹)":       f"₹{pl2:+,.2f}",
                        "P&L %":         f"{pct2:+.2f}%",
                    })
                except Exception:
                    continue
            if rows_pt:
                st.dataframe(pd.DataFrame(rows_pt), use_container_width=True, hide_index=True)

    with tab_log:
        sec("📜 Trade History")
        if not st.session_state.pt_trades:
            st.info("💡 No trades yet.")
        else:
            st.dataframe(pd.DataFrame(st.session_state.pt_trades[::-1]),
                         use_container_width=True, hide_index=True)

    with tab_chart:
        sec("📈 Equity Curve")
        eq = st.session_state.pt_equity
        if len(eq) < 2:
            st.info("💡 Execute at least 2 trades to see the equity curve.")
        else:
            try:
                eq_df = pd.DataFrame(eq)
                fig_eq = go.Figure()
                fig_eq.add_trace(go.Scatter(
                    x=eq_df["time"], y=eq_df["equity"],
                    mode="lines+markers", fill="tozeroy", name="Equity",
                    line=dict(color="#6366f1", width=2.5),
                    fillcolor="rgba(99,102,241,0.1)",
                    marker=dict(size=6, color="#6366f1"),
                ))
                fig_eq.add_hline(y=STARTING_CAPITAL, line_dash="dash", line_color="#f59e0b",
                                 annotation_text=f"Start ₹{STARTING_CAPITAL:,.0f}")
                fig_eq.update_layout(**PLT_LAYOUT, height=380,
                                     xaxis_title="Time", yaxis_title="Equity (₹)")
                style_fig(fig_eq)
                st.plotly_chart(fig_eq, use_container_width=True)
            except Exception as e:
                st.warning(f"⚠️ Chart error: {e}")

# ── MARKET CALENDAR ──────────────────────────────────────────────────────
elif page == "📅 Market Calendar":
    hero("📅", "Market Calendar",
         "<span class='ui-badge badge-nse'>NSE</span>",
         "NSE trading holidays & upcoming events")
    NSE_HOLIDAYS_2025 = [
        ("Jan 26", "Republic Day"), ("Feb 19", "Chhatrapati Shivaji Maharaj Jayanti"),
        ("Mar 14", "Holi"), ("Mar 31", "Id-Ul-Fitr (Ramzan Id)"),
        ("Apr 10", "Shri Ram Navami"), ("Apr 14", "Dr. Baba Saheb Ambedkar Jayanti"),
        ("Apr 18", "Good Friday"), ("May 1", "Maharashtra Day"),
        ("Jun 7", "Id-Ul-Adha (Bakri Id)"), ("Jul 6", "Muharram"),
        ("Aug 15", "Independence Day"), ("Aug 27", "Ganesh Chaturthi"),
        ("Oct 2", "Mahatma Gandhi Jayanti / Dussehra"),
        ("Oct 21", "Diwali Laxmi Pujan (Muhurat Trading)"),
        ("Oct 22", "Diwali Balipratipada"), ("Oct 28", "Gurunanak Jayanti"),
        ("Dec 25", "Christmas"),
    ]
    st.markdown("### 🗓️ NSE Holidays 2025")
    hol_df = pd.DataFrame(NSE_HOLIDAYS_2025, columns=["Date", "Holiday"])
    st.dataframe(hol_df, use_container_width=True, hide_index=True)
    divider()
    st.markdown("### ⏰ Trading Hours")
    tc1, tc2 = st.columns(2)
    with tc1:
        st.markdown("""
        | Session | Time (IST) |
        |---|---|
        | Pre-Open | 9:00 AM – 9:15 AM |
        | Normal Market | 9:15 AM – 3:30 PM |
        | Post-Close | 3:40 PM – 4:00 PM |
        """)
    with tc2:
        st.markdown("""
        | Day | Status |
        |---|---|
        | Monday – Friday | Trading |
        | Saturday | Closed |
        | Sunday | Closed |
        | Public Holidays | Closed |
        """)
