# Testing

The project uses **pytest** with three test layers: unit, integration, and Streamlit smoke tests.

## Running Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=utils --cov-report=html
open htmlcov/index.html

# Run a specific layer
pytest tests/test_utils.py -v       # unit tests
pytest tests/test_pnl.py -v         # P&L tests
pytest tests/test_api.py -v         # integration (mocked API)
pytest tests/test_streamlit_app.py  # Streamlit smoke tests
```

## Test Suite Structure

| File | Type | Tests | What it covers |
|---|---|---|---|
| `tests/conftest.py` | Fixtures | — | Shared OHLCV data, holdings, mock yfinance ticker |
| `tests/test_utils.py` | Unit | 20 | `clean_ohlcv`, returns, Sharpe ratio, max drawdown, MAs |
| `tests/test_pnl.py` | Unit | 10 | `calc_pl`, portfolio summary, edge cases (zero shares) |
| `tests/test_api.py` | Integration | 13 | Mocked yfinance: return types, column names, period passthrough |
| `tests/test_streamlit_app.py` | Smoke | 10 | AppTest: no exceptions, charts, KPIs, sidebar, error-free load |

## Key Fixtures (`conftest.py`)

```python
@pytest.fixture
def raw_price_data():
    """30-day synthetic OHLCV DataFrame."""

@pytest.fixture
def cleaned_price_data(raw_price_data):
    """Same data with DatetimeIndex applied."""

@pytest.fixture
def holdings_data():
    """4-stock portfolio: RELIANCE, HDFCBANK, INFY, TCS."""

@pytest.fixture
def mock_yfinance_ticker(cleaned_price_data):
    """Mocked yfinance.Ticker — no real API calls."""
```

## CI with GitHub Actions

Tests run automatically on every push and pull request via `.github/workflows/` (see the repository). To trigger manually:

```bash
gh workflow run tests.yml
```

!!! tip "AppTest Requirement"
    The Streamlit smoke tests require `streamlit >= 1.31`. They are automatically skipped (`pytest.importorskip`) on older versions.
