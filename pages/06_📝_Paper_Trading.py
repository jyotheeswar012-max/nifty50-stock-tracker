import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import pytz
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Paper Trading — NSE Tracker",
    page_icon="🎮",
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

NIFTY50 = [
    {"symbol":"RELIANCE.NS",   "name":"Reliance Industries"},
    {"symbol":"HDFCBANK.NS",   "name":"HDFC Bank"},
    {"symbol":"ICICIBANK.NS",  "name":"ICICI Bank"},
    {"symbol":"INFY.NS",       "name":"Infosys"},
    {"symbol":"TCS.NS",        "name":"TCS"},
    {"symbol":"BHARTIARTL.NS", "name":"Bharti Airtel"},
    {"symbol":"ITC.NS",        "name":"ITC"},
    {"symbol":"KOTAKBANK.NS",  "name":"Kotak Mahindra Bank"},
    {"symbol":"LT.NS",         "name":"Larsen & Toubro"},
    {"symbol":"HCLTECH.NS",    "name":"HCL Technologies"},
    {"symbol":"AXISBANK.NS",   "name":"Axis Bank"},
    {"symbol":"SBIN.NS",       "name":"State Bank of India"},
    {"symbol":"BAJFINANCE.NS", "name":"Bajaj Finance"},
    {"symbol":"WIPRO.NS",      "name":"Wipro"},
    {"symbol":"ASIANPAINT.NS", "name":"Asian Paints"},
    {"symbol":"MARUTI.NS",     "name":"Maruti Suzuki"},
    {"symbol":"SUNPHARMA.NS",  "name":"Sun Pharmaceutical"},
    {"symbol":"TITAN.NS",      "name":"Titan Company"},
    {"symbol":"ULTRACEMCO.NS", "name":"UltraTech Cement"},
    {"symbol":"ONGC.NS",       "name":"ONGC"},
    {"symbol":"NTPC.NS",       "name":"NTPC"},
    {"symbol":"POWERGRID.NS",  "name":"Power Grid Corp"},
    {"symbol":"M&M.NS",        "name":"Mahindra & Mahindra"},
    {"symbol":"TATAMOTORS.NS", "name":"Tata Motors"},
    {"symbol":"TATASTEEL.NS",  "name":"Tata Steel"},
    {"symbol":"JSWSTEEL.NS",   "name":"JSW Steel"},
    {"symbol":"HINDALCO.NS",   "name":"Hindalco Industries"},
    {"symbol":"ADANIENT.NS",   "name":"Adani Enterprises"},
    {"symbol":"ADANIPORTS.NS", "name":"Adani Ports"},
    {"symbol":"BAJAJFINSV.NS", "name":"Bajaj Finserv"},
    {"symbol":"BAJAJAUTO.NS",  "name":"Bajaj Auto"},
    {"symbol":"HEROMOTOCO.NS", "name":"Hero MotoCorp"},
    {"symbol":"CIPLA.NS",      "name":"Cipla"},
    {"symbol":"DRREDDY.NS",    "name":"Dr. Reddy's Labs"},
    {"symbol":"DIVISLAB.NS",   "name":"Divi's Laboratories"},
    {"symbol":"EICHERMOT.NS",  "name":"Eicher Motors"},
    {"symbol":"GRASIM.NS",     "name":"Grasim Industries"},
    {"symbol":"HDFCLIFE.NS",   "name":"HDFC Life Insurance"},
    {"symbol":"SBILIFE.NS",    "name":"SBI Life Insurance"},
    {"symbol":"INDUSINDBK.NS", "name":"IndusInd Bank"},
    {"symbol":"TATACONSUM.NS", "name":"Tata Consumer Products"},
    {"symbol":"BRITANNIA.NS",  "name":"Britannia Industries"},
    {"symbol":"NESTLEIND.NS",  "name":"Nestle India"},
    {"symbol":"HINDUNILVR.NS", "name":"Hindustan Unilever"},
    {"symbol":"COALINDIA.NS",  "name":"Coal India"},
    {"symbol":"BPCL.NS",       "name":"BPCL"},
    {"symbol":"TECHM.NS",      "name":"Tech Mahindra"},
    {"symbol":"LTF.NS",        "name":"L&T Finance"},
    {"symbol":"SHRIRAMFIN.NS", "name":"Shriram Finance"},
    {"symbol":"BEL.NS",        "name":"Bharat Electronics"},
]
PT_NAMES = [s["name"]   for s in NIFTY50]
PT_N2S   = {s["name"]: s["symbol"] for s in NIFTY50}

