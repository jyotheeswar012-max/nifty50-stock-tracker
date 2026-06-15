# Contributing to Nifty 50 Tracker

Please read the full [Contributing Guide](https://jyotheeswar012-max.github.io/nifty50-stock-tracker/contributing/) on the documentation site.

## Quick Start for Contributors

```bash
git clone https://github.com/YOUR-USERNAME/nifty50-stock-tracker.git
cd nifty50-stock-tracker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
pytest          # verify all tests pass
streamlit run app.py  # verify app runs
```

Create a branch, make your change, write tests, open a PR against `main`.

See the full guide for branching strategy, commit message format, and what to contribute.
