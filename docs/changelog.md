# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/). Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Planned
- NSE holiday calendar integration
- LSTM price prediction tab
- Portfolio export (CSV/Excel)

---

## [1.2.0] — 2026-06-15

### Added
- Comprehensive pytest test suite: unit, integration, and Streamlit AppTest smoke tests (`tests/`)
- Full MkDocs documentation site with GitHub Pages deployment
- `CONTRIBUTING.md` with development setup, branching strategy, and PR guide
- `pytest.ini` with strict markers and short tracebacks
- `requirements-test.txt` for isolated test dependency management

---

## [1.1.0] — 2026-06-12

### Added
- **Time Machine** tab: travel to any historical NSE trading date
- Famous dates preset (COVID crash, Budget 2024, etc.)
- Beta-adjusted P&L impact simulation in the P&L Calculator
- Sector filter on All 50 Companies tab
- Auto-refresh every 5 seconds when market is live

### Fixed
- `safe_float()` now handles `pd.NA` and `None` gracefully
- Removed duplicate API calls in Gainers & Losers tab

---

## [1.0.0] — 2026-06-12

### Added
- Initial release
- Market Overview, Nifty 50 Index, All 50 Companies, Gainers & Losers, P&L Calculator, Stock Chart tabs
- yfinance data pipeline with `@st.cache_data` caching
- Plotly charts: line, candlestick, area, percentage bar, trend comparison
- Streamlit Cloud deployment
