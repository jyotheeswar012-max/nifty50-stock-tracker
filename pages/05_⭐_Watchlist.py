"""
Page: Saved Watchlists (session-persistent + JSON export/import)
Users build named watchlists, track live prices, and export/import as JSON.
Note: True persistence across browser sessions requires a backend DB;
this version uses st.session_state + JSON download/upload as a workaround
compatible with Streamlit Community Cloud (no secrets needed).
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json
import io
from datetime import datetime
import pytz
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Watchlist", page_icon="⭐", layout="wide")

NIFTY50_NAMES = [
    "Reliance Industries","HDFC Bank","ICICI Bank","Infosys","TCS",
    "Bharti Airtel","ITC","Kotak Mahindra Bank","Larsen & Toubro",
    "HCL Technologies","Axis Bank","State Bank of India","Bajaj Finance",
    "Wipro","Asian Paints","Maruti Suzuki","Sun Pharmaceutical",
    "Titan Company","UltraTech Cement","ONGC","NTPC","Power Grid Corp",
    "Mahindra & Mahindra","Tata Motors","Tata Steel","JSW Steel",
    "Hindalco Industries","Adani Enterprises","Adani Ports","Bajaj Finserv",
    "Bajaj Auto","Hero MotoCorp","Cipla","Dr. Reddy's Labs",
    "Divi's Laboratories","Eicher Motors","Grasim Industries",
    "HDFC Life Insurance","SBI Life Insurance","IndusInd Bank",
    "Tata Consumer Products","Britannia Industries","Nestle India",
    "Hindustan Unilever","Coal India","BPCL","Tech Mahindra",
    "L&T Finance","Shriram Finance","Bharat Electronics",
]
NIFTY50_SYMS = [
    "RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","TCS.NS",
    "BHARTIARTL.NS","ITC.NS","KOTAKBANK.NS","LT.NS","HCLTECH.NS",
    "AXISBANK.NS","SBIN.NS","BAJFINANCE.NS","WIPRO.NS","ASIANPAINT.NS",
    "MARUTI.NS","SUNPHARMA.NS","TITAN.NS","ULTRACEMCO.NS","ONGC.NS",
    "NTPC.NS","POWERGRID.NS","M&M.NS","TATAMOTORS.NS","TATASTEEL.NS",
    "JSWSTEEL.NS","HINDALCO.NS","ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS",
    "BAJAJAUTO.NS","HEROMOTOCO.NS","CIPLA.NS","DRREDDY.NS","DIVISLAB.NS",
    "EICHERMOT.NS","GRASIM.NS","HDFCLIFE.NS","SBILIFE.NS","INDUSINDBK.NS",
    "TATACONSUM.NS","BRITANNIA.NS","NESTLEIND.NS","HINDUNILVR.NS","COALINDIA.NS",
    "BPCL.NS","TECHM.NS","LTF.NS","SHRIRAMFIN.NS","BEL.NS",
]
NAME_TO_SYM = dict(zip(NIFTY50_NAMES, NIFTY50_SYMS))

def safe_float(val, default=0.0):
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default

@st.cache_data(ttl=60)
def get_live_prices(symbols: tuple) -> dict:
    prices = {}
    try:
        raw = yf.download(list(symbols), period="2d", auto_adjust=True,
                          progress=False, group_by="ticker")
        for sym in symbols:
            try:
                if isinstance(raw.columns, pd.MultiIndex):
                    if sym in raw.columns.get_level_values(0):
                        s = raw[sym]["Close"].dropna()
                    elif "Close" in raw.columns.get_level_values(0):
                        s = raw["Close"][sym].dropna()
                    else:
                        s = pd.Series()
                else:
                    s = raw["Close"].dropna() if "Close" in raw.columns else pd.Series()
                if len(s) >= 2:
                    prices[sym] = (safe_float(s.iloc[-1]), safe_float(s.iloc[-2]))
                elif len(s) == 1:
                    prices[sym] = (safe_float(s.iloc[0]), None)
            except Exception:
                pass
    except Exception:
        pass
    return prices

# ---- Session state init ----
if "watchlists" not in st.session_state:
    st.session_state.watchlists = {"My Watchlist": []}
if "active_wl" not in st.session_state:
    st.session_state.active_wl = "My Watchlist"

st.title("⭐ Watchlists")
st.markdown("""
Build **named watchlists**, track live prices, and **export/import** as JSON
to preserve them across sessions.
""")

# ---- Sidebar-style list management ----
wl_names = list(st.session_state.watchlists.keys())
col_wl, col_main = st.columns([1, 3])

with col_wl:
    st.subheader("📂 Lists")
    for name in wl_names:
        count = len(st.session_state.watchlists[name])
        if st.button(f"{name} ({count})", key=f"wl_sel_{name}",
                     use_container_width=True,
                     type="primary" if name == st.session_state.active_wl else "secondary"):
            st.session_state.active_wl = name
            st.rerun()
    st.markdown("---")
    new_name = st.text_input("➕ New list name", key="new_wl_name")
    if st.button("➕ Create", use_container_width=True):
        if new_name and new_name not in st.session_state.watchlists:
            st.session_state.watchlists[new_name] = []
            st.session_state.active_wl = new_name
            st.rerun()
    if len(wl_names) > 1:
        if st.button("🗑️ Delete current", use_container_width=True, type="secondary"):
            del st.session_state.watchlists[st.session_state.active_wl]
            st.session_state.active_wl = list(st.session_state.watchlists.keys())[0]
            st.rerun()
    st.markdown("---")
    # Export
    export_data = json.dumps(st.session_state.watchlists, indent=2)
    st.download_button("📥 Export JSON", export_data,
        file_name="watchlists.json", mime="application/json",
        use_container_width=True)
    # Import
    uploaded = st.file_uploader("📤 Import JSON", type="json", key="wl_upload")
    if uploaded:
        try:
            imported = json.load(uploaded)
            if isinstance(imported, dict):
                st.session_state.watchlists.update(imported)
                st.success("✅ Imported!")
                st.rerun()
        except Exception as e:
            st.error(f"❌ {e}")

with col_main:
    active = st.session_state.active_wl
    st.subheader(f"⭐ {active}")

    # Add stock
    ca, cb = st.columns([3,1])
    with ca:
        add_name = st.selectbox("Add stock", NIFTY50_NAMES, key="wl_add_stock")
    with cb:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add", use_container_width=True, key="wl_add_btn"):
            sym = NAME_TO_SYM[add_name]
            entry = {"name": add_name, "symbol": sym,
                     "added": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%d %b %H:%M")}
            if sym not in [x["symbol"] for x in st.session_state.watchlists[active]]:
                st.session_state.watchlists[active].append(entry)
                st.success(f"✅ Added {add_name}")
                st.rerun()
            else:
                st.info(f"{add_name} already in list.")

    wl = st.session_state.watchlists[active]
    if not wl:
        st.info("💡 Watchlist is empty. Add stocks above.")
    else:
        syms_tuple = tuple(x["symbol"] for x in wl)
        with st.spinner("Loading live prices..."):
            prices = get_live_prices(syms_tuple)

        rows = []
        for i, entry in enumerate(wl):
            sym  = entry["symbol"]
            pair = prices.get(sym)
            curr = pair[0] if pair else None
            prev = pair[1] if pair and len(pair) > 1 else None
            chg  = (curr - prev) if curr and prev else None
            pct  = (chg / prev * 100) if chg and prev else None
            arrow = "🟢" if pct and pct > 0 else ("🔴" if pct and pct < 0 else "⚪")
            rows.append({
                "#":         i + 1,
                "Company":   entry["name"],
                "Symbol":    sym.replace(".NS",""),
                "Price (₹)": f"₹{curr:,.2f}" if curr else "N/A",
                "Change (₹)": f"{chg:+.2f}" if chg else "N/A",
                "Change %":  f"{arrow} {pct:+.2f}%" if pct else "N/A",
                "Added":     entry.get("added",""),
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("---")
        col_r, col_clr = st.columns([1, 3])
        with col_r:
            rm_name = st.selectbox("Remove", [e["name"] for e in wl], key="wl_rm")
            if st.button("🗑️ Remove", use_container_width=True):
                st.session_state.watchlists[active] = [
                    x for x in wl if x["name"] != rm_name
                ]
                st.rerun()
        with col_clr:
            if st.button("🧹 Clear list", type="secondary"):
                st.session_state.watchlists[active] = []
                st.rerun()

        # Mini sparkline chart
        st.subheader("📉 30-Day Sparklines")
        sel_spark = st.multiselect(
            "Compare", [e["name"] for e in wl],
            default=[wl[0]["name"]] if wl else []
        )
        if sel_spark:
            try:
                import plotly.graph_objects as go
                fig_sp = go.Figure()
                COLORS = ["#00e5ff","#ffd600","#69f0ae","#ff6d00","#ea80fc","#ff6e40"]
                sym_lookup = {e["name"]: e["symbol"] for e in wl}
                for i_c, name_s in enumerate(sel_spark):
                    sym_s = sym_lookup.get(name_s)
                    if not sym_s: continue
                    h = yf.Ticker(sym_s).history(period="1mo", auto_adjust=True)
                    if h is None or h.empty: continue
                    base = safe_float(h["Close"].iloc[0], 1)
                    norm = h["Close"] / base * 100
                    fig_sp.add_trace(go.Scatter(
                        x=h.index, y=norm, mode="lines", name=name_s,
                        line=dict(color=COLORS[i_c % len(COLORS)], width=2)))
                fig_sp.update_layout(
                    title="Normalized 30-Day Performance (Base=100)",
                    template="plotly_dark", height=380,
                    xaxis_title="Date", yaxis_title="Normalized Price",
                )
                st.plotly_chart(fig_sp, use_container_width=True)
            except Exception as e:
                st.warning(f"⚠️ {e}")
