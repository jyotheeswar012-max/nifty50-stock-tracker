# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Paper Portfolio", page_icon="[PP]", layout="wide")

try:
    from utils.theme import inject, inject_topbar
    inject()
except Exception:
    pass

try:
    from utils.supabase_auth import get_current_user
except Exception:
    def get_current_user(): return None

user = get_current_user()
try:
    inject_topbar(user=user)
except Exception:
    pass

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
NIFTY50_SYMS = {
    "Reliance Industries":"RELIANCE.NS","HDFC Bank":"HDFCBANK.NS","ICICI Bank":"ICICIBANK.NS",
    "Infosys":"INFY.NS","TCS":"TCS.NS","Bharti Airtel":"BHARTIARTL.NS","ITC":"ITC.NS",
    "Kotak Mahindra Bank":"KOTAKBANK.NS","Larsen & Toubro":"LT.NS","HCL Technologies":"HCLTECH.NS",
    "Axis Bank":"AXISBANK.NS","State Bank of India":"SBIN.NS","Bajaj Finance":"BAJFINANCE.NS",
    "Wipro":"WIPRO.NS","Asian Paints":"ASIANPAINT.NS","Maruti Suzuki":"MARUTI.NS",
    "Sun Pharmaceutical":"SUNPHARMA.NS","Titan Company":"TITAN.NS","UltraTech Cement":"ULTRACEMCO.NS",
    "ONGC":"ONGC.NS","NTPC":"NTPC.NS","Power Grid Corp":"POWERGRID.NS",
    "Mahindra & Mahindra":"M&M.NS","Tata Motors":"TATAMOTORS.NS","Tata Steel":"TATASTEEL.NS",
    "JSW Steel":"JSWSTEEL.NS","Hindalco Industries":"HINDALCO.NS","Adani Enterprises":"ADANIENT.NS",
    "Adani Ports":"ADANIPORTS.NS","Bajaj Finserv":"BAJAJFINSV.NS",
    "Bajaj Auto":"BAJAJAUTO.NS","Hero MotoCorp":"HEROMOTOCO.NS","Cipla":"CIPLA.NS",
    "Dr. Reddy's Labs":"DRREDDY.NS","Divi's Laboratories":"DIVISLAB.NS",
    "Eicher Motors":"EICHERMOT.NS","Grasim Industries":"GRASIM.NS",
    "HDFC Life Insurance":"HDFCLIFE.NS","SBI Life Insurance":"SBILIFE.NS",
    "IndusInd Bank":"INDUSINDBK.NS","Tata Consumer Products":"TATACONSUM.NS",
    "Britannia Industries":"BRITANNIA.NS","Nestle India":"NESTLEIND.NS",
    "Hindustan Unilever":"HINDUNILVR.NS","Coal India":"COALINDIA.NS","BPCL":"BPCL.NS",
    "Tech Mahindra":"TECHM.NS","L&T Finance":"LTF.NS",
    "Shriram Finance":"SHRIRAMFIN.NS","Bharat Electronics":"BEL.NS",
}

PLT_LAYOUT = dict(
    paper_bgcolor="#ffffff", plot_bgcolor="#fafafa",
    font=dict(color="#1e293b", family="Inter, sans-serif", size=12),
    title_font=dict(size=15, color="#0f172a"),
    margin=dict(l=16, r=16, t=48, b=16),
    legend=dict(font=dict(color="#1e293b", size=12), bgcolor="rgba(255,255,255,0.85)",
                bordercolor="#e2e8f0", borderwidth=1),
)
AXIS_STYLE = dict(
    tickfont=dict(color="#1e293b", size=11, family="Inter, sans-serif"),
    title_font=dict(color="#0f172a", size=12, family="Inter, sans-serif"),
    linecolor="#cbd5e1", gridcolor="#f1f5f9", zerolinecolor="#cbd5e1",
)

def rs(val, fmt=",.2f"):
    try:
        return "Rs." + format(float(val), fmt)
    except:
        return "Rs.0.00"

def style_fig(fig):
    fig.update_xaxes(**AXIS_STYLE)
    fig.update_yaxes(**AXIS_STYLE)
    return fig

st.markdown("""
<div class="hero-banner">
  <div class="hero-icon">[PP]</div>
  <div>
    <div class="hero-title">Paper Portfolio</div>
    <div class="hero-sub"><span class="ui-badge badge-sim">VIRTUAL</span>&nbsp; Track holdings &amp; backtest historical scenarios</div>
  </div>
</div>
""", unsafe_allow_html=True)

