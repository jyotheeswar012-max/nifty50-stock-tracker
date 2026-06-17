"""
utils/ml_signals.py  –  Real ML signal engine v2

Models available:
  • Random Forest   (sklearn RandomForestClassifier)
  • Gradient Boost  (sklearn GradientBoostingClassifier)
  • Logistic Regression  (fast baseline)

Features: 30+ engineered technical indicators.
Validation: walk-forward TimeSeriesSplit (no look-ahead bias).
Output: calibrated probability, directional signal, 1-5 star strength.

Models are cached to disk with joblib so they are reused across
Streamlit reruns without retraining every time.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

_CACHE_DIR = Path(os.environ.get("DATA_DIR", "./data")) / "ml_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Feature engineering
# ─────────────────────────────────────────────────────────────────────────────
def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    return 100 - 100 / (1 + gain / loss.replace(0, np.nan))


def build_features(df: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
    """
    Builds a feature matrix from OHLCV data.

    Parameters
    ----------
    df      : DataFrame with columns Close (required), High, Low, Volume (optional)
    horizon : prediction horizon in days (default 1 = next-day direction)

    Returns
    -------
    DataFrame with features + 'target' column, NaN rows dropped.
    """
    c = df["Close"]
    feat = pd.DataFrame(index=df.index)

    # ── Momentum features ──
    for w in [1, 3, 5, 10, 20, 60]:
        feat[f"ret_{w}d"] = c.pct_change(w)
        feat[f"sma_ratio_{w}"] = c / c.rolling(w).mean() - 1

    # ── RSI multi-period ──
    for p in [7, 14, 21]:
        feat[f"rsi_{p}"] = _rsi(c, p)

    # ── Bollinger Band position ──
    for w in [10, 20]:
        mu = c.rolling(w).mean()
        sigma = c.rolling(w).std()
        feat[f"bb_pos_{w}"] = (c - mu) / (2 * sigma.replace(0, np.nan))

    # ── MACD ──
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    feat["macd"] = macd
    feat["macd_signal"] = macd - macd.ewm(span=9, adjust=False).mean()

    # ── Volatility ──
    for w in [5, 10, 20]:
        feat[f"vol_{w}d"] = c.pct_change().rolling(w).std()
    feat["vol_ratio"] = feat["vol_5d"] / feat["vol_20d"].replace(0, np.nan)

    # ── High/Low channel position ──
    if "High" in df.columns and "Low" in df.columns:
        for w in [5, 20]:
            h = df["High"].rolling(w).max()
            lo = df["Low"].rolling(w).min()
            feat[f"hl_pos_{w}"] = (c - lo) / (h - lo).replace(0, np.nan)

    # ── Volume features ──
    if "Volume" in df.columns:
        v = df["Volume"]
        feat["vol_sma_ratio_10"] = v / v.rolling(10).mean().replace(0, np.nan)
        feat["vol_sma_ratio_20"] = v / v.rolling(20).mean().replace(0, np.nan)
        feat["vol_change"] = v.pct_change()

    # ── Target: 1 if price rises by >= 0.1% over next `horizon` days ──
    feat["target"] = (c.shift(-horizon) > c * 1.001).astype(int)

    return feat.replace([np.inf, -np.inf], np.nan).dropna()


# ─────────────────────────────────────────────────────────────────────────────
# Model registry
# ─────────────────────────────────────────────────────────────────────────────
def _make_pipeline(model_type: str) -> Pipeline:
    if model_type == "rf":
        base = RandomForestClassifier(
            n_estimators=300, max_depth=6, min_samples_leaf=8,
            max_features="sqrt", random_state=42, n_jobs=-1,
        )
    elif model_type == "gb":
        base = GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.8, random_state=42,
        )
    else:  # lr
        base = LogisticRegression(C=0.1, max_iter=1000, random_state=42)

    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf", CalibratedClassifierCV(base, cv=3, method="isotonic")),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────────────────────────────────────
def train_model(
    df: pd.DataFrame,
    model_type: str = "rf",
    horizon: int = 1,
    force_retrain: bool = False,
) -> tuple[Pipeline, dict]:
    """
    Trains a classifier with walk-forward TimeSeriesSplit CV.

    Returns (fitted_pipeline, metrics_dict).
    Results are cached to disk keyed by a hash of the data + params.
    """
    feat_df = build_features(df, horizon=horizon)
    X = feat_df.drop(columns=["target"])
    y = feat_df["target"]

    # Cache key: hash of data shape + last date + params
    key = hashlib.md5(
        f"{len(df)}-{df.index[-1]}-{model_type}-{horizon}".encode()
    ).hexdigest()[:12]
    cache_path = _CACHE_DIR / f"{model_type}_{key}.joblib"

    if cache_path.exists() and not force_retrain:
        pipeline = joblib.load(cache_path)
        metrics = {"cached": True, "cache_key": key}
        return pipeline, metrics

    pipeline = _make_pipeline(model_type)
    tscv = TimeSeriesSplit(n_splits=5)
    cv_acc, cv_auc = [], []

    for train_idx, val_idx in tscv.split(X):
        pipeline.fit(X.iloc[train_idx], y.iloc[train_idx])
        preds = pipeline.predict(X.iloc[val_idx])
        proba = pipeline.predict_proba(X.iloc[val_idx])[:, 1]
        cv_acc.append(accuracy_score(y.iloc[val_idx], preds))
        try:
            cv_auc.append(roc_auc_score(y.iloc[val_idx], proba))
        except Exception:
            pass

    # Final fit on all data
    pipeline.fit(X, y)

    # Feature importance
    try:
        inner = pipeline.named_steps["clf"].calibrated_classifiers_[0].estimator
        fi = pd.DataFrame({
            "feature": X.columns,
            "importance": inner.feature_importances_,
        }).sort_values("importance", ascending=False)
    except AttributeError:
        fi = pd.DataFrame(columns=["feature", "importance"])

    metrics = {
        "cached": False,
        "cv_accuracy": round(float(np.mean(cv_acc)) * 100, 1),
        "cv_auc": round(float(np.mean(cv_auc)) * 100, 1) if cv_auc else None,
        "n_samples": len(X),
        "n_features": X.shape[1],
        "feature_importance": fi,
        "model_type": model_type,
        "horizon_days": horizon,
    }

    try:
        joblib.dump(pipeline, cache_path)
    except Exception:
        pass

    return pipeline, metrics


# ─────────────────────────────────────────────────────────────────────────────
# Inference
# ─────────────────────────────────────────────────────────────────────────────
def get_signal(
    pipeline: Pipeline,
    df: pd.DataFrame,
    horizon: int = 1,
) -> dict:
    """
    Returns a signal dict for the latest available data point.

    Returns
    -------
    {
        'direction'      : 'UP' | 'DOWN',
        'prob_up'        : float  (calibrated probability, 0–1),
        'confidence'     : float  (distance from 0.5, scaled to 0–1),
        'signal_strength': int    (1–5 stars),
        'label'          : str    (human-readable),
    }
    """
    feat_df = build_features(df, horizon=horizon).drop(columns=["target"])
    if feat_df.empty:
        return {
            "direction": "UNKNOWN", "prob_up": 0.5,
            "confidence": 0.0, "signal_strength": 0, "label": "Insufficient data",
        }

    latest = feat_df.iloc[[-1]]
    # Align features to what the pipeline saw during training
    try:
        latest = latest[pipeline.feature_names_in_]
    except AttributeError:
        pass

    prob_up = float(pipeline.predict_proba(latest)[0][1])
    direction = "UP" if prob_up >= 0.5 else "DOWN"
    confidence = abs(prob_up - 0.5) * 2          # 0 = neutral, 1 = max
    strength = max(1, min(5, int(np.ceil(confidence * 5))))

    labels = {
        1: "Very Weak", 2: "Weak", 3: "Moderate", 4: "Strong", 5: "Very Strong",
    }
    arrow = "▲" if direction == "UP" else "▼"
    label = f"{arrow} {direction} — {labels[strength]} ({prob_up:.0%})"

    return {
        "direction": direction,
        "prob_up": round(prob_up, 4),
        "confidence": round(confidence, 4),
        "signal_strength": strength,
        "label": label,
    }


def batch_signals(
    symbols: list[str],
    data_fn,                # callable(symbol) -> DataFrame
    model_type: str = "rf",
    horizon: int = 1,
) -> pd.DataFrame:
    """
    Trains one model per symbol and returns a summary DataFrame.
    Useful for scanning all Nifty 50 stocks at once.
    """
    rows = []
    for sym in symbols:
        try:
            df = data_fn(sym)
            if df is None or len(df) < 100:
                continue
            pipeline, metrics = train_model(df, model_type=model_type, horizon=horizon)
            sig = get_signal(pipeline, df, horizon=horizon)
            rows.append({
                "symbol": sym,
                "direction": sig["direction"],
                "prob_up": sig["prob_up"],
                "strength": sig["signal_strength"],
                "label": sig["label"],
                "cv_acc": metrics.get("cv_accuracy"),
            })
        except Exception:
            continue
    return pd.DataFrame(rows)
