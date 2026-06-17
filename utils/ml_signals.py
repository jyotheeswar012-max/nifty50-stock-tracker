"""
utils/ml_signals.py  —  scikit-learn signal engine for Nifty 50 stocks.

Model
-----
Ensemble of RandomForestClassifier + RidgeClassifier (soft-voting via
probability calibration) trained on a 30-feature rolling-window feature
matrix derived purely from price/volume history.

Features (30 total)
-------------------
  price momentum : 5/10/20/60-day log returns
  volatility     : 5/10/20-day rolling std of log-returns
  volume trend   : 5/10/20-day volume z-score
  RSI            : 7, 14, 21-day
  MACD           : value, signal, histogram
  Bollinger      : %B (position within band), bandwidth
  ATR            : 14-day average true range normalised by price
  SMA ratios     : close/SMA10, close/SMA20, close/SMA50
  calendar       : day-of-week, month (as ints)

Label
-----
Binary: 1 if forward 5-day return > +0.5%, else 0.
Classes: 1 = BUY, 0 = HOLD/SELL

Model lifecycle
---------------
* Trained once per symbol per session; result pickled into SQLite blob
  (utils/db.model_cache_write/read) with a 24-hour TTL.
* On cache hit the model is deserialised directly, skipping re-training.
* Falls back gracefully: on any sklearn error returns an empty signal.

Public API
----------
  predict_signals(symbol, df)  -> SignalResult
  bulk_signals(symbols, hist)  -> dict[str, SignalResult]
"""
from __future__ import annotations

import io
import pickle
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from utils.logger import get_logger

log = get_logger(__name__)

# Lazy imports so the module is importable even if sklearn is absent
try:
    from sklearn.ensemble import RandomForestClassifier, VotingClassifier
    from sklearn.linear_model import RidgeClassifier
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import f1_score
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False
    log.warning("scikit-learn not available — ML signals disabled")


_MODEL_TTL_HOURS = 24
_FWD_DAYS        = 5      # forward return horizon for labelling
_FWD_THRESHOLD   = 0.005  # +0.5 % to call it a BUY
_MIN_TRAIN_ROWS  = 252    # 1 year minimum


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class SignalResult:
    symbol:        str
    signal:        str           # "BUY" | "HOLD" | "SELL"
    confidence:    float         # 0.0 – 1.0
    feature_imp:   pd.Series     # feature name -> importance (RF only)
    last_proba:    float         # P(BUY) for the latest bar
    trained_at:    Optional[datetime] = None
    f1_cv:         float = 0.0   # cross-validated F1 on training set
    error:         str = ""
    history:       pd.Series = field(default_factory=pd.Series)  # daily P(BUY)


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def _log_ret(s: pd.Series, n: int) -> pd.Series:
    return np.log(s / s.shift(n))


