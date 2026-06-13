"""
Page: Paper Trading Simulator
Guests can use paper trading fully (session only); login nudge shown to encourage saving.
"""
import streamlit as st
from utils.supabase_auth import get_current_user, is_guest, login_nudge

st.set_page_config(page_title="Paper Trading", page_icon="📝", layout="wide")
user  = get_current_user()
guest = is_guest()

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import pytz
import io
import warnings
warnings.filterwarnings("ignore")

NIFTY50_NAMES = [
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
def get_live_price(sym):
    try:
        h = yf.Ticker(sym).history(period="1d", interval="1m")
        if h is not None and not h.empty:
            return safe_float(h["Close"].iloc[-1])
    except Exception:
        pass
    return None

for k, v in [("pt_balance", 1_000_000.0), ("pt_holdings", {}), ("pt_trades", []), ("pt_equity", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

IST = pytz.timezone("Asia/Kolkata")

def _snapshot_equity():
    port_val = sum(
        (get_live_price(s) or h["avg_price"]) * h["qty"]
        for s, h in st.session_state.pt_holdings.items()
    )
    total = st.session_state.pt_balance + port_val
    st.session_state.pt_equity.append({
        "time": datetime.now(IST).strftime("%H:%M:%S"),
        "equity": round(total, 2),
    })

def generate_pdf(user_info):
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Nifty50 Tracker — Paper Trading Report", ln=True, align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Generated: {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}", ln=True, align="C")
        if user_info:
            pdf.cell(0, 8, f"User: {user_info['full_name']} ({user_info['email']})", ln=True, align="C")
        else:
            pdf.cell(0, 8, "User: Guest Session", ln=True, align="C")
        pdf.ln(4)

        port_val = sum(
            (get_live_price(s) or h["avg_price"]) * h["qty"]
            for s, h in st.session_state.pt_holdings.items()
        )
        total_equity = st.session_state.pt_balance + port_val
        pnl = total_equity - 1_000_000.0

        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "Account Summary", ln=True)
        pdf.set_font("Helvetica", "", 11)
        for label, val in [
            ("Starting Capital", "₹10,00,000.00"),
            ("Cash Balance",     f"₹{st.session_state.pt_balance:,.2f}"),
            ("Portfolio Value",  f"₹{port_val:,.2f}"),
            ("Total Equity",     f"₹{total_equity:,.2f}"),
            ("Net P&L",          f"₹{pnl:+,.2f}"),
            ("Total Trades",     str(len(st.session_state.pt_trades))),
        ]:
            pdf.cell(60, 8, label + ":", border=0)
            pdf.cell(0, 8, val, ln=True)

        if st.session_state.pt_trades:
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 10, "Trade Log", ln=True)
            pdf.set_font("Helvetica", "B", 9)
            headers = ["Time", "Stock", "Type", "Qty", "Price", "Value"]
            widths  = [22, 52, 16, 16, 26, 28]
            for h_label, w in zip(headers, widths):
                pdf.cell(w, 7, h_label, border=1)
            pdf.ln()
            pdf.set_font("Helvetica", "", 9)
            for trade in st.session_state.pt_trades[-50:]:
                row = [
                    str(trade.get("time", "")),
                    str(trade.get("stock", ""))[:28],
                    str(trade.get("type", "")),
                    str(trade.get("qty", "")),
                    f"₹{trade.get('price', 0):,.2f}",
                    f"₹{trade.get('value', 0):,.2f}",
                ]
                for cell, w in zip(row, widths):
                    pdf.cell(w, 6, cell, border=1)
                pdf.ln()

        return bytes(pdf.output())
    except ImportError:
        return None
    except Exception:
        return None

# ── UI ────────────────────────────────────────────────────────────────
st.title("📝 Paper Trading Simulator")
if guest:
    st.caption("👤 Browsing as **Guest** — paper trading works but progress resets on refresh")
    login_nudge("save your paper trading progress")
