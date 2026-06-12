"""
Page: Paper Trading Simulator
Simulated trading with virtual capital — zero real money involved.

Features:
  - Virtual portfolio with configurable starting capital (default ₹10,00,000)
  - BUY / SELL orders on any Nifty-50 F&O stock
  - Live mark-to-market P&L via yfinance
  - Full trade log with entry price, exit price, realised P&L
  - Portfolio summary: holdings, unrealised P&L, cash balance
  - Risk metrics: win rate, avg trade P&L, max drawdown, total return
  - JSON export/import for persistence across sessions
  - Reset portfolio button
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import json
from datetime import datetime
from typing import Optional, Dict, List
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Paper Trading",
    page_icon="📝",
    layout="wide",
)

# ================================================================== constants

DEFAULT_CAPITAL: float = 1_000_000.0  # ₹10 Lakhs

NIFTY50_NAMES: List[str] = [
    "Reliance Industries", "HDFC Bank", "ICICI Bank", "Infosys", "TCS",
    "Bharti Airtel", "ITC", "Kotak Mahindra Bank", "Larsen & Toubro",
    "HCL Technologies", "Axis Bank", "State Bank of India", "Bajaj Finance",
    "Wipro", "Asian Paints", "Maruti Suzuki", "Sun Pharmaceutical",
    "Titan Company", "UltraTech Cement", "ONGC", "NTPC", "Tata Motors",
    "Tata Steel", "Adani Enterprises", "Adani Ports", "Bajaj Auto",
    "Cipla", "Dr. Reddy's Labs", "Hindustan Unilever",
    "Mahindra & Mahindra", "Eicher Motors", "Hero MotoCorp",
]

NAME_TO_SYM: Dict[str, str] = {
    "Reliance Industries":  "RELIANCE.NS",
    "HDFC Bank":            "HDFCBANK.NS",
    "ICICI Bank":           "ICICIBANK.NS",
    "Infosys":              "INFY.NS",
    "TCS":                  "TCS.NS",
    "Bharti Airtel":        "BHARTIARTL.NS",
    "ITC":                  "ITC.NS",
    "Kotak Mahindra Bank":  "KOTAKBANK.NS",
    "Larsen & Toubro":      "LT.NS",
    "HCL Technologies":     "HCLTECH.NS",
    "Axis Bank":            "AXISBANK.NS",
    "State Bank of India":  "SBIN.NS",
    "Bajaj Finance":        "BAJFINANCE.NS",
    "Wipro":                "WIPRO.NS",
    "Asian Paints":         "ASIANPAINT.NS",
    "Maruti Suzuki":        "MARUTI.NS",
    "Sun Pharmaceutical":   "SUNPHARMA.NS",
    "Titan Company":        "TITAN.NS",
    "UltraTech Cement":     "ULTRACEMCO.NS",
    "ONGC":                 "ONGC.NS",
    "NTPC":                 "NTPC.NS",
    "Tata Motors":          "TATAMOTORS.NS",
    "Tata Steel":           "TATASTEEL.NS",
    "Adani Enterprises":    "ADANIENT.NS",
    "Adani Ports":          "ADANIPORTS.NS",
    "Bajaj Auto":           "BAJAJAUTO.NS",
    "Cipla":                "CIPLA.NS",
    "Dr. Reddy's Labs":     "DRREDDY.NS",
    "Hindustan Unilever":   "HINDUNILVR.NS",
    "Mahindra & Mahindra":  "M&M.NS",
    "Eicher Motors":        "EICHERMOT.NS",
    "Hero MotoCorp":        "HEROMOTOCO.NS",
}

# ================================================================== helpers

def safe_float(val, default: float = 0.0) -> float:
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default


@st.cache_data(ttl=60)
def get_live_price(sym: str) -> Optional[float]:
    try:
        h = yf.Ticker(sym).history(period="1d", interval="1m")
        if h is not None and not h.empty:
            return safe_float(h["Close"].iloc[-1])
    except Exception:
        pass
    return None


def get_live_prices_bulk(symbols: List[str]) -> Dict[str, float]:
    """Fetch latest prices for multiple symbols at once."""
    prices: Dict[str, float] = {}
    for sym in symbols:
        p = get_live_price(sym)
        if p:
            prices[sym] = p
    return prices


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ================================================================== session state init

def init_state() -> None:
    if "pt_capital" not in st.session_state:
        st.session_state["pt_capital"]  = DEFAULT_CAPITAL   # available cash
    if "pt_holdings" not in st.session_state:
        # {sym: {"name": str, "qty": int, "avg_price": float}}
        st.session_state["pt_holdings"] = {}
    if "pt_trades" not in st.session_state:
        # list of trade dicts
        st.session_state["pt_trades"]   = []
    if "pt_initial" not in st.session_state:
        st.session_state["pt_initial"]  = DEFAULT_CAPITAL
    if "pt_equity_curve" not in st.session_state:
        # list of {ts, portfolio_value}
        st.session_state["pt_equity_curve"] = [
            {"ts": ts(), "value": DEFAULT_CAPITAL}
        ]


init_state()


# ================================================================== trade engine

def place_order(
    action: str,        # "BUY" or "SELL"
    sym: str,
    name: str,
    qty: int,
    price: float,
) -> str:
    """
    Execute a paper trade. Returns a status message string.
    Updates session_state: pt_capital, pt_holdings, pt_trades, pt_equity_curve.
    """
    cost    = qty * price
    capital = st.session_state["pt_capital"]
    holdings = st.session_state["pt_holdings"]

    if action == "BUY":
        if cost > capital:
            return f"❌ Insufficient cash. Need ₹{cost:,.2f}, available ₹{capital:,.2f}"
        # Update holdings (average-price method)
        if sym in holdings:
            old_qty   = holdings[sym]["qty"]
            old_avg   = holdings[sym]["avg_price"]
            new_qty   = old_qty + qty
            new_avg   = (old_qty * old_avg + qty * price) / new_qty
            holdings[sym]["qty"]       = new_qty
            holdings[sym]["avg_price"] = new_avg
        else:
            holdings[sym] = {"name": name, "qty": qty, "avg_price": price}
        st.session_state["pt_capital"] -= cost
        msg = f"✅ BUY {qty} × {name} @ ₹{price:,.2f}  |  Cost: ₹{cost:,.2f}"

    else:  # SELL
        if sym not in holdings or holdings[sym]["qty"] < qty:
            held = holdings.get(sym, {}).get("qty", 0)
            return f"❌ Cannot sell {qty} shares. You hold only {held}."
        avg_price  = holdings[sym]["avg_price"]
        realised   = (price - avg_price) * qty
        holdings[sym]["qty"] -= qty
        if holdings[sym]["qty"] == 0:
            del holdings[sym]
        st.session_state["pt_capital"] += qty * price
        pnl_icon = "🟢" if realised >= 0 else "🔴"
        msg = (
            f"{pnl_icon} SELL {qty} × {name} @ ₹{price:,.2f}  |  "
            f"Realised P&L: ₹{realised:+,.2f}"
        )

    # Log trade
    trade: Dict = {
        "timestamp":  ts(),
        "action":     action,
        "symbol":     sym,
        "name":       name,
        "qty":        qty,
        "price":      round(price, 2),
        "value":      round(cost if action == "BUY" else qty * price, 2),
        "realised_pnl": round((price - holdings.get(sym, {}).get("avg_price", price)) * qty
                               if action == "SELL" else 0.0, 2)
                        if action == "SELL" else 0.0,
    }
    # Re-compute realised_pnl correctly for SELL (holdings entry may be deleted above)
    if action == "SELL":
        trade["realised_pnl"] = round((price - avg_price) * qty, 2)

    st.session_state["pt_trades"].append(trade)

    # Snapshot equity curve
    _snapshot_equity()
    return msg


def _snapshot_equity() -> None:
    """Append current portfolio value to equity curve."""
    holdings = st.session_state["pt_holdings"]
    cash     = st.session_state["pt_capital"]
    mkt_val  = sum(
        h["qty"] * safe_float(get_live_price(sym) or h["avg_price"])
        for sym, h in holdings.items()
    )
    st.session_state["pt_equity_curve"].append(
        {"ts": ts(), "value": round(cash + mkt_val, 2)}
    )


def portfolio_summary(live_prices: Dict[str, float]) -> pd.DataFrame:
    """Build a DataFrame of current holdings with live P&L."""
    rows = []
    for sym, h in st.session_state["pt_holdings"].items():
        lp        = live_prices.get(sym, h["avg_price"])
        unreal    = (lp - h["avg_price"]) * h["qty"]
        mkt_val   = lp * h["qty"]
        pct       = (lp - h["avg_price"]) / h["avg_price"] * 100
        rows.append({
            "Stock":         h["name"],
            "Symbol":        sym,
            "Qty":           h["qty"],
            "Avg Price (₹)": round(h["avg_price"], 2),
            "LTP (₹)":       round(lp, 2),
            "Mkt Value (₹)": round(mkt_val, 2),
            "Unreal P&L (₹)": round(unreal, 2),
            "P&L %":         round(pct, 2),
        })
    return pd.DataFrame(rows)


def risk_metrics() -> Dict:
    trades = st.session_state["pt_trades"]
    sells  = [t for t in trades if t["action"] == "SELL"]
    if not sells:
        return {}
    pnls      = [t["realised_pnl"] for t in sells]
    wins      = [p for p in pnls if p > 0]
    losses    = [p for p in pnls if p <= 0]
    win_rate  = len(wins) / len(pnls) * 100 if pnls else 0.0
    avg_win   = np.mean(wins)   if wins   else 0.0
    avg_loss  = np.mean(losses) if losses else 0.0
    expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)
    # Max drawdown from equity curve
    curve  = [e["value"] for e in st.session_state["pt_equity_curve"]]
    if len(curve) > 1:
        arr    = np.array(curve)
        peaks  = np.maximum.accumulate(arr)
        dd     = (arr - peaks) / peaks * 100
        max_dd = float(np.min(dd))
    else:
        max_dd = 0.0
    total_return = (
        (st.session_state["pt_equity_curve"][-1]["value"] -
         st.session_state["pt_initial"]) /
        st.session_state["pt_initial"] * 100
    )
    return {
        "Total Trades":  len(sells),
        "Win Rate":      round(win_rate, 1),
        "Avg Win (₹)":   round(avg_win, 2),
        "Avg Loss (₹)":  round(avg_loss, 2),
        "Expectancy (₹)": round(expectancy, 2),
        "Max Drawdown": round(max_dd, 2),
        "Total Return %": round(total_return, 2),
    }


# ================================================================== EXPORT / IMPORT

def export_portfolio() -> str:
    return json.dumps({
        "capital":      st.session_state["pt_capital"],
        "initial":      st.session_state["pt_initial"],
        "holdings":     st.session_state["pt_holdings"],
        "trades":       st.session_state["pt_trades"],
        "equity_curve": st.session_state["pt_equity_curve"],
    }, indent=2)


def import_portfolio(json_str: str) -> str:
    try:
        data = json.loads(json_str)
        st.session_state["pt_capital"]      = float(data["capital"])
        st.session_state["pt_initial"]      = float(data["initial"])
        st.session_state["pt_holdings"]     = data["holdings"]
        st.session_state["pt_trades"]       = data["trades"]
        st.session_state["pt_equity_curve"] = data["equity_curve"]
        return "✅ Portfolio imported successfully!"
    except Exception as e:
        return f"❌ Import failed: {e}"


# ================================================================== PAGE UI

st.title("📝 Paper Trading Simulator")
st.markdown("""
> 🟡 **Simulated trading only — zero real money involved.**
> Practice buying and selling Nifty-50 stocks with virtual capital.
> Live prices are fetched from Yahoo Finance for realistic simulation.
""")

# Top-level metrics bar
cash = st.session_state["pt_capital"]
holdings_map = st.session_state["pt_holdings"]
live_syms = list(holdings_map.keys())
live_prices = get_live_prices_bulk(live_syms) if live_syms else {}

mkt_value   = sum(
    h["qty"] * live_prices.get(sym, h["avg_price"])
    for sym, h in holdings_map.items()
)
total_value  = cash + mkt_value
initial      = st.session_state["pt_initial"]
unreal_total = mkt_value - sum(
    h["qty"] * h["avg_price"] for h in holdings_map.values()
)
total_pnl    = total_value - initial
pnl_pct      = total_pnl / initial * 100

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("💰 Cash Balance",      f"₹{cash:,.0f}")
m2.metric("📈 Holdings Value",   f"₹{mkt_value:,.0f}")
m3.metric("🏆 Portfolio Value",  f"₹{total_value:,.0f}")
m4.metric("📉 Unrealised P&L",   f"₹{unreal_total:+,.0f}")
m5.metric("📊 Total Return",
          f"₹{total_pnl:+,.0f}",
          delta=f"{pnl_pct:+.2f}%")

st.markdown("---")

# ------------------------------------------------------------------ TABS
tab_order, tab_holdings, tab_log, tab_metrics, tab_chart, tab_io = st.tabs([
    "🛒 Place Order",
    "💼 Holdings",
    "📃 Trade Log",
    "📊 Risk Metrics",
    "📈 Equity Curve",
    "📥 Export / Import",
])


# ------------------------------------------------------------------
# TAB 1 — Place Order
# ------------------------------------------------------------------
with tab_order:
    st.subheader("🛒 Place a Paper Trade")
    st.caption("Live price is fetched automatically. You can override it for limit-order simulation.")

    oc1, oc2, oc3 = st.columns(3)
    with oc1:
        order_name = st.selectbox("🏢 Stock", NIFTY50_NAMES, key="order_stock")
    with oc2:
        order_action = st.radio("🔄 Action", ["BUY", "SELL"],
                                horizontal=True, key="order_action")
    with oc3:
        order_qty = st.number_input("🔢 Quantity", min_value=1,
                                    max_value=10000, value=10, step=1,
                                    key="order_qty")

    order_sym = NAME_TO_SYM.get(order_name, "RELIANCE.NS")

    # Fetch live price
    with st.spinner("Fetching live price…"):
        live_px = get_live_price(order_sym)

    if live_px:
        st.info(f"📌 **Live Price ({order_name}):** ₹{live_px:,.2f}")
    else:
        st.warning("⚠️ Could not fetch live price. Enter price manually below.")
        live_px = 0.0

    override_px = st.number_input(
        "₹ Order Price (editable — use live price or set your limit price)",
        min_value=0.01,
        value=float(round(live_px, 2)) if live_px else 100.0,
        step=0.5,
        format="%.2f",
        key="order_price",
    )

    order_value = override_px * order_qty
    st.markdown(
        f"**Order Value:** ₹{order_value:,.2f} &nbsp;|&nbsp; "
        f"**Available Cash:** ₹{cash:,.2f} &nbsp;|&nbsp; "
        f"**After Trade:** ₹{cash - order_value:,.2f}"
        if order_action == "BUY" else
        f"**Order Value:** ₹{order_value:,.2f}"
    )

    # Holding info for SELL
    if order_action == "SELL" and order_sym in holdings_map:
        h = holdings_map[order_sym]
        est_pnl = (override_px - h["avg_price"]) * order_qty
        st.markdown(
            f"📌 Holding: **{h['qty']} shares** @ avg ₹{h['avg_price']:,.2f} &nbsp;|"
            f" Est. P&L for this trade: **₹{est_pnl:+,.2f}**"
        )

    confirm = st.checkbox("✅ I confirm this is a PAPER trade — no real money")
    if st.button("🚀 Execute Order", disabled=not confirm, type="primary"):
        result = place_order(
            order_action, order_sym, order_name,
            int(order_qty), float(override_px)
        )
        if result.startswith("✅") or result.startswith("🟢") or result.startswith("🔴"):
            st.success(result)
        else:
            st.error(result)
        st.rerun()


# ------------------------------------------------------------------
# TAB 2 — Holdings
# ------------------------------------------------------------------
with tab_holdings:
    st.subheader("💼 Current Holdings")
    if not holdings_map:
        st.info("ℹ️ No open positions. Place a BUY order to start.")
    else:
        port_df = portfolio_summary(live_prices)
        # Colour unrealised P&L
        def colour_pnl(val):
            color = "#00c853" if val > 0 else ("#ff1744" if val < 0 else "#ffd600")
            return f"color: {color}"

        styled = port_df.style.applymap(
            colour_pnl,
            subset=["Unreal P&L (₹)", "P&L %"]
        ).format({
            "Avg Price (₹)": "₹{:,.2f}",
            "LTP (₹)":       "₹{:,.2f}",
            "Mkt Value (₹)": "₹{:,.2f}",
            "Unreal P&L (₹)": "₹{:+,.2f}",
            "P&L %":          "{:+.2f}%",
        })
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # Holdings pie chart
        fig_pie = px.pie(
            port_df, names="Stock", values="Mkt Value (₹)",
            title="Portfolio Allocation",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig_pie.update_layout(template="plotly_dark", height=380)
        st.plotly_chart(fig_pie, use_container_width=True)


# ------------------------------------------------------------------
# TAB 3 — Trade Log
# ------------------------------------------------------------------
with tab_log:
    st.subheader("📃 Trade History")
    trades = st.session_state["pt_trades"]
    if not trades:
        st.info("ℹ️ No trades yet.")
    else:
        tdf = pd.DataFrame(trades)
        # Format display
        display_cols = [
            "timestamp", "action", "name", "qty",
            "price", "value", "realised_pnl"
        ]
        present = [c for c in display_cols if c in tdf.columns]
        tdf_disp = tdf[present].copy()
        tdf_disp.rename(columns={
            "timestamp":    "Time",
            "action":       "Action",
            "name":         "Stock",
            "qty":          "Qty",
            "price":        "Price (₹)",
            "value":        "Value (₹)",
            "realised_pnl": "Realised P&L (₹)",
        }, inplace=True)
        st.dataframe(
            tdf_disp.sort_index(ascending=False)
            .reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

        # Cumulative realised P&L bar
        sell_trades = tdf[tdf["action"] == "SELL"].copy()
        if not sell_trades.empty:
            sell_trades["cum_pnl"] = sell_trades["realised_pnl"].cumsum()
            sell_trades["color"]   = sell_trades["realised_pnl"].apply(
                lambda x: "#00c853" if x >= 0 else "#ff1744")
            fig_bar = go.Figure(go.Bar(
                x=sell_trades["timestamp"],
                y=sell_trades["realised_pnl"],
                marker_color=sell_trades["color"],
                name="Realised P&L",
                text=sell_trades["realised_pnl"].apply(lambda x: f"₹{x:+,.0f}"),
                textposition="outside",
            ))
            fig_bar.update_layout(
                title="Realised P&L per Trade",
                template="plotly_dark", height=350,
                xaxis_title="Time", yaxis_title="P&L (₹)",
            )
            st.plotly_chart(fig_bar, use_container_width=True)


# ------------------------------------------------------------------
# TAB 4 — Risk Metrics
# ------------------------------------------------------------------
with tab_metrics:
    st.subheader("📊 Risk & Performance Metrics")
    metrics = risk_metrics()
    if not metrics:
        st.info("ℹ️ Complete at least one SELL trade to see metrics.")
    else:
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("📊 Total Closed Trades", metrics["Total Trades"])
        mc2.metric("🎯 Win Rate",            f"{metrics['Win Rate']}%")
        mc3.metric("🟢 Avg Win",             f"₹{metrics['Avg Win (₹)']:,.2f}")
        mc4.metric("🔴 Avg Loss",            f"₹{metrics['Avg Loss (₹)']:,.2f}")

        mc5, mc6, mc7, _ = st.columns(4)
        mc5.metric("🧠 Expectancy",        f"₹{metrics['Expectancy (₹)']:,.2f}")
        mc6.metric("📉 Max Drawdown",      f"{metrics['Max Drawdown']}%")
        mc7.metric("💰 Total Return",      f"{metrics['Total Return %']}%")

        # Explainer
        st.markdown("""
        | Metric | What it means |
        |--------|---------------|
        | **Win Rate** | % of closed trades that were profitable |
        | **Expectancy** | Average expected P&L per trade (positive = edge) |
        | **Max Drawdown** | Largest peak-to-trough drop in portfolio value |
        | **Total Return** | Overall gain/loss vs starting capital |
        """)


# ------------------------------------------------------------------
# TAB 5 — Equity Curve
# ------------------------------------------------------------------
with tab_chart:
    st.subheader("📈 Portfolio Equity Curve")
    eq_curve = st.session_state["pt_equity_curve"]
    if len(eq_curve) < 2:
        st.info("ℹ️ Place at least one trade to see the equity curve.")
    else:
        eq_df = pd.DataFrame(eq_curve)
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(
            x=eq_df["ts"], y=eq_df["value"],
            mode="lines+markers",
            name="Portfolio Value",
            line=dict(color="#00e5ff", width=2),
            fill="tozeroy",
            fillcolor="rgba(0,229,255,0.08)",
        ))
        fig_eq.add_hline(
            y=initial, line_dash="dash",
            line_color="#ffd600",
            annotation_text=f"Starting Capital ₹{initial:,.0f}",
        )
        fig_eq.update_layout(
            title="Portfolio Value Over Time",
            template="plotly_dark", height=420,
            xaxis_title="Time", yaxis_title="Portfolio Value (₹)",
        )
        st.plotly_chart(fig_eq, use_container_width=True)


# ------------------------------------------------------------------
# TAB 6 — Export / Import / Reset
# ------------------------------------------------------------------
with tab_io:
    st.subheader("📥 Save & Restore Portfolio")
    st.markdown(
        "Export your portfolio as JSON and paste it back later to restore "
        "your trades across sessions (e.g., after Streamlit restarts)."
    )

    # Export
    json_out = export_portfolio()
    st.download_button(
        label="⬇️ Download Portfolio JSON",
        data=json_out,
        file_name="paper_portfolio.json",
        mime="application/json",
    )
    with st.expander("📋 View raw JSON"):
        st.code(json_out, language="json")

    st.markdown("---")

    # Import
    st.subheader("📤 Restore Portfolio")
    uploaded = st.file_uploader(
        "Upload portfolio JSON", type=["json"], key="pt_upload")
    if uploaded is not None:
        raw = uploaded.read().decode("utf-8")
        msg = import_portfolio(raw)
        if msg.startswith("✅"):
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.markdown("---")

    # Reset
    st.subheader("⚠️ Reset Portfolio")
    reset_capital = st.number_input(
        "Starting capital for new portfolio (₹)",
        min_value=10_000.0,
        max_value=100_000_000.0,
        value=DEFAULT_CAPITAL,
        step=100_000.0,
        format="%.0f",
        key="reset_capital_input",
    )
    confirm_reset = st.checkbox(
        "✅ Yes, I want to reset and lose all trade history",
        key="confirm_reset"
    )
    if st.button("🗑️ Reset Portfolio", disabled=not confirm_reset, type="primary"):
        st.session_state["pt_capital"]      = float(reset_capital)
        st.session_state["pt_initial"]      = float(reset_capital)
        st.session_state["pt_holdings"]     = {}
        st.session_state["pt_trades"]       = []
        st.session_state["pt_equity_curve"] = [
            {"ts": ts(), "value": float(reset_capital)}
        ]
        st.success(f"✅ Portfolio reset with ₹{reset_capital:,.0f} starting capital.")
        st.rerun()
