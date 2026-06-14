import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import pytz
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Paper Trading", page_icon="🎮", layout="wide")

from utils.theme import inject, inject_topbar
inject()

try:
    from utils.supabase_auth import get_current_user, logout, is_guest, login_nudge
except Exception:
    def get_current_user(): return None
    def logout(): pass
    def is_guest(): return True
    def login_nudge(f=""): st.info("💡 Sign in to save your data.")

user = get_current_user()
inject_topbar(user=user)

try:
    from textblob import TextBlob
    TEXTBLOB_OK = True
except ImportError:
    TEXTBLOB_OK = False

NIFTY50_NAMES = ["Reliance Industries","HDFC Bank","ICICI Bank","Infosys","TCS","Bharti Airtel","ITC","Kotak Mahindra Bank","Larsen & Toubro","HCL Technologies","Axis Bank","State Bank of India","Bajaj Finance","Wipro","Asian Paints","Maruti Suzuki","Sun Pharmaceutical","Titan Company","UltraTech Cement","ONGC","NTPC","Power Grid Corp","Mahindra & Mahindra","Tata Motors","Tata Steel","JSW Steel","Hindalco Industries","Adani Enterprises","Adani Ports","Bajaj Finserv","Bajaj Auto","Hero MotoCorp","Cipla","Dr. Reddy's Labs","Divi's Laboratories","Eicher Motors","Grasim Industries","HDFC Life Insurance","SBI Life Insurance","IndusInd Bank","Tata Consumer Products","Britannia Industries","Nestle India","Hindustan Unilever","Coal India","BPCL","Tech Mahindra","L&T Finance","Shriram Finance","Bharat Electronics"]
NIFTY50_SYMS = {"Reliance Industries":"RELIANCE.NS","HDFC Bank":"HDFCBANK.NS","ICICI Bank":"ICICIBANK.NS","Infosys":"INFY.NS","TCS":"TCS.NS","Bharti Airtel":"BHARTIARTL.NS","ITC":"ITC.NS","Kotak Mahindra Bank":"KOTAKBANK.NS","Larsen & Toubro":"LT.NS","HCL Technologies":"HCLTECH.NS","Axis Bank":"AXISBANK.NS","State Bank of India":"SBIN.NS","Bajaj Finance":"BAJFINANCE.NS","Wipro":"WIPRO.NS","Asian Paints":"ASIANPAINT.NS","Maruti Suzuki":"MARUTI.NS","Sun Pharmaceutical":"SUNPHARMA.NS","Titan Company":"TITAN.NS","UltraTech Cement":"ULTRACEMCO.NS","ONGC":"ONGC.NS","NTPC":"NTPC.NS","Power Grid Corp":"POWERGRID.NS","Mahindra & Mahindra":"M&M.NS","Tata Motors":"TATAMOTORS.NS","Tata Steel":"TATASTEEL.NS","JSW Steel":"JSWSTEEL.NS","Hindalco Industries":"HINDALCO.NS","Adani Enterprises":"ADANIENT.NS","Adani Ports":"ADANIPORTS.NS","Bajaj Finserv":"BAJAJFINSV.NS","Bajaj Auto":"BAJAJAUTO.NS","Hero MotoCorp":"HEROMOTOCO.NS","Cipla":"CIPLA.NS","Dr. Reddy's Labs":"DRREDDY.NS","Divi's Laboratories":"DIVISLAB.NS","Eicher Motors":"EICHERMOT.NS","Grasim Industries":"GRASIM.NS","HDFC Life Insurance":"HDFCLIFE.NS","SBI Life Insurance":"SBILIFE.NS","IndusInd Bank":"INDUSINDBK.NS","Tata Consumer Products":"TATACONSUM.NS","Britannia Industries":"BRITANNIA.NS","Nestle India":"NESTLEIND.NS","Hindustan Unilever":"HINDUNILVR.NS","Coal India":"COALINDIA.NS","BPCL":"BPCL.NS","Tech Mahindra":"TECHM.NS","L&T Finance":"LTF.NS","Shriram Finance":"SHRIRAMFIN.NS","Bharat Electronics":"BEL.NS"}

STARTING_CAPITAL = 1_000_000.0
IST_TZ = pytz.timezone("Asia/Kolkata")