else:
    st.caption(f"Signed in as **{user['full_name']}** • Virtual money only • Starting capital ₹10,00,000")

port_val = sum(
    (get_live_price(sym) or h["avg_price"]) * h["qty"]
    for sym, h in st.session_state.pt_holdings.items()
)
total_equity = st.session_state.pt_balance + port_val
pnl_total    = total_equity - 1_000_000.0
pnl_pct      = pnl_total / 10000.0  # as percentage of 10L

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("💵 Cash",       f"₹{st.session_state.pt_balance:,.2f}")
m2.metric("💼 Portfolio", f"₹{port_val:,.2f}")
m3.metric("📊 Equity",   f"₹{total_equity:,.2f}")
m4.metric("📈 Net P&L",   f"₹{pnl_total:+,.2f}",
          delta=f"{'+'  if pnl_pct >= 0 else ''}{pnl_pct:.2f}%")
m5.metric("🔄 Trades",   len(st.session_state.pt_trades))

st.markdown("---")

# ── Order form ────────────────────────────────────────────────────────────────
st.subheader("🛒 Place Order")
col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
with col1: stock_name = st.selectbox("Stock", NIFTY50_NAMES, key="pt_stock")
with col2: order_type = st.radio("Order", ["BUY", "SELL"], horizontal=True)
with col3: qty        = st.number_input("Qty", min_value=1, value=10, step=1)
with col4:
    st.markdown("<br>", unsafe_allow_html=True)
    execute = st.button("⚡ Execute", type="primary", use_container_width=True)

cur_sym    = NAME_TO_SYM[stock_name]
live_price = get_live_price(cur_sym)
if live_price:
    st.info(f"📊 **{stock_name}**: ₹{live_price:,.2f} | Order value: ₹{live_price*qty:,.2f}")

if execute:
    price = live_price or 0.0
    if price <= 0:
        st.error("❌ Could not fetch live price.")
    elif order_type == "BUY":
        cost = price * qty
        if cost > st.session_state.pt_balance:
            st.error(f"❌ Insufficient balance. Need ₹{cost:,.2f}, have ₹{st.session_state.pt_balance:,.2f}")
        else:
            st.session_state.pt_balance -= cost
            hld = st.session_state.pt_holdings.get(cur_sym, {"qty": 0, "avg_price": 0.0})
            total_qty = hld["qty"] + qty
            avg = (hld["avg_price"] * hld["qty"] + price * qty) / total_qty
            st.session_state.pt_holdings[cur_sym] = {"qty": total_qty, "avg_price": avg, "name": stock_name}
            st.session_state.pt_trades.append({
                "time": datetime.now(IST).strftime("%H:%M:%S"), "stock": stock_name,
                "type": "BUY", "qty": qty, "price": price, "value": cost,
            })
            _snapshot_equity()
            st.success(f"✅ BUY {qty} x {stock_name} @ ₹{price:,.2f} = ₹{cost:,.2f}")
            st.rerun()
    else:
        holding = st.session_state.pt_holdings.get(cur_sym)
        if not holding or holding["qty"] < qty:
            held = holding["qty"] if holding else 0
            st.error(f"❌ Not enough shares. Holding {held}.")
        else:
            proceeds = price * qty
            pnl_trade = (price - holding["avg_price"]) * qty
            st.session_state.pt_balance += proceeds
            new_qty = holding["qty"] - qty
            if new_qty == 0:
                del st.session_state.pt_holdings[cur_sym]
            else:
                st.session_state.pt_holdings[cur_sym]["qty"] = new_qty
            st.session_state.pt_trades.append({
                "time": datetime.now(IST).strftime("%H:%M:%S"), "stock": stock_name,
                "type": "SELL", "qty": qty, "price": price, "value": proceeds, "pnl": pnl_trade,
            })
            _snapshot_equity()
            st.success(f"✅ SELL {qty} x {stock_name} @ ₹{price:,.2f} | P&L: ₹{pnl_trade:+,.2f}")
            st.rerun()

