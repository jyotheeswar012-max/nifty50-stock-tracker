---
title: Changelog
---

# Changelog

All notable changes to the Nifty 50 Tracker are documented here.
This project follows [Semantic Versioning](https://semver.org/) and [Conventional Commits](https://www.conventionalcommits.org/).

---

## [Unreleased]

### Planned
- Live beta recalculation from 252-day rolling returns
- Portfolio tracker with optional Supabase backend
- NSE F&O (options/futures) data support
- Alert system — email/SMS when price crosses a threshold

---

## [1.4.0] — 2026-06-15

### Added
- **Structured logging** (`utils/logger.py`) — rotating file handler (5 MB × 3 backups), console handler, ISO-8601 timestamps, module name + line number in every record
- `read_recent_logs(n)` and `log_file_path()` exported from `utils/logger.py` for the sidebar Live Logs widget
- Sidebar **Live Logs expander** in `app.py` — real-time tail of `logs/app.log` with level filter and line count slider
- Sidebar **Data Source Status badge** — green/yellow/red health indicator for each source
- `LOG_LEVEL` environment variable + Streamlit secrets support for runtime verbosity control

### Changed
- All `print()` statements replaced with `log.info/warning/error()`
- All `except Exception: pass` blocks replaced with `log.error(..., exc_info=True)`
- `logs/*.log` added to `.gitignore`; `logs/.gitkeep` tracks the folder

---

## [1.3.0] — 2026-06-15

### Fixed
- **Price precision bug** — intraday price now uses 1-minute bars during market hours instead of daily close, eliminating the ₹0.50–₹1.50 discrepancy seen with Yahoo Finance's adjusted close

### Added
- Two-mode price strategy: `get_last_price()` with `fetch_intraday_fn` injection for testability
- `_ticker_intraday()` and `fetch_intraday()` helpers in `utils/data.py`

---

## [1.2.0] — 2026-06-14

### Added
- `utils/data.py` with multi-source fallback: yfinance → nselib → stale cache
- `get_source_status()` health probe
- Stale cache guard with visible `⚠️` warning in UI via `st.session_state["data_warnings"]`
- nselib column normalisation (comma-stripped numerics, `DD-MM-YYYY` date parsing)

### Changed
- All fetch logic moved out of `app.py` into `utils/data.py`

---

## [1.1.0] — 2026-06-13

### Added
- `utils/calculations.py` — pure calculation helpers extracted from `app.py`
- `utils/charts.py` — Plotly chart builders as pure functions
- `utils/constants.py` — centralised symbols, colours, cache TTL
- `tests/` directory with initial pytest suite
- `pytest.ini` configuration

### Changed
- `app.py` reduced to UI orchestration only — no calculations or chart logic

---

## [1.0.0] — 2026-06-13

### Added
- Initial release
- 7-tab Streamlit dashboard: Market Overview, Nifty 50 Index, All 50 Companies, Gainers & Losers, P&L Calculator, Stock Chart, Time Machine
- Live prices via `yfinance` during market hours
- Beta-adjusted P&L impact calculator
- Time Machine — historical snapshots back to 2010
- MkDocs Material documentation scaffold
