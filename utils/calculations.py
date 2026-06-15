"""Pure calculation helpers — no Streamlit, no yfinance, no I/O.

Every function here is stateless: given inputs, return outputs.
This makes them trivially unit-testable.
"""
import numpy as np
import pandas as pd

from utils.constants import NIFTY50, SYMBOLS


# ---------------------------------------------------------------------------
# Numeric safety
# ---------------------------------------------------------------------------

def safe_float(val, default=0.0):
    """Convert val to float, returning default on NaN/Inf/error."""
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Price helpers
# ---------------------------------------------------------------------------

def get_last_price(symbol, stock_data_5d, market_open, fetch_intraday_fn):
    """Return (current_price, previous_close) at the highest available precision.

    During market hours  -> last 1-min intraday bar Close  (matches live feeds).
    After close/weekend  -> official daily close bar       (matches Google Finance).

    Parameters
    ----------
    symbol            : str  e.g. 'RELIANCE.NS'
    stock_data_5d     : dict  {symbol: DataFrame}  from fetch_all_stocks_5d()
    market_open       : bool  from is_nse_open()[0]
    fetch_intraday_fn : callable  fetch_intraday() from utils.data
    """
    try:
        daily = stock_data_5d.get(symbol)
        if daily is None or daily.empty or "Close" not in daily.columns:
            return None, None

        daily_close = daily["Close"].dropna()
        if len(daily_close) == 0:
            return None, None

        prev = safe_float(daily_close.iloc[-2]) if len(daily_close) >= 2 else None

        if market_open:
            intra = fetch_intraday_fn(symbol)
            if not intra.empty and "Close" in intra.columns:
                intra_close = intra["Close"].dropna()
                if len(intra_close) > 0:
                    curr      = safe_float(intra_close.iloc[-1])
                    prev_daily = safe_float(daily_close.iloc[-1]) if len(daily_close) >= 1 else prev
                    return curr, prev_daily

        # Fallback: daily bars
        curr = safe_float(daily_close.iloc[-1])
        return curr, prev

    except Exception:
        return None, None


def build_stock_rows(stock_data_5d, market_open, fetch_intraday_fn):
    """Build the DataFrame used in All-50, Gainers/Losers tabs.

    Returns a DataFrame with columns:
        Symbol, Company, Sector, Beta,
        Price (Rs.) | Last Close (Rs.),
        Change (Rs.), Change (%),
        _curr, _pct   (internal numerics for sorting/charting)
    """
    p_lbl = "Price (Rs.)" if market_open else "Last Close (Rs.)"
    rows  = []
    for s in NIFTY50:
        try:
            curr, prev = get_last_price(s["symbol"], stock_data_5d, market_open, fetch_intraday_fn)
            chg = (curr - prev) if (curr is not None and prev is not None) else None
            pct = (chg / prev * 100) if (chg is not None and prev and prev != 0) else None
            rows.append({
                "Symbol":       s["symbol"].replace(".NS", ""),
                "Company":      s["name"],
                "Sector":       s["sector"],
                "Beta":         s["beta"],
                p_lbl:          round(curr, 2) if curr is not None else "N/A",
                "Change (Rs.)": round(chg,  2) if chg  is not None else "N/A",
                "Change (%)":   round(pct,  2) if pct  is not None else "N/A",
                "_curr": curr, "_pct": pct,
            })
        except Exception:
            rows.append({
                "Symbol":       s["symbol"].replace(".NS", ""),
                "Company":      s["name"],
                "Sector":       s["sector"],
                "Beta":         s["beta"],
                p_lbl:          "N/A",
                "Change (Rs.)": "N/A",
                "Change (%)":   "N/A",
                "_curr": None, "_pct": None,
            })
    return pd.DataFrame(rows)


def safe_sort(df, col, ascending=True):
    """Sort DataFrame by col, pushing non-numeric values to the bottom."""
    try:
        num   = pd.to_numeric(df[col], errors="coerce").reset_index(drop=True)
        df2   = df.reset_index(drop=True)
        if num.isna().all():
            return df2
        order = num.argsort(kind="stable")
        if not ascending:
            nv    = int(num.notna().sum())
            order = list(order[:nv][::-1]) + list(order[nv:])
        return df2.iloc[list(order)].reset_index(drop=True)
    except Exception:
        return df


# ---------------------------------------------------------------------------
# P&L / Beta-impact calculations
# ---------------------------------------------------------------------------

def calc_pl(buy_price, sell_price, qty):
    """Return (pl, investment, return_pct)."""
    inv = buy_price * qty
    pl  = (sell_price - buy_price) * qty
    ret = (pl / inv * 100) if inv > 0 else 0.0
    return pl, inv, ret


def calc_beta_impact(nifty_pct, stock_price, qty, beta):
    """Return (stock_move_pct, price_change, new_price, old_value, new_value, pl)."""
    spct = nifty_pct * beta
    pchg = stock_price * (spct / 100)
    nsp  = stock_price + pchg
    return spct, pchg, nsp, stock_price * qty, nsp * qty, pchg * qty


# ---------------------------------------------------------------------------
# Time-Machine snapshot
# ---------------------------------------------------------------------------

def nearest_row(df, target, window=4):
    """Find the DataFrame row whose date index is nearest to target (±window days)."""
    for delta in range(window + 1):
        for sign in ([0] if delta == 0 else [1, -1]):
            cand = target + pd.Timedelta(days=delta * sign)
            mask = df.index.normalize() == cand.normalize()
            if mask.any():
                return df[mask].iloc[0]
    return None


def build_time_machine_snapshot(all_hist, target):
    """Return a DataFrame of OHLCV for all 50 stocks on the nearest trading day."""
    ts       = pd.Timestamp(target)
    meta_map = {s["symbol"]: s for s in NIFTY50}
    rows     = []
    for sym in SYMBOLS:
        try:
            if sym not in all_hist:
                continue
            row  = nearest_row(all_hist[sym], ts)
            if row is None:
                continue
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
        except Exception:
            pass
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("Symbol")
