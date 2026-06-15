# Contributing Guide

Thank you for considering a contribution! This guide explains how to set up a development environment, run tests, and submit a pull request.

---

## Code of Conduct

Be respectful, constructive, and inclusive. Disagreements about code are fine; personal attacks are not.

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork via GitHub UI, then:
git clone https://github.com/YOUR-USERNAME/nifty50-stock-tracker.git
cd nifty50-stock-tracker
```

### 2. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3. Install All Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
pip install mkdocs-material  # only needed if editing docs
```

### 4. Verify Setup

```bash
pytest          # all tests should pass
streamlit run app.py  # app should open at localhost:8501
```

---

## Branching Strategy

```
main          ← stable, always deployable
  └── feature/your-feature-name   ← your work
  └── fix/bug-description
  └── docs/what-you-documented
```

Create your branch from `main`:

```bash
git checkout -b feature/add-nse-holiday-calendar
```

---

## Making Changes

### Adding a New Feature

1. Write your code in the relevant `utils/` module
2. Add or update docstrings
3. Write tests in `tests/` (unit + integration as appropriate)
4. Run `pytest` and ensure all tests pass
5. Run `streamlit run app.py` and verify the UI manually

### Changing a Data Function

All data logic lives in `utils/data.py`. The function must:

- Accept primitive types (no Streamlit state inside)
- Return a clean `pd.DataFrame` or primitive
- Handle failures gracefully (return empty DataFrame, not raise)
- Be compatible with `@st.cache_data`

### Updating Documentation

Docs live in `docs/`. To preview:

```bash
mkdocs serve
```

Edit Markdown files under `docs/`, then preview at `localhost:8000`.

---

## Running Tests

```bash
pytest                      # full suite
pytest tests/test_utils.py  # one file
pytest -k "TestCalcPnL"     # one class
pytest --cov=utils --cov-report=term-missing  # with coverage
```

**All tests must pass before opening a PR.**

---

## Submitting a Pull Request

1. Commit your changes with a clear message:

    ```bash
    git add .
    git commit -m "feat: add NSE holiday calendar to market state detection"
    ```

2. Push to your fork:

    ```bash
    git push origin feature/add-nse-holiday-calendar
    ```

3. Open a PR on GitHub against the `main` branch.

4. Fill in the PR template:
   - **What** does this change?
   - **Why** is it needed?
   - **How** was it tested?

5. A maintainer will review within a few days.

---

## Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add RSI indicator to stock chart
fix: handle empty DataFrame in fetch_intraday
docs: clarify beta formula in methodology
test: add edge case for zero-share portfolio
refactor: simplify build_stock_rows loop
```

---

## What to Contribute

Here are some areas where contributions are especially welcome:

- [ ] NSE holiday calendar for accurate market-state detection
- [ ] Export portfolio P&L to CSV/Excel
- [ ] Dark mode toggle in the Streamlit app
- [ ] Additional NSE indices (Nifty Midcap 100, Nifty FMCG, etc.)
- [ ] LSTM price prediction feature (see [Methodology](methodology.md))
- [ ] Improve Time Machine performance with async fetching
- [ ] Add more edge-case tests for `build_stock_rows`