PLT_LAYOUT = dict(paper_bgcolor="#ffffff",plot_bgcolor="#fafafa",font=dict(color="#1e293b",family="Inter, sans-serif",size=12),title_font=dict(size=15,color="#0f172a"),margin=dict(l=16,r=16,t=48,b=16),legend=dict(font=dict(color="#1e293b",size=12),bgcolor="rgba(255,255,255,0.85)",bordercolor="#e2e8f0",borderwidth=1))
AXIS_STYLE = dict(tickfont=dict(color="#1e293b",size=11,family="Inter, sans-serif"),title_font=dict(color="#0f172a",size=12,family="Inter, sans-serif"),linecolor="#cbd5e1",gridcolor="#f1f5f9",zerolinecolor="#cbd5e1")

def style_fig(fig):
    fig.update_xaxes(**AXIS_STYLE); fig.update_yaxes(**AXIS_STYLE); return fig

def _sf(v, d=0.0):
    try:
        f = float(v)
        return d if (np.isnan(f) or np.isinf(f)) else f
    except:
        return d

@st.cache_data(ttl=60)
def _live_price(sym):
    for period, interval in [("1d", "1m"), ("5d", None)]:
        try:
            kw = dict(period=period, auto_adjust=True)
            if interval:
                kw["interval"] = interval
            h = yf.Ticker(sym).history(**kw)
            if h is not None and not h.empty:
                c = h["Close"]
                if isinstance(c, pd.DataFrame):
                    c = c.iloc[:, 0]
                p = _sf(c.iloc[-1])
                if p > 0:
                    return p
        except:
            pass
    return None

for k, v in [("pt_balance", STARTING_CAPITAL), ("pt_holdings", {}), ("pt_trades", []), ("pt_equity", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

def _snapshot():
    try:
        pv = sum(_sf(_live_price(s) or hd["avg_price"]) * _sf(hd["qty"]) for s, hd in st.session_state.pt_holdings.items())
        st.session_state.pt_equity.append({"time": datetime.now(IST_TZ).strftime("%H:%M:%S"), "equity": round(st.session_state.pt_balance + pv, 2)})
    except:
        pass

name = user["full_name"] if user else "Guest"

# --- Hero banner (safe: no nested quotes inside f-string) ---
badge_class = "badge-live" if user else "badge-hist"
badge_label = "\u2705 " + name if user else "\ud83d\udc64 Guest"
st.markdown(
    '<div class="hero-banner">'
    '<div class="hero-icon">\ud83c\udfae</div>'
    '<div>'
    '<div class="hero-title">Paper Trading</div>'
    '<div class="hero-sub">'
    '<span class="ui-badge ' + badge_class + '">' + badge_label + '</span>'
    '&nbsp;&nbsp;Virtual \u20b910,00,000 \u2014 zero risk, real prices'
    '</div></div></div>',
    unsafe_allow_html=True,
)

if is_guest():
    login_nudge("save your paper trading progress")

try:
    port_val = sum(_sf(_live_price(s) or hd["avg_price"]) * _sf(hd["qty"]) for s, hd in st.session_state.pt_holdings.items())
except:
    port_val = 0.0

total_eq = st.session_state.pt_balance + port_val
pnl = total_eq - STARTING_CAPITAL
pnl_pct = pnl / STARTING_CAPITAL * 100

st.markdown("<p class='sec-label'>\ud83d\udcb0 Account Summary</p>", unsafe_allow_html=True)
pa, pb, pc, pd_col, pe = st.columns(5)
pa.metric("Cash", f"\u20b9{st.session_state.pt_balance:,.0f}")
pb.metric("Portfolio", f"\u20b9{port_val:,.0f}")
pc.metric("Total Equity", f"\u20b9{total_eq:,.0f}")
pd_col.metric("Net P&L", f"\u20b9{pnl:+,.0f}", delta=f"{pnl_pct:+.2f}%")
pe.metric("Trades", str(len(st.session_state.pt_trades)))

col_reset, col_pdf = st.columns([3, 1])
with col_reset:
    if st.button("\ud83d\udd04 Reset Account", key="pt_reset"):
        for k, v in [("pt_balance", STARTING_CAPITAL), ("pt_holdings", {}), ("pt_trades", []), ("pt_equity", [])]:
            st.session_state[k] = v
        st.success("\u2705 Account reset to \u20b910,00,000")
        st.rerun()
with col_pdf:
    if st.button("\ud83d\udcc4 PDF Report", type="primary", use_container_width=True, key="pt_pdf"):
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "NSE Tracker - Paper Trading Report", ln=True, align="C")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 8, f"Generated: {datetime.now(IST_TZ).strftime('%Y-%m-%d %H:%M IST')}", ln=True, align="C")
            pdf.cell(0, 8, f"User: {name}", ln=True, align="C")
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 10, "Account Summary", ln=True)
            pdf.set_font("Helvetica", "", 11)
            for lbl, val in [
                ("Starting Capital", f"Rs.{STARTING_CAPITAL:,.2f}"),
                ("Cash Balance", f"Rs.{st.session_state.pt_balance:,.2f}"),
                ("Portfolio Value", f"Rs.{port_val:,.2f}"),
                ("Total Equity", f"Rs.{total_eq:,.2f}"),
                ("Net P&L", f"Rs.{pnl:+,.2f}"),
                ("Total Trades", str(len(st.session_state.pt_trades))),
            ]:
                pdf.cell(60, 8, lbl + ":", border=0)
                pdf.cell(0, 8, val, ln=True)
            pdf_bytes = bytes(pdf.output())
            st.download_button(
                "\u2b07\ufe0f Download PDF",
                data=pdf_bytes,
                file_name=f"paper_trading_{datetime.now(IST_TZ).strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                key="pt_dl",
            )
        except Exception as e:
            st.warning(f"\u26a0\ufe0f PDF error: {e}")

