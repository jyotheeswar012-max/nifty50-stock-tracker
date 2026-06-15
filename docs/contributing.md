---
title: Contributing
---

# Contributing Guide

Thank you for considering a contribution to the Nifty 50 Tracker. This guide covers everything from setting up your dev environment to getting your pull request merged.

---

## Code of Conduct

Be respectful. Constructive criticism only. All contributors are expected to follow the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

---

## Development Setup

### 1. Fork & Clone

```bash
# Fork on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/nifty50-stock-tracker.git
cd nifty50-stock-tracker

# Add upstream remote
git remote add upstream https://github.com/jyotheeswar012-max/nifty50-stock-tracker.git
```

### 2. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### 3. Verify Setup

```bash
streamlit run app.py               # app should open at localhost:8501
pytest                             # all tests should pass
```

---

## Branching Strategy

| Branch | Purpose |
|---|---|
| `main` | Production — always deployable |
| `feature/<name>` | New features (e.g. `feature/portfolio-tracker`) |
| `fix/<name>` | Bug fixes (e.g. `fix/intraday-price-precision`) |
| `docs/<name>` | Documentation only (e.g. `docs/api-reference`) |
| `chore/<name>` | Refactoring, dependency updates, CI changes |

```bash
# Always branch from an up-to-date main
git fetch upstream
git checkout -b feature/my-feature upstream/main
```

---

## Making Changes

### Adding a New Data Source

1. Add the fetch logic in `utils/data.py` as a private function `_newsource_history(symbol, period) -> pd.DataFrame`
2. Insert it into `_fetch_with_fallback()` after the existing sources
3. Update `get_source_status()` to probe the new source
4. Add a `log.info("New source used: ...")` call
5. Document it in `docs/methodology.md` under **Data Sourcing**

### Adding a New Tab

1. Add the tab label to the `st.tabs([...])` call in `app.py`
2. Write the tab body inside a `with tabs[N]:` block, wrapped in `try/except` with `log.error`
3. Keep all calculations in `utils/calculations.py`, all charts in `utils/charts.py`
4. Add the new functions to the API docs in `docs/api/`

### Updating Beta Values

Beta values live in `utils/constants.py` alongside each stock's metadata. Update the `"beta"` field for the relevant symbol and add a note in `docs/changelog.md`.

---

## Code Style

- **Python 3.10+** — use `match/case`, `X | Y` type unions, `from __future__ import annotations`
- **Type hints** on all public function signatures
- **Docstrings** for every public function (one-line summary + Args/Returns if non-obvious)
- **No bare `except:`** — always catch specific exceptions or at minimum `Exception as exc` and log it
- **No `print()`** — use `log = get_logger(__name__)` and `log.info/warning/error()`
- Line length: 100 characters

---

## Running Tests

```bash
pytest                              # run all tests
pytest -v                           # verbose output
pytest --cov=utils --cov-report=html  # coverage report in htmlcov/
pytest -k "test_calc"               # run only tests matching pattern
```

All tests must pass before opening a pull request. New features require new tests.

---

## Opening a Pull Request

1. **Commit messages** follow [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat: add portfolio tracker tab
   fix: intraday price discrepancy on market close
   docs: add API reference for fetch_ticker
   chore: bump yfinance to 0.2.54
   ```

2. **Push your branch** and open a PR against `main`

3. **PR description** must include:
   - What the change does
   - How to test it
   - Screenshots if UI changes are involved

4. **CI must be green** — tests and linting run automatically

5. A maintainer will review within a few days. Please respond to review comments promptly.

---

## What We're Looking For

!!! success "Good contributions"
    - Bug fixes with a failing test that now passes
    - New NSE index symbols added to `constants.py`
    - Performance improvements to the data pipeline
    - Documentation improvements
    - Additional test coverage

!!! warning "Discuss before building"
    - ML price prediction features (see [Methodology — What This App Deliberately Does Not Do](methodology.md#what-this-app-deliberately-does-not-do))
    - New heavy dependencies (plotly, pandas alternatives)
    - Major UI restructuring

    Open an issue first to discuss these — they require maintainer sign-off before work begins.