STARTING_CAPITAL = 1_000_000.0
IST_TZ           = pytz.timezone("Asia/Kolkata")

PLT_LAYOUT = dict(
    paper_bgcolor="#ffffff", plot_bgcolor="#fafafa",
    font=dict(color="#1e293b", family="Inter, sans-serif", size=12),
    title_font=dict(size=15, color="#0f172a", family="Inter, sans-serif"),
    margin=dict(l=16, r=16, t=48, b=16),
    legend=dict(font=dict(color="#1e293b", size=12),
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor="#e2e8f0", borderwidth=1),
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

def _sf(v, d=0.0):
    try:
        f = float(v)
        return d if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return d

@st.cache_data(ttl=60)
def _live_price(sym: str):
    for period, interval in [("1d","1m"),("5d",None)]:
        try:
            kw = dict(period=period, auto_adjust=True)
            if interval: kw["interval"] = interval
            h = yf.Ticker(sym).history(**kw)
            if h is not None and not h.empty:
                c = h["Close"]
                if isinstance(c, pd.DataFrame): c = c.iloc[:, 0]
                p = _sf(c.iloc[-1])
                if p > 0: return p
        except Exception:
            pass
    return None

# ─ Session state init ───────────────────────────────────────────────────
for k, v in [("pt_balance", STARTING_CAPITAL), ("pt_holdings", {}),
             ("pt_trades", []), ("pt_equity", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

def _snapshot():
    try:
        pv = sum(
            _sf(_live_price(s) or hd["avg_price"]) * _sf(hd["qty"])
            for s, hd in st.session_state.pt_holdings.items()
        )
        st.session_state.pt_equity.append({
            "time":   datetime.now(IST_TZ).strftime("%H:%M:%S"),
            "equity": round(st.session_state.pt_balance + pv, 2),
        })
    except Exception:
        pass

# ─ Sidebar ──────────────────────────────────────────────────────────
user = get_current_user()
name = user["full_name"] if user else "Guest"
try:
    st.sidebar.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/NSE_Logo.svg/200px-NSE_Logo.svg.png",
        width=110)
except Exception:
    pass
st.sidebar.markdown("<h3 style='color:#fff;margin:0 0 .4rem 0;font-size:1rem;'>Paper Trading</h3>",
                    unsafe_allow_html=True)
if user:
    st.sidebar.markdown(f"<span class='ui-badge badge-live'>👤 {name}</span>",
                        unsafe_allow_html=True)
    if st.sidebar.button("🚧 Sign Out", key="pt_logout"):
        logout(); st.rerun()
else:
    st.sidebar.markdown(
        "<span class='ui-badge badge-hist' style='background:rgba(255,255,255,.15);color:#e0e7ff!important;'>👤 Guest</span>",
        unsafe_allow_html=True)
    try:
        st.sidebar.page_link("pages/00_🔐_Login.py", label="🔐 Sign In")
    except Exception:
        pass
st.sidebar.markdown("---")
try:
    st.sidebar.page_link("app.py", label="🏠 Back to Main")
except Exception:
    pass
st.sidebar.markdown("---")
st.sidebar.caption("📊 Prices: Yahoo Finance")
st.sidebar.caption("⚠️ Virtual money only")

# ─ Hero ──────────────────────────────────────────────────────────
badge_class = "badge-live" if not is_guest() else "badge-hist"
badge_text  = f"✅ {name}" if not is_guest() else "👤 Guest"
st.markdown(f"""
<div class="hero-banner">
  <div class="hero-icon">🎮</div>
  <div>
    <div class="hero-title">Paper Trading</div>
    <div class="hero-sub">
      <span class='ui-badge {badge_class}'>{badge_text}</span>&nbsp;&nbsp;
      Virtual ₹10,00,000 — zero risk, real prices
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

if is_guest():
    login_nudge("save your paper trading progress")

# ─ Account summary ───────────────────────────────────────────────────
try:
    port_val = sum(
        _sf(_live_price(s) or hd["avg_price"]) * _sf(hd["qty"])
        for s, hd in st.session_state.pt_holdings.items()
    )
except Exception:
    port_val = 0.0

total_eq = st.session_state.pt_balance + port_val
pnl      = total_eq - STARTING_CAPITAL
pnl_pct  = pnl / STARTING_CAPITAL * 100

st.markdown("<p class='sec-label'>💰 Account Summary</p>", unsafe_allow_html=True)
pa, pb, pc, pd_col, pe = st.columns(5)
pa.metric("Cash",           f"₹{st.session_state.pt_balance:,.0f}")
pb.metric("Portfolio",      f"₹{port_val:,.0f}")
pc.metric("Total Equity",   f"₹{total_eq:,.0f}")
pd_col.metric("Net P&L",    f"₹{pnl:+,.0f}", delta=f"{pnl_pct:+.2f}%")
pe.metric("Trades",         str(len(st.session_state.pt_trades)))

col_reset, col_pdf = st.columns([3, 1])
with col_reset:
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
            pdf.cell(0, 10, "NSE Tracker — Paper Trading Report", ln=True, align="C")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 8, f"Generated: {datetime.now(IST_TZ).strftime('%Y-%m-%d %H:%M IST')}",
                     ln=True, align="C")
            pdf.cell(0, 8, f"User: {name}", ln=True, align="C")
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 10, "Account Summary", ln=True)
            pdf.set_font("Helvetica", "", 11)
            for lbl, val in [
                ("Starting Capital", f"Rs.{STARTING_CAPITAL:,.2f}"),
                ("Cash Balance",     f"Rs.{st.session_state.pt_balance:,.2f}"),
                ("Portfolio Value",  f"Rs.{port_val:,.2f}"),
                ("Total Equity",     f"Rs.{total_eq:,.2f}"),
                ("Net P&L",          f"Rs.{pnl:+,.2f}"),
                ("Total Trades",     str(len(st.session_state.pt_trades))),
            ]:
                pdf.cell(60, 8, lbl + ":", border=0)
                pdf.cell(0,  8, val, ln=True)
            if st.session_state.pt_trades:
                pdf.ln(4)
                pdf.set_font("Helvetica", "B", 13)
                pdf.cell(0, 10, "Trade History", ln=True)
                pdf.set_font("Helvetica", "", 9)
                for t in st.session_state.pt_trades[-30:]:
                    pdf.cell(0, 7,
                        f"{t.get('time','')}  {t.get('type','')}  {t.get('stock','')}  "
                        f"Qty:{t.get('qty','')}  @Rs.{t.get('price','')}",
                        ln=True)
            pdf_bytes = bytes(pdf.output())
            st.download_button(
                "⬇️ Download PDF", data=pdf_bytes,
                file_name=f"paper_trading_{datetime.now(IST_TZ).strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf", key="pt_dl")
        except Exception as e:
            st.warning(f"⚠️ PDF error: {e}")

st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)

# ─ Tabs ──────────────────────────────────────────────────────────
tab_buy, tab_sell, tab_port, tab_log, tab_chart = st.tabs([
    "🟢  Buy", "🔴  Sell", "💼  Portfolio", "📜  Trade Log", "📈  Equity Curve"
])

# BUY TAB
with tab_buy:
    st.markdown("<p class='sec-label'>🟢 Place a Buy Order</p>", unsafe_allow_html=True)
    bc1, bc2, bc3 = st.columns(3)
    with bc1: buy_stock = st.selectbox("Stock", PT_NAMES, key="pt_buy_stock")
    with bc2: buy_qty   = st.number_input("Quantity", min_value=1, value=1, step=1, key="pt_buy_qty")
    buy_sym   = PT_N2S[buy_stock]
    with bc3:
        buy_price = _live_price(buy_sym)
        if buy_price and buy_price > 0:
            st.metric("Live Price", f"₹{buy_price:,.2f}")
        else:
            st.warning("⏳ Price unavailable")
            buy_price = 0.0
    buy_cost = _sf(buy_price) * int(buy_qty)
    st.markdown(
        f"💰 **Order Value:** ₹{buy_cost:,.2f} &nbsp;|&nbsp; "
        f"💵 **Available Cash:** ₹{st.session_state.pt_balance:,.2f}",
        unsafe_allow_html=True)
    if st.button("🟢 Execute Buy", type="primary", key="pt_exec_buy"):
        if buy_price <= 0:
            st.error("❌ Cannot fetch live price. Try again shortly.")
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
                "time":  datetime.now(IST_TZ).strftime("%H:%M:%S"),
                "stock": buy_stock, "type": "BUY",
                "qty":   buy_qty,   "price": round(buy_price, 2),
                "value": round(buy_cost, 2),
            })
            _snapshot()
            st.success(f"✅ Bought {buy_qty} × {buy_stock} @ ₹{buy_price:,.2f}")
            st.rerun()

# SELL TAB
with tab_sell:
    st.markdown("<p class='sec-label'>🔴 Place a Sell Order</p>", unsafe_allow_html=True)
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
        with sc2: sell_qty = st.number_input("Quantity", min_value=1, max_value=held_qty,
                                              value=1, step=1, key="pt_sell_qty")
        with sc3:
            sell_price = _live_price(sell_sym)
            if sell_price and sell_price > 0:
                st.metric("Live Price", f"₹{sell_price:,.2f}")
            else:
                st.warning("⏳ Price unavailable")
                sell_price = 0.0
        avg_pr    = pt_holdings[sell_sym]["avg_price"]
        sell_val  = _sf(sell_price) * int(sell_qty)
        est_pnl   = (_sf(sell_price) - avg_pr) * sell_qty
        st.markdown(
            f"💰 **Value:** ₹{sell_val:,.2f} &nbsp;|&nbsp; "
            f"📊 **Avg Buy:** ₹{avg_pr:,.2f} &nbsp;|&nbsp; "
            f"📈 **Est. P&L:** ₹{est_pnl:+,.2f}",
            unsafe_allow_html=True)
        if st.button("🔴 Execute Sell", type="primary", key="pt_exec_sell"):
            if sell_price <= 0:
                st.error("❌ Cannot fetch live price.")
            else:
                hh = st.session_state.pt_holdings
                if sell_qty >= held_qty:
                    del hh[sell_sym]
                else:
                    hh[sell_sym]["qty"] -= sell_qty
                st.session_state.pt_balance += sell_val
                st.session_state.pt_trades.append({
                    "time":  datetime.now(IST_TZ).strftime("%H:%M:%S"),
                    "stock": sell_name, "type": "SELL",
                    "qty":   sell_qty,  "price": round(sell_price, 2),
                    "value": round(sell_val, 2),
                })
                _snapshot()
                st.success(f"✅ Sold {sell_qty} × {sell_name} @ ₹{sell_price:,.2f} | P&L: ₹{est_pnl:+,.2f}")
                st.rerun()

# PORTFOLIO TAB
with tab_port:
    st.markdown("<p class='sec-label'>💼 Current Holdings</p>", unsafe_allow_html=True)
    if not st.session_state.pt_holdings:
        st.info("💡 No open positions.")
    else:
        rows_port = []
        for sym, hd in st.session_state.pt_holdings.items():
            try:
                lp2  = _sf(_live_price(sym) or hd["avg_price"])
                val2 = lp2 * hd["qty"]
                pl2  = (lp2 - hd["avg_price"]) * hd["qty"]
                pct2 = ((lp2 - hd["avg_price"]) / hd["avg_price"] * 100) if hd["avg_price"] else 0
                rows_port.append({
                    "Stock":       hd["name"],
                    "Qty":         hd["qty"],
                    "Avg Buy (₹)": f"₹{hd['avg_price']:,.2f}",
                    "Live (₹)":    f"₹{lp2:,.2f}",
                    "Value (₹)":   f"₹{val2:,.2f}",
                    "P&L (₹)":     f"₹{pl2:+,.2f}",
                    "P&L %":       f"{pct2:+.2f}%",
                })
            except Exception:
                continue
        if rows_port:
            st.dataframe(pd.DataFrame(rows_port), use_container_width=True, hide_index=True)
            try:
                import plotly.express as px
                vals_pie = [_sf(_live_price(s) or hd["avg_price"]) * _sf(hd["qty"])
                            for s, hd in st.session_state.pt_holdings.items()]
                names_pie= [hd["name"] for hd in st.session_state.pt_holdings.values()]
                fig_pie  = px.pie(values=vals_pie, names=names_pie,
                                  title="Portfolio Allocation",
                                  template="plotly_white", height=350)
                fig_pie.update_layout(**PLT_LAYOUT)
                st.plotly_chart(fig_pie, use_container_width=True)
            except Exception as e:
                st.warning(f"⚠️ {e}")

# TRADE LOG TAB
with tab_log:
    st.markdown("<p class='sec-label'>📜 Trade History</p>", unsafe_allow_html=True)
    if not st.session_state.pt_trades:
        st.info("💡 No trades yet.")
    else:
        st.dataframe(pd.DataFrame(st.session_state.pt_trades[::-1]),
                     use_container_width=True, hide_index=True)

# EQUITY CURVE TAB
with tab_chart:
    st.markdown("<p class='sec-label'>📈 Equity Curve</p>", unsafe_allow_html=True)
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
            fig_eq.update_layout(**PLT_LAYOUT, height=400,
                                 xaxis_title="Time", yaxis_title="Equity (₹)")
            style_fig(fig_eq)
            st.plotly_chart(fig_eq, use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ Chart error: {e}")