st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)
tab_buy, tab_sell, tab_port, tab_log, tab_chart = st.tabs(
    ["\ud83d\udfe2  Buy", "\ud83d\udd34  Sell", "\ud83d\udcbc  Portfolio", "\ud83d\udcdc  Trade Log", "\ud83d\udcc8  Equity Curve"]
)

with tab_buy:
    st.markdown("<p class='sec-label'>\ud83d\udfe2 Place a Buy Order</p>", unsafe_allow_html=True)
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        buy_stock = st.selectbox("Stock", NIFTY50_NAMES, key="pt_buy_stock")
    with bc2:
        buy_qty = st.number_input("Quantity", min_value=1, value=1, step=1, key="pt_buy_qty")
    buy_sym = NIFTY50_SYMS[buy_stock]
    with bc3:
        buy_price = _live_price(buy_sym)
        if buy_price and buy_price > 0:
            st.metric("Live Price", f"\u20b9{buy_price:,.2f}")
        else:
            st.warning("\u23f3 Price unavailable")
            buy_price = 0.0
    buy_cost = _sf(buy_price) * int(buy_qty)
    st.markdown(f"\ud83d\udcb0 **Order Value:** \u20b9{buy_cost:,.2f} &nbsp;|&nbsp; \ud83d\udcb5 **Cash:** \u20b9{st.session_state.pt_balance:,.2f}", unsafe_allow_html=True)
    if st.button("\ud83d\udfe2 Execute Buy", type="primary", key="pt_exec_buy"):
        if buy_price <= 0:
            st.error("\u274c Cannot fetch live price.")
        elif buy_cost > st.session_state.pt_balance:
            st.error(f"\u274c Insufficient balance. Need \u20b9{buy_cost:,.2f}")
        else:
            hh = st.session_state.pt_holdings
            if buy_sym in hh:
                old = hh[buy_sym]
                tq = old["qty"] + buy_qty
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
            _snapshot()
            st.success(f"\u2705 Bought {buy_qty}\u00d7{buy_stock} @ \u20b9{buy_price:,.2f}")
            st.rerun()

