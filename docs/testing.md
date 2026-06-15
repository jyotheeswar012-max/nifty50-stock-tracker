---
title: Testing
---

# Testing

The test suite uses `pytest` and targets `utils/calculations.py` and `utils/charts.py` — the two modules with zero I/O dependencies.

---

## Running Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=utils --cov-report=term-missing

# Run a specific test file
pytest tests/test_calculations.py -v
```

---

## Test Structure

```
tests/
├── __init__.py
├── test_calculations.py   ← P&L, beta, price helpers, stock rows
├── test_charts.py         ← Chart builders return valid Figure objects
└── conftest.py            ← Shared fixtures (sample DataFrames)
```

---

## What Is Tested

### `test_calculations.py`

| Test | What it verifies |
|---|---|
| `test_safe_float_nan` | Returns default on NaN |
| `test_safe_float_inf` | Returns default on Infinity |
| `test_calc_pl_gain` | Positive P&L calculated correctly |
| `test_calc_pl_loss` | Negative P&L (loss) calculated correctly |
| `test_calc_pl_breakeven` | Zero P&L when buy == sell |
| `test_calc_beta_impact` | Stock move = nifty_pct × beta |
| `test_build_stock_rows_structure` | Returns DataFrame with required columns |
| `test_build_stock_rows_na_on_missing` | Missing symbols get "N/A" not exceptions |

### `test_charts.py`

| Test | What it verifies |
|---|---|
| `test_build_price_chart_line` | Returns `go.Figure` for Line type |
| `test_build_price_chart_candle` | Returns `go.Figure` for Candlestick type |
| `test_build_price_chart_empty_df` | Returns empty `go.Figure` on empty input |
| `test_build_pct_bar` | Returns `go.Figure` |
| `test_build_trend_chart_normalised` | First value of each series normalises to 100 |

---

## Mocking Network Calls

Since `calculations.py` accepts `fetch_intraday_fn` as a parameter, network calls are trivially mockable:

```python
def fake_intraday(symbol):
    """Returns a synthetic 1-minute bar DataFrame."""
    return pd.DataFrame(
        {"Open": [100.0], "High": [105.0], "Low": [99.0], "Close": [103.5], "Volume": [5000]},
        index=pd.to_datetime(["2026-06-15 09:15:00"])
    )

def test_get_last_price_market_open(sample_5d_data):
    curr, prev = get_last_price("RELIANCE.NS", sample_5d_data, True, fake_intraday)
    assert curr == 103.5
    assert prev is not None
```

---

## CI — GitHub Actions

Tests run automatically on every push and pull request via `.github/workflows/tests.yml`:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt -r requirements-test.txt
      - run: pytest --tb=short
```