def _rolling_std(s: pd.Series, n: int) -> pd.Series:
    return _log_ret(s, 1).rolling(n).std()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
    loss  = (-delta).clip(lower=0).ewm(com=period - 1, adjust=False).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([
        h - l,
        (h - c.shift(1)).abs(),
        (l - c.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(com=n - 1, adjust=False).mean() / c


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return a feature matrix aligned to df.index."""
    c = df["Close"]
    v = df.get("Volume", pd.Series(1, index=df.index))

    feat: dict[str, pd.Series] = {}

    # Momentum
    for n in (5, 10, 20, 60):
        feat[f"ret_{n}d"] = _log_ret(c, n)

    # Volatility
    for n in (5, 10, 20):
        feat[f"vol_{n}d"] = _rolling_std(c, n)

    # Volume z-score
    for n in (5, 10, 20):
        vol_mean = v.rolling(n).mean()
        vol_std  = v.rolling(n).std().replace(0, np.nan)
        feat[f"volz_{n}d"] = (v - vol_mean) / vol_std

    # RSI
    for p in (7, 14, 21):
        feat[f"rsi_{p}"] = _rsi(c, p) / 100.0  # normalise 0-1

    # MACD
    macd_line   = _ema(c, 12) - _ema(c, 26)
    macd_signal = _ema(macd_line, 9)
    feat["macd"]      = macd_line / c
    feat["macd_sig"]  = macd_signal / c
    feat["macd_hist"] = (macd_line - macd_signal) / c

    # Bollinger %B and bandwidth
    sma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    upper = sma20 + 2 * std20
    lower = sma20 - 2 * std20
    bw    = (upper - lower) / sma20.replace(0, np.nan)
    pct_b = (c - lower) / (upper - lower).replace(0, np.nan)
    feat["bb_pctb"] = pct_b
    feat["bb_bw"]   = bw

    # ATR
    feat["atr_14"] = _atr(df, 14)

    # SMA ratios
    for n in (10, 20, 50):
        feat[f"sma_ratio_{n}"] = c / c.rolling(n).mean().replace(0, np.nan)

    # Calendar
    feat["dow"]   = pd.Series(df.index.dayofweek.astype(float),  index=df.index)
    feat["month"] = pd.Series(df.index.month.astype(float),       index=df.index)

    return pd.DataFrame(feat, index=df.index)


# ---------------------------------------------------------------------------
# Model cache helpers  (SQLite blob store)
# ---------------------------------------------------------------------------

def _cache_key(symbol: str) -> str:
    return f"ml_model:{symbol}"


def _save_model(symbol: str, bundle: dict) -> None:
    try:
        from utils.db import _db_conn
        blob = pickle.dumps(bundle)
        conn = _db_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ml_model_cache
            (key TEXT PRIMARY KEY, blob BLOB, ts REAL)
            """
        )
        conn.execute(
            "INSERT OR REPLACE INTO ml_model_cache (key, blob, ts) VALUES (?,?,?)",
            (_cache_key(symbol), blob, datetime.utcnow().timestamp()),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        log.warning("_save_model: could not persist model for %s: %s", symbol, exc)


def _load_model(symbol: str) -> dict | None:
    try:
        from utils.db import _db_conn
        conn = _db_conn()
        conn.execute(
            "CREATE TABLE IF NOT EXISTS ml_model_cache (key TEXT PRIMARY KEY, blob BLOB, ts REAL)"
        )
        row = conn.execute(
            "SELECT blob, ts FROM ml_model_cache WHERE key=?",
            (_cache_key(symbol),),
        ).fetchone()
        conn.close()
        if row is None:
            return None
        age_hours = (datetime.utcnow().timestamp() - row[1]) / 3600
        if age_hours > _MODEL_TTL_HOURS:
            log.debug("_load_model: cache expired for %s (%.1fh)", symbol, age_hours)
            return None
        return pickle.loads(row[0])  # noqa: S301
    except Exception as exc:
        log.warning("_load_model: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def _build_model():
    """Return an untrained sklearn Pipeline."""
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1,
    )
    ridge = CalibratedClassifierCV(
        RidgeClassifier(alpha=1.0),
        cv=3,
        method="sigmoid",
    )
    voter = VotingClassifier(
        estimators=[("rf", rf), ("ridge", ridge)],
        voting="soft",
        weights=[2, 1],
    )
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    voter),
    ])