with tab_sell:
    st.markdown("<p class='sec-label'>\ud83d\udd34 Place a Sell Order</p>", unsafe_allow_html=True)
    if not st.session_state.pt_holdings:
        st.info("\ud83d\udca1 No holdings yet. Buy some stocks first.")
    else:
        held_names = [st.session_state.pt_holdings[s]["name"] for s in st.session_state.pt_holdings]
        held_syms = list(st.session_state.pt_holdings.keys())
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            sell_name = st.selectbox("Stock", held_names, key="pt_sell_stock")
        sell_sym = held_syms[held_names.index(sell_name)]
        held_qty = st.session_state.pt_holdings[sell_sym]["qty"]
        with sc2:
            sell_qty = st.number_input("Quantity", min_value=1, max_value=held_qty, value=1, step=1, key="pt_sell_qty")
        with sc3:
            sell_price = _live_price(sell_sym)
            if sell_price and sell_price > 0:
                st.metric("Live Price", f"\u20b9{sell_price:,.2f}")
            else:
                st.warning("\u23f3 Price unavailable")
                sell_price = 0.0
        avg_pr = st.session_state.pt_holdings[sell_sym]["avg_price"]
        sell_val = _sf(sell_price) * int(sell_qty)
        est_pnl = (_sf(sell_price) - avg_pr) * sell_qty
        st.markdown(f"\ud83d\udcb0 **Value:** \u20b9{sell_val:,.2f} | **Avg Buy:** \u20b9{avg_pr:,.2f} | **Est. P&L:** \u20b9{est_pnl:+,.2f}", unsafe_allow_html=True)
        if st.button("\ud83d\udd34 Execute Sell", type="primary", key="pt_exec_sell"):
            if sell_price <= 0:
                st.error("\u274c Cannot fetch live price.")
            else:
                hh = st.session_state.pt_holdings
                if sell_qty >= held_qty:
                    del hh[sell_sym]
                else:
                    hh[sell_sym]["qty"] -= sell_qty
                st.session_state.pt_balance += sell_val
                st.session_state.pt_trades.append({
                    "time": datetime.now(IST_TZ).strftime("%H:%M:%S"),
                    "stock": sell_name, "type": "SELL",
                    "qty": sell_qty, "price": round(sell_price, 2), "value": round(sell_val, 2),
                })
                _snapshot()
                st.success(f"\u2705 Sold {sell_qty}\u00d7{sell_name} @ \u20b9{sell_price:,.2f} | P&L: \u20b9{est_pnl:+,.2f}")
                st.rerun()

with tab_port:
    st.markdown("<p class='sec-label'>\ud83d\udcbc Current Holdings</p>", unsafe_allow_html=True)
    if not st.session_state.pt_holdings:
        st.info("\ud83d\udca1 No open positions.")
    else:
        rows_port = []
        for sym, hd in st.session_state.pt_holdings.items():
            try:
                lp = _sf(_live_price(sym) or hd["avg_price"])
                val = lp * hd["qty"]
                pl = (lp - hd["avg_price"]) * hd["qty"]
                pct = ((lp - hd["avg_price"]) / hd["avg_price"] * 100) if hd["avg_price"] else 0
                rows_port.append({
                    "Stock": hd["name"],
                    "Qty": hd["qty"],
                    "Avg Buy": f"\u20b9{hd['avg_price']:,.2f}",
                    "Live": f"\u20b9{lp:,.2f}",
                    "Value": f"\u20b9{val:,.2f}",
                    "P&L": f"\u20b9{pl:+,.2f}",
                    "P&L %": f"{pct:+.2f}%",
                })
            except:
                continue
        if rows_port:
            st.dataframe(pd.DataFrame(rows_port), use_container_width=True, hide_index=True)

with tab_log:
    st.markdown("<p class='sec-label'>\ud83d\udcdc Trade History</p>", unsafe_allow_html=True)
    if not st.session_state.pt_trades:
        st.info("\ud83d\udca1 No trades yet.")
    else:
        st.dataframe(pd.DataFrame(st.session_state.pt_trades[::-1]), use_container_width=True, hide_index=True)

with tab_chart:
    st.markdown("<p class='sec-label'>\ud83d\udcc8 Equity Curve</p>", unsafe_allow_html=True)
    eq = st.session_state.pt_equity
    if len(eq) < 2:
        st.info("\ud83d\udca1 Execute at least 2 trades to see the equity curve.")
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
                             annotation_text=f"Start \u20b9{STARTING_CAPITAL:,.0f}")
            fig_eq.update_layout(**PLT_LAYOUT, height=400, xaxis_title="Time", yaxis_title="Equity (\u20b9)")
            style_fig(fig_eq)
            st.plotly_chart(fig_eq, use_container_width=True)
        except Exception as e:
            st.warning(f"\u26a0\ufe0f {e}")

st.caption("\u26a0\ufe0f Virtual money only \u2014 not financial advice.")
