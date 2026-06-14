"""
Page: Paper Trading Simulator  —  light theme, fully error-proofed
"""
import streamlit as st

try:
    st.set_page_config(page_title="Paper Trading", page_icon="📝", layout="wide")
except Exception:
    pass

try:
    from utils.theme import inject
    inject()
except Exception:
    pass

try:
    from utils.supabase_auth import get_current_user, is_guest
except Exception:
    def get_current_user(): return None
    def is_guest(): return True

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import pytz
import warnings
warnings.filterwarnings("ignore")

user  = get_current_user()
guest = is_guest()

NAMES = [
    "Reliance Industries","HDFC Bank","ICICI Bank","Infosys","TCS",
    "Bharti Airtel","ITC","Kotak Mahindra Bank","Larsen & Toubro","HCL Technologies",
    "Axis Bank","State Bank of India","Bajaj Finance","Wipro","Asian Paints",
    "Maruti Suzuki","Sun Pharmaceutical","Titan Company","UltraTech Cement","ONGC",
    "NTPC","Power Grid Corp","Mahindra & Mahindra","Tata Motors","Tata Steel",
    "JSW Steel","Hindalco Industries","Adani Enterprises","Adani Ports","Bajaj Finserv",
    "Bajaj Auto","Hero MotoCorp","Cipla","Dr. Reddy's Labs","Divi's Laboratories",
    "Eicher Motors","Grasim Industries","HDFC Life Insurance","SBI Life Insurance",
    "IndusInd Bank","Tata Consumer Products","Britannia Industries","Nestle India",
    "Hindustan Unilever","Coal India","BPCL","Tech Mahindra","L&T Finance",
    "Shriram Finance","Bharat Electronics",
]
SYMS = [
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
N2S = dict(zip(NAMES, SYMS))

IST = pytz.timezone("Asia/Kolkata")
STARTING_CAPITAL = 1_000_000.0

def safe_float(v, d=0.0):
    try:
        f = float(v)
        return d if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return d

@st.cache_data(ttl=60)
def get_live_price(sym: str):
    """Fetch latest price — tries 1m intraday first, falls back to 5d daily."""
    try:
        h = yf.Ticker(sym).history(period="1d", interval="1m")
        if h is not None and not h.empty:
            p = safe_float(h["Close"].iloc[-1])
            if p > 0:
                return p
    except Exception:
        pass
    try:
        h = yf.Ticker(sym).history(period="5d")
        if h is not None and not h.empty:
            p = safe_float(h["Close"].iloc[-1])
            if p > 0:
                return p
    except Exception:
        pass
    return None

# Init session state
for k, v in [
    ("pt_balance",  STARTING_CAPITAL),
    ("pt_holdings", {}),
    ("pt_trades",   []),
    ("pt_equity",   []),
]:
    if k not in st.session_state:
        st.session_state[k] = v

def _snapshot_equity():
    try:
        port_val = sum(
            safe_float(get_live_price(s) or hd["avg_price"]) * safe_float(hd["qty"])
            for s, hd in st.session_state.pt_holdings.items()
        )
        st.session_state.pt_equity.append({
            "time":   datetime.now(IST).strftime("%H:%M:%S"),
            "equity": round(st.session_state.pt_balance + port_val, 2),
        })
    except Exception:
        pass

def generate_pdf():
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Nifty50 Tracker - Paper Trading Report", ln=True, align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Generated: {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}", ln=True, align="C")
        u = get_current_user()
        pdf.cell(0, 8,
            f"User: {u['full_name']} ({u['email']})" if u else "User: Guest Session",
            ln=True, align="C")
        pdf.ln(4)
        port_val = sum(
            safe_float(get_live_price(s) or hd["avg_price"]) * safe_float(hd["qty"])
            for s, hd in st.session_state.pt_holdings.items()
        )
        total_eq = st.session_state.pt_balance + port_val
        pnl      = total_eq - STARTING_CAPITAL
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "Account Summary", ln=True)
        pdf.set_font("Helvetica", "", 11)
        for label, val in [
            ("Starting Capital", f"Rs.{STARTING_CAPITAL:,.2f}"),
            ("Cash Balance",     f"Rs.{st.session_state.pt_balance:,.2f}"),
            ("Portfolio Value",  f"Rs.{port_val:,.2f}"),
            ("Total Equity",     f"Rs.{total_eq:,.2f}"),
            ("Net P&L",          f"Rs.{pnl:+,.2f}"),
            ("Total Trades",     str(len(st.session_state.pt_trades))),
        ]:
            pdf.cell(60, 8, label + ":", border=0)
            pdf.cell(0,  8, val, ln=True)
        trades = st.session_state.pt_trades
        if trades:
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 10, "Trade Log (last 50)", ln=True)
            pdf.set_font("Helvetica", "B", 9)
            headers = ["Time", "Stock", "Type", "Qty", "Price (Rs.)", "Value (Rs.)"]
            widths  = [24, 50, 16, 16, 30, 30]
            for h_lbl, w in zip(headers, widths):
                pdf.cell(w, 7, h_lbl, border=1)
            pdf.ln()
            pdf.set_font("Helvetica", "", 9)
            for tr in trades[-50:]:
                row = [
                    str(tr.get("time", "")),
                    str(tr.get("stock", ""))[:28],
                    str(tr.get("type", "")),
                    str(tr.get("qty", "")),
                    f"{tr.get('price', 0):,.2f}",
                    f"{tr.get('value', 0):,.2f}",
                ]
                for cell, w in zip(row, widths):
                    pdf.cell(w, 6, cell, border=1)
                pdf.ln()
        return bytes(pdf.output())
    except Exception as e:
        st.warning(f"⚠️ PDF generation failed: {e}")
        return None