if "pp_holdings" not in st.session_state:
    st.session_state.pp_holdings = []

tab_port, tab_backtest = st.tabs(["Portfolio", "Historical Backtest"])

# ─────────────────────────────────────────────
# TAB 1 — PORTFOLIO
# ─────────────────────────────────────────────
with tab_port:
    st.markdown("<p class='sec-label'>Add a Holding</p>", unsafe_allow_html=True)
    with st.form("pp_add", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        with c1: sel_name = st.selectbox("Stock", NIFTY50_NAMES)
        with c2: qty = st.number_input("Qty", min_value=1, value=10, step=1)
        with c3: buy_p = st.number_input("Buy Price (Rs.)", min_value=0.01, value=100.0, step=1.0)
        with c4: note = st.text_input("Note", placeholder="Optional")
        submitted = st.form_submit_button("Add", type="primary")
        if submitted:
            st.session_state.pp_holdings.append({
                "stock": sel_name, "symbol": NIFTY50_SYMS.get(sel_name, ""),
                "qty": qty, "buy_price": buy_p,
                "note": note, "added": datetime.now().strftime("%d %b %Y"),
            })
            st.success("Added " + str(qty) + "x " + sel_name + " @ " + rs(buy_p))

    if not st.session_state.pp_holdings:
        st.info("No holdings yet. Add a stock above to get started!")
    else:
        st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)
        rows = []
        total_inv = 0.0
        total_cur = 0.0
        with st.spinner("Fetching live prices..."):
            for i, h in enumerate(st.session_state.pp_holdings):
                live = h["buy_price"]
                try:
                    tick = yf.Ticker(h["symbol"]).history(period="2d", auto_adjust=True)
                    if not tick.empty:
                        live = float(tick["Close"].iloc[-1])
                except Exception:
                    pass
                inv_val = h["buy_price"] * h["qty"]
                cur_val = live * h["qty"]
                pl = cur_val - inv_val
                pct = (pl / inv_val * 100) if inv_val > 0 else 0
                total_inv += inv_val
                total_cur += cur_val
                rows.append({
                    "#": i, "Stock": h["stock"], "Qty": h["qty"],
                    "Buy (Rs.)": round(h["buy_price"], 2),
                    "Live (Rs.)": round(live, 2),
                    "Invested (Rs.)": round(inv_val, 2),
                    "Current (Rs.)": round(cur_val, 2),
                    "P&L (Rs.)": round(pl, 2),
                    "Return (%)": round(pct, 2),
                    "Added": h["added"],
                    "Note": h.get("note", ""),
                })
        total_pl = total_cur - total_inv
        total_pct = (total_pl / total_inv * 100) if total_inv > 0 else 0
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Invested", rs(total_inv))
        m2.metric("Current", rs(total_cur))
        m3.metric("Total P&L", rs(total_pl, "+,.2f"))
        m4.metric("Return", f"{total_pct:+.2f}%")
        df = pd.DataFrame(rows)
        st.dataframe(df.drop(columns=["#"]), use_container_width=True, hide_index=True)

        st.markdown("<p class='sec-label'>Remove a Holding</p>", unsafe_allow_html=True)
        del_name = st.selectbox("Select to remove", [r["Stock"] for r in rows], key="pp_del_sel")
        if st.button("Remove", key="pp_del_btn"):
            idx = next((r["#"] for r in rows if r["Stock"] == del_name), None)
            if idx is not None:
                st.session_state.pp_holdings.pop(idx)
                st.success("Removed " + del_name)
                st.rerun()

        st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            try:
                fig_pl = px.bar(
                    df, x="Stock", y="P&L (Rs.)",
                    color="P&L (Rs.)",
                    color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
                    color_continuous_midpoint=0,
                    title="P&L per Stock", height=320, text="P&L (Rs.)",
                )
                fig_pl.update_traces(texttemplate="Rs.%{text:,.0f}", textposition="outside")
                fig_pl.update_layout(**PLT_LAYOUT, coloraxis_showscale=False)
                style_fig(fig_pl)
                st.plotly_chart(fig_pl, use_container_width=True)
            except Exception:
                pass
        with c2:
            try:
                fig_pie = px.pie(
                    df, names="Stock", values="Current (Rs.)",
                    title="Portfolio Allocation", height=320,
                    color_discrete_sequence=px.colors.qualitative.Vivid,
                )
                fig_pie.update_layout(**PLT_LAYOUT)
                st.plotly_chart(fig_pie, use_container_width=True)
            except Exception:
                pass

        if st.button("Clear All Holdings", key="pp_clear"):
            st.session_state.pp_holdings = []
            st.rerun()