def _train(df: pd.DataFrame) -> dict:
    """
    Build feature matrix, create labels, walk-forward CV, train final model.
    Returns a bundle dict {model, feature_names, f1_cv, trained_at}.
    """
    X = build_features(df)
    c = df["Close"]

    # Forward return label
    fwd_ret = c.shift(-_FWD_DAYS) / c - 1
    y       = (fwd_ret > _FWD_THRESHOLD).astype(int)

    # Drop rows with NaN in X or y
    valid   = X.notna().all(axis=1) & y.notna()
    X, y    = X[valid], y[valid]

    if len(X) < _MIN_TRAIN_ROWS:
        raise ValueError(
            f"Insufficient rows after feature engineering: {len(X)} (need {_MIN_TRAIN_ROWS})"
        )

    feature_names = X.columns.tolist()
    X_arr = X.values
    y_arr = y.values

    # Walk-forward CV for F1 estimate
    tscv  = TimeSeriesSplit(n_splits=5)
    f1s: list[float] = []
    for tr_idx, val_idx in tscv.split(X_arr):
        m = _build_model()
        m.fit(X_arr[tr_idx], y_arr[tr_idx])
        pred  = m.predict(X_arr[val_idx])
        f1s.append(f1_score(y_arr[val_idx], pred, zero_division=0))
    f1_cv = float(np.mean(f1s))

    # Final model on full data
    model = _build_model()
    model.fit(X_arr, y_arr)

    return {
        "model":         model,
        "feature_names": feature_names,
        "f1_cv":         f1_cv,
        "trained_at":    datetime.utcnow(),
    }


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

def predict_signals(symbol: str, df: pd.DataFrame) -> SignalResult:
    """
    Return a SignalResult for *symbol* given its OHLCV DataFrame.

    Uses a cached model when available; trains a fresh one otherwise.
    Safe to call from Streamlit — never raises, returns error SignalResult
    on any failure.
    """
    if not SKLEARN_OK:
        return SignalResult(
            symbol=symbol, signal="N/A", confidence=0.0,
            feature_imp=pd.Series(dtype=float), last_proba=0.0,
            error="scikit-learn not installed",
        )

    try:
        # Try cache first
        bundle = _load_model(symbol)
        if bundle is None:
            log.info("predict_signals: training new model for %s", symbol)
            bundle = _train(df)
            _save_model(symbol, bundle)
        else:
            log.debug("predict_signals: using cached model for %s", symbol)

        model         = bundle["model"]
        feature_names = bundle["feature_names"]
        f1_cv         = bundle["f1_cv"]
        trained_at    = bundle.get("trained_at")

        # Build features for the full history to get the signal time-series
        X_full = build_features(df)[feature_names].dropna()
        if X_full.empty:
            raise ValueError("Feature matrix is empty after dropna")

        probas  = model.predict_proba(X_full.values)[:, 1]  # P(BUY)
        history = pd.Series(probas, index=X_full.index)

        last_proba = float(probas[-1])
        if last_proba >= 0.55:
            signal, confidence = "BUY",  last_proba
        elif last_proba <= 0.45:
            signal, confidence = "SELL", 1 - last_proba
        else:
            signal, confidence = "HOLD", 1 - abs(last_proba - 0.5) * 2

        # Feature importance from the RF sub-estimator
        try:
            rf_step  = model.named_steps["clf"].estimators_[0]
            imp      = rf_step.feature_importances_
            feat_imp = pd.Series(imp, index=feature_names).sort_values(ascending=False)
        except Exception:
            feat_imp = pd.Series(dtype=float)

        return SignalResult(
            symbol=symbol,
            signal=signal,
            confidence=round(confidence, 4),
            feature_imp=feat_imp,
            last_proba=round(last_proba, 4),
            trained_at=trained_at,
            f1_cv=round(f1_cv, 4),
            history=history,
        )

    except Exception as exc:
        log.error("predict_signals: symbol=%s error=%s", symbol, exc, exc_info=True)
        return SignalResult(
            symbol=symbol, signal="N/A", confidence=0.0,
            feature_imp=pd.Series(dtype=float), last_proba=0.0,
            error=str(exc),
        )


def bulk_signals(
    symbols: list[str],
    history: dict[str, pd.DataFrame],
) -> dict[str, SignalResult]:
    """Run predict_signals for every symbol in *symbols*."""
    results: dict[str, SignalResult] = {}
    for sym in symbols:
        df = history.get(sym)
        if df is None or df.empty:
            log.warning("bulk_signals: no history for %s, skipping", sym)
            continue
        results[sym] = predict_signals(sym, df)
    return results
