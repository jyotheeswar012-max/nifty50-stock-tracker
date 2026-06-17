"""API/integration tests (all marked network -- skipped in CI)."""
import pytest


@pytest.mark.network
def test_yfinance_fetch_reliance():
    """Live fetch -- only runs when -m network is passed."""
    import yfinance as yf
    ticker = yf.Ticker("RELIANCE.NS")
    hist = ticker.history(period="1d")
    assert not hist.empty


@pytest.mark.network
def test_yfinance_fetch_tcs():
    import yfinance as yf
    ticker = yf.Ticker("TCS.NS")
    hist = ticker.history(period="1d")
    assert not hist.empty