# ─────────────────────────────────────────────
# TAB 2 — HISTORICAL BACKTEST
# ─────────────────────────────────────────────
with tab_backtest:
    st.markdown("<p class='sec-label'>Historical Backtest — What If I Had Invested?</p>", unsafe_allow_html=True)
    st.markdown(
        "Pick a stock, quantity, and date range to see exactly what your gain or loss would have been "
        "using real historical market prices.",
        unsafe_allow_html=False,
    )

    bt1, bt2, bt3 = st.columns(3)
    with bt1:
        bt_stock = st.selectbox("Stock", NIFTY50_NAMES, key="bt_stock")
    with bt2:
        bt_qty = st.number_input("Quantity", min_value=1, value=10, step=1, key="bt_qty")
    with bt3:
        bt_capital = st.number_input("Or enter capital (Rs.) [optional]", min_value=0.0, value=0.0, step=1000.0, key="bt_capital",
                                     help="If set, quantity will be auto-calculated from start price")

    dt1, dt2 = st.columns(2)
    today = date.today()
    default_start = today - timedelta(days=365)
    with dt1:
        bt_start = st.date_input("Buy Date (Start)", value=default_start, max_value=today - timedelta(days=2), key="bt_start")
    with dt2:
        bt_end = st.date_input("Sell Date (End)", value=today - timedelta(days=1), max_value=today, key="bt_end")

    if st.button("Run Backtest", type="primary", key="bt_run"):
        if bt_start >= bt_end:
            st.error("Start date must be before end date.")
        else:
            sym = NIFTY50_SYMS.get(bt_stock, "")
            with st.spinner("Fetching historical data..."):
                try:
                    # fetch data with extra buffer days to handle weekends/holidays
                    fetch_start = bt_start - timedelta(days=7)
                    fetch_end = bt_end + timedelta(days=2)
                    hist = yf.Ticker(sym).history(
                        start=fetch_start.strftime("%Y-%m-%d"),
                        end=fetch_end.strftime("%Y-%m-%d"),
                        auto_adjust=True,
                    )
                    if hist is None or hist.empty:
                        st.error("No historical data found for " + bt_stock + ". Try a different date range.")
                    else:
                        hist.index = pd.to_datetime(hist.index).tz_localize(None)
                        # filter to requested range for the chart
                        chart_data = hist[hist.index.date >= bt_start][hist.index.date <= bt_end].copy()
                        if chart_data.empty:
                            st.error("No trading data between " + str(bt_start) + " and " + str(bt_end) + ". Markets may have been closed.")
                        else:
                            close = chart_data["Close"]
                            if isinstance(close, pd.DataFrame):
                                close = close.iloc[:, 0]

                            buy_price = float(close.iloc[0])
                            sell_price = float(close.iloc[-1])
                            actual_buy_date = chart_data.index[0].date()
                            actual_sell_date = chart_data.index[-1].date()

                            # auto-calc qty from capital if given
                            qty_used = bt_qty
                            if bt_capital > 0:
                                qty_used = max(1, int(bt_capital // buy_price))

                            invested = buy_price * qty_used
                            current = sell_price * qty_used
                            pnl = current - invested
                            pnl_pct = (pnl / invested * 100) if invested > 0 else 0
                            holding_days = (actual_sell_date - actual_buy_date).days

                            # ── Summary metrics ──
                            st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)
                            st.markdown("**Backtest Result: " + bt_stock + "**", unsafe_allow_html=False)

                            col_a, col_b, col_c, col_d, col_e = st.columns(5)
                            col_a.metric("Buy Price", rs(buy_price), help="Actual first trading day in range")
                            col_b.metric("Sell Price", rs(sell_price), help="Actual last trading day in range")
                            col_c.metric("Qty", str(qty_used))
                            col_d.metric("Invested", rs(invested))
                            col_e.metric("Return", f"{pnl_pct:+.2f}%", delta=rs(pnl, "+,.2f"))

                            col_f, col_g, col_h = st.columns(3)
                            col_f.metric("Final Value", rs(current))
                            col_g.metric("Net P&L", rs(pnl, "+,.2f"))
                            col_h.metric("Holding Period", str(holding_days) + " days")

                            # verdict banner
                            if pnl >= 0:
                                st.success(
                                    "GAIN: If you had bought " + str(qty_used) + " shares of " + bt_stock +
                                    " on " + str(actual_buy_date) + " and sold on " + str(actual_sell_date) +
                                    ", you would have GAINED " + rs(pnl, "+,.2f") +
                                    " (" + f"{pnl_pct:+.2f}" + "%)"
                                )
                            else:
                                st.error(
                                    "LOSS: If you had bought " + str(qty_used) + " shares of " + bt_stock +
                                    " on " + str(actual_buy_date) + " and sold on " + str(actual_sell_date) +
                                    ", you would have LOST " + rs(abs(pnl)) +
                                    " (" + f"{pnl_pct:.2f}" + "%)"
                                )

                            # ── Price chart with invested line ──
                            st.markdown("<p class='sec-label'>Price Movement Over Period</p>", unsafe_allow_html=True)
                            fig_bt = go.Figure()
                            fig_bt.add_trace(go.Scatter(
                                x=chart_data.index, y=close,
                                mode="lines", name=bt_stock,
                                line=dict(color="#6366f1", width=2),
                                fill="tozeroy", fillcolor="rgba(99,102,241,0.07)",
                            ))
                            fig_bt.add_hline(
                                y=buy_price, line_dash="dash", line_color="#f59e0b",
                                annotation_text="Buy @ Rs." + format(buy_price, ",.2f"),
                                annotation_position="top left",
                            )
                            fig_bt.add_hline(
                                y=sell_price, line_dash="dot",
                                line_color="#10b981" if sell_price >= buy_price else "#ef4444",
                                annotation_text="Sell @ Rs." + format(sell_price, ",.2f"),
                                annotation_position="bottom right",
                            )
                            # mark buy and sell points
                            fig_bt.add_trace(go.Scatter(
                                x=[chart_data.index[0]], y=[buy_price],
                                mode="markers", name="Buy",
                                marker=dict(color="#f59e0b", size=12, symbol="triangle-up"),
                            ))
                            fig_bt.add_trace(go.Scatter(
                                x=[chart_data.index[-1]], y=[sell_price],
                                mode="markers", name="Sell",
                                marker=dict(
                                    color="#10b981" if sell_price >= buy_price else "#ef4444",
                                    size=12, symbol="triangle-down",
                                ),
                            ))
                            fig_bt.update_layout(
                                **PLT_LAYOUT,
                                height=380,
                                title=bt_stock + " | " + str(actual_buy_date) + " to " + str(actual_sell_date),
                                xaxis_title="Date",
                                yaxis_title="Price (Rs.)",
                            )
                            style_fig(fig_bt)
                            st.plotly_chart(fig_bt, use_container_width=True)

                            # ── Portfolio value curve ──
                            st.markdown("<p class='sec-label'>Portfolio Value Curve</p>", unsafe_allow_html=True)
                            port_val_series = close * qty_used
                            fig_pv = go.Figure()
                            fig_pv.add_trace(go.Scatter(
                                x=chart_data.index, y=port_val_series,
                                mode="lines", name="Portfolio Value",
                                line=dict(color="#0ea5e9", width=2),
                                fill="tozeroy", fillcolor="rgba(14,165,233,0.08)",
                            ))
                            fig_pv.add_hline(
                                y=invested, line_dash="dash", line_color="#94a3b8",
                                annotation_text="Invested Rs." + format(invested, ",.0f"),
                            )
                            fig_pv.update_layout(
                                **PLT_LAYOUT,
                                height=320,
                                title="Portfolio Value over Time (" + str(qty_used) + " shares)",
                                xaxis_title="Date",
                                yaxis_title="Value (Rs.)",
                            )
                            style_fig(fig_pv)
                            st.plotly_chart(fig_pv, use_container_width=True)

                            # ── Daily returns table ──
                            with st.expander("View Daily Price Data"):
                                daily_df = pd.DataFrame({
                                    "Date": chart_data.index.date,
                                    "Close (Rs.)": close.round(2).values,
                                    "Portfolio Value (Rs.)": (close * qty_used).round(2).values,
                                    "Daily P&L (Rs.)": ((close - buy_price) * qty_used).round(2).values,
                                    "Return (%)": (((close - buy_price) / buy_price) * 100).round(2).values,
                                })
                                st.dataframe(daily_df, use_container_width=True, hide_index=True)

                except Exception as e:
                    st.error("Error fetching data: " + str(e))

    else:
        st.info(
            "Select a stock, quantity or capital, choose your start date (buy) and end date (sell), "
            "then click Run Backtest to see your hypothetical gain or loss."
        )