# ── Header ────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:1rem;margin-bottom:.5rem;">
  <div style="width:52px;height:52px;border-radius:50%;
              background:linear-gradient(135deg,#10b981,#06b6d4);
              display:flex;align-items:center;justify-content:center;
              font-size:1.5rem;color:#fff;box-shadow:0 4px 14px rgba(16,185,129,.35);">
    📝
  </div>
  <div>
    <div style="font-size:1.7rem;font-weight:700;">Paper Trading Simulator</div>
    <div style="font-size:.85rem;color:#64748b;margin:0;">Trade with virtual ₹10,00,000 — zero risk, real prices</div>
  </div>
</div>
""", unsafe_allow_html=True)

if guest:
    st.markdown(
        "<span style='background:#94a3b8;color:#fff;padding:2px 10px;border-radius:99px;font-size:.75rem;'>👤 Guest — session only, sign in to save progress</span>",
        unsafe_allow_html=True)
else:
    name_display = user.get('full_name', 'User') if isinstance(user, dict) else 'User'
    st.markdown(
        f"<span style='background:#10b981;color:#fff;padding:2px 10px;border-radius:99px;font-size:.75rem;'>✅ {name_display} — Virtual ₹10,00,000 capital</span>",
        unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Account summary ────────────────────────────────────────────────────────
try:
    port_val = sum(
        safe_float(get_live_price(s) or hd["avg_price"]) * safe_float(hd["qty"])
        for s, hd in st.session_state.pt_holdings.items()
    )
except Exception:
    port_val = 0.0

total_eq = st.session_state.pt_balance + port_val
pnl      = total_eq - STARTING_CAPITAL
pnl_pct  = (pnl / STARTING_CAPITAL * 100)

st.markdown("#### 💰 Account Summary")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("💵 Cash Balance",   f"₹{st.session_state.pt_balance:,.0f}")
m2.metric("💼 Portfolio Value", f"₹{port_val:,.0f}")
m3.metric("⚖️ Total Equity",    f"₹{total_eq:,.0f}")
m4.metric("📈 Net P&L",        f"₹{pnl:+,.0f}", delta=f"{pnl_pct:+.2f}%")
m5.metric("🔄 Total Trades",   str(len(st.session_state.pt_trades)))

col_r, col_pdf = st.columns([3, 1])
with col_r:
    if st.button("🔄 Reset Account", key="pt_reset"):
        for k, v in [("pt_balance", STARTING_CAPITAL), ("pt_holdings", {}),
                     ("pt_trades", []), ("pt_equity", [])]:
            st.session_state[k] = v
        st.success("✅ Account reset to ₹10,00,000")
        st.rerun()
with col_pdf:
    if st.button("📄 Download PDF Report", type="primary", use_container_width=True, key="pt_pdf"):
        pdf_bytes = generate_pdf()
        if pdf_bytes:
            st.download_button(
                label="⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"paper_trading_{datetime.now(IST).strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                key="pt_dl",
            )

st.markdown("<br>", unsafe_allow_html=True)

# ── Trade Panel ───────────────────────────────────────────────────────────
tab_buy, tab_sell, tab_port, tab_log, tab_chart = st.tabs([
    "🟢  Buy", "🔴  Sell", "💼  Portfolio", "📜  Trade Log", "📈  Equity Chart"
])

# ── BUY ───────────────────────────────────────────────────────────────────
with tab_buy:
    st.markdown("#### 🟢 Place a Buy Order")
    bc1, bc2, bc3 = st.columns(3)
    with bc1: buy_stock = st.selectbox("Stock", NAMES, key="pt_buy_stock")
    with bc2: buy_qty   = st.number_input("Qty", min_value=1, value=1, step=1, key="pt_buy_qty")
    with bc3:
        buy_sym   = N2S[buy_stock]
        buy_price = get_live_price(buy_sym)
        if buy_price and buy_price > 0:
            st.metric("Live Price", f"₹{buy_price:,.2f}")
        else:
            st.warning("⏳ Price unavailable")
            buy_price = 0.0

    buy_cost = safe_float(buy_price) * int(buy_qty)
    st.markdown(
        f"💰 **Order Value:** ₹{buy_cost:,.2f} &nbsp;|&nbsp; "
        f"💵 **Available Cash:** ₹{st.session_state.pt_balance:,.2f}",
        unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🟢 Execute Buy", type="primary", key="pt_exec_buy"):
        if buy_price <= 0:
            st.error("❌ Cannot fetch live price. Try again.")
        elif buy_cost > st.session_state.pt_balance:
            st.error(f"❌ Insufficient balance. Need ₹{buy_cost:,.2f}, have ₹{st.session_state.pt_balance:,.2f}")
        else:
            h = st.session_state.pt_holdings
            if buy_sym in h:
                old       = h[buy_sym]
                total_qty = old["qty"] + buy_qty
                avg       = (old["avg_price"] * old["qty"] + buy_price * buy_qty) / total_qty
                h[buy_sym] = {"qty": total_qty, "avg_price": round(avg, 4), "name": buy_stock}
            else:
                h[buy_sym] = {"qty": buy_qty, "avg_price": round(buy_price, 4), "name": buy_stock}
            st.session_state.pt_balance -= buy_cost
            st.session_state.pt_trades.append({
                "time":  datetime.now(IST).strftime("%H:%M:%S"),
                "stock": buy_stock, "type": "BUY",
                "qty":   buy_qty,   "price": round(buy_price, 2),
                "value": round(buy_cost, 2),
            })
            _snapshot_equity()
            st.success(f"✅ Bought {buy_qty} × {buy_stock} @ ₹{buy_price:,.2f}")
            st.rerun()

# ── SELL ───────────────────────────────────────────────────────────────────
with tab_sell:
    st.markdown("#### 🔴 Place a Sell Order")
    holdings = st.session_state.pt_holdings
    if not holdings:
        st.info("💡 No holdings yet. Buy some stocks first.")
    else:
        held_names = [holdings[s]["name"] for s in holdings]
        held_syms  = list(holdings.keys())
        sc1, sc2, sc3 = st.columns(3)
        with sc1: sell_name = st.selectbox("Stock", held_names, key="pt_sell_stock")
        sell_sym  = held_syms[held_names.index(sell_name)]
        held_qty  = holdings[sell_sym]["qty"]
        with sc2: sell_qty = st.number_input("Qty", min_value=1, max_value=held_qty, value=1, key="pt_sell_qty")
        with sc3:
            sell_price = get_live_price(sell_sym)
            if sell_price and sell_price > 0:
                st.metric("Live Price", f"₹{sell_price:,.2f}")
            else:
                st.warning("⏳ Price unavailable")
                sell_price = 0.0

        sell_value = safe_float(sell_price) * int(sell_qty)
        avg_price  = holdings[sell_sym]["avg_price"]
        est_pnl    = (safe_float(sell_price) - avg_price) * sell_qty
        st.markdown(
            f"💰 **Order Value:** ₹{sell_value:,.2f} &nbsp;|&nbsp; "
            f"📊 **Avg Buy:** ₹{avg_price:,.2f} &nbsp;|&nbsp; "
            f"📈 **Est. P&L:** ₹{est_pnl:+,.2f}",
            unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔴 Execute Sell", type="primary", key="pt_exec_sell"):
            if sell_price <= 0:
                st.error("❌ Cannot fetch live price. Try again.")
            else:
                h = st.session_state.pt_holdings
                if sell_qty >= held_qty:
                    del h[sell_sym]
                else:
                    h[sell_sym]["qty"] -= sell_qty
                st.session_state.pt_balance += sell_value
                st.session_state.pt_trades.append({
                    "time":  datetime.now(IST).strftime("%H:%M:%S"),
                    "stock": sell_name, "type": "SELL",
                    "qty":   sell_qty,  "price": round(sell_price, 2),
                    "value": round(sell_value, 2),
                })
                _snapshot_equity()
                st.success(f"✅ Sold {sell_qty} × {sell_name} @ ₹{sell_price:,.2f} | P&L: ₹{est_pnl:+,.2f}")
                st.rerun()

# ── PORTFOLIO ──────────────────────────────────────────────────────────────
with tab_port:
    st.markdown("#### 💼 Current Holdings")
    if not st.session_state.pt_holdings:
        st.info("💡 No open positions. Go to Buy tab to start trading.")
    else:
        rows = []
        for sym, hd in st.session_state.pt_holdings.items():
            try:
                lp  = safe_float(get_live_price(sym) or hd["avg_price"])
                val = lp * hd["qty"]
                pl  = (lp - hd["avg_price"]) * hd["qty"]
                pct = ((lp - hd["avg_price"]) / hd["avg_price"] * 100) if hd["avg_price"] else 0
                rows.append({
                    "Stock":         hd["name"],
                    "Symbol":        sym.replace(".NS", ""),
                    "Qty":           hd["qty"],
                    "Avg Price (₹)": f"₹{hd['avg_price']:,.2f}",
                    "Live Price (₹)":f"₹{lp:,.2f}",
                    "Value (₹)":     f"₹{val:,.2f}",
                    "P&L (₹)":       f"₹{pl:+,.2f}",
                    "P&L %":         f"{pct:+.2f}%",
                })
            except Exception:
                continue
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── TRADE LOG ─────────────────────────────────────────────────────────────
with tab_log:
    st.markdown("#### 📜 Trade History")
    if not st.session_state.pt_trades:
        st.info("💡 No trades yet.")
    else:
        log_df = pd.DataFrame(st.session_state.pt_trades[::-1])
        st.dataframe(log_df, use_container_width=True, hide_index=True)

# ── EQUITY CHART ───────────────────────────────────────────────────────────
with tab_chart:
    st.markdown("#### 📈 Equity Curve")
    eq = st.session_state.pt_equity
    if len(eq) < 2:
        st.info("💡 Execute at least 2 trades to see your equity curve.")
    else:
        try:
            eq_df = pd.DataFrame(eq)
            fig   = go.Figure()
            fig.add_trace(go.Scatter(
                x=eq_df["time"], y=eq_df["equity"],
                mode="lines+markers", fill="tozeroy", name="Equity",
                line=dict(color="#6366f1", width=2.5),
                fillcolor="rgba(99,102,241,0.1)",
                marker=dict(size=6, color="#6366f1"),
            ))
            fig.add_hline(y=STARTING_CAPITAL, line_dash="dash", line_color="#f59e0b",
                          annotation_text=f"Start ₹{STARTING_CAPITAL:,.0f}")
            fig.update_layout(
                template="plotly_white", height=380,
                paper_bgcolor="#ffffff", plot_bgcolor="#fafafa",
                font_color="#1a1a2e",
                xaxis_title="Time", yaxis_title="Equity (₹)",
                margin=dict(t=30, b=30),
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ Chart error: {e}")