st.markdown("---")

# ── Holdings ────────────────────────────────────────────────────────────────
if st.session_state.pt_holdings:
    st.subheader("💼 Current Holdings")
    h_rows = []
    for sym_h, hld in st.session_state.pt_holdings.items():
        lp     = get_live_price(sym_h) or hld["avg_price"]
        pnl_h  = (lp - hld["avg_price"]) * hld["qty"]
        h_rows.append({
            "Stock":      hld["name"],
            "Qty":        hld["qty"],
            "Avg Price":  f"₹{hld['avg_price']:,.2f}",
            "Live Price": f"₹{lp:,.2f}",
            "P&L":        f"₹{pnl_h:+,.2f}",
            "📊":         "🟢" if pnl_h >= 0 else "🔴",
        })
    st.dataframe(pd.DataFrame(h_rows), use_container_width=True, hide_index=True)

# ── P&L History Chart ──────────────────────────────────────────────────────────
if len(st.session_state.pt_equity) >= 2:
    st.markdown("---")
    st.subheader("📈 Equity History")
    eq_df  = pd.DataFrame(st.session_state.pt_equity)
    max_eq = eq_df["equity"].max()
    min_eq = eq_df["equity"].min()
    try:
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(
            x=eq_df.index, y=eq_df["equity"],
            mode="lines+markers", fill="tozeroy", name="Total Equity",
            line=dict(color="#00c853", width=2), marker=dict(size=5),
            hovertemplate="₹%{y:,.2f}<extra></extra>",
        ))
        fig_eq.add_hline(y=1_000_000, line_dash="dash", line_color="#ffd600",
                         annotation_text="Starting Capital ₹10,00,000")
        fig_eq.add_annotation(x=int(eq_df["equity"].idxmax()), y=max_eq,
            text=f"Max: ₹{max_eq:,.0f}", showarrow=True, arrowhead=2,
            font=dict(color="#00c853"), bgcolor="rgba(0,200,83,.15)")
        fig_eq.add_annotation(x=int(eq_df["equity"].idxmin()), y=min_eq,
            text=f"Min: ₹{min_eq:,.0f}", showarrow=True, arrowhead=2,
            font=dict(color="#ff1744"), bgcolor="rgba(255,23,68,.15)")
        fig_eq.update_layout(
            title="Portfolio Equity Over Time", template="plotly_dark", height=380,
            xaxis_title="Trade #", yaxis_title="Equity (₹)",
        )
        st.plotly_chart(fig_eq, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ Chart error: {e}")

# ── Trade log + exports ──────────────────────────────────────────────────────────
if st.session_state.pt_trades:
    st.markdown("---")
    st.subheader("📜 Trade Log")
    trade_df = pd.DataFrame(st.session_state.pt_trades)
    st.dataframe(trade_df, use_container_width=True, hide_index=True)

    st.markdown("**📥 Export**")
    ec1, ec2 = st.columns(2)
    with ec1:
        csv_buf = io.StringIO()
        trade_df.to_csv(csv_buf, index=False)
        st.download_button(
            label="📊 Download CSV",
            data=csv_buf.getvalue(),
            file_name=f"trade_log_{datetime.now(IST).strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with ec2:
        pdf_bytes = generate_pdf(user)
        if pdf_bytes:
            st.download_button(
                label="📄 Download PDF Report",
                data=pdf_bytes,
                file_name=f"portfolio_report_{datetime.now(IST).strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.info("💡 Add `fpdf2` to requirements.txt for PDF export.")

# ── Reset ────────────────────────────────────────────────────────────────
st.markdown("---")
if st.button("🔄 Reset Paper Trading Account", type="secondary"):
    for k in ["pt_balance", "pt_holdings", "pt_trades", "pt_equity"]:
        st.session_state.pop(k, None)
    st.rerun()
