# Contributing

Full contributing guide lives in the [docs site](https://jyotheeswar012-max.github.io/nifty50-stock-tracker/contributing/).

## Quick Start

```bash
git clone https://github.com/jyotheeswar012-max/nifty50-stock-tracker.git
cd nifty50-stock-tracker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
streamlit run app.py   # verify app works
pytest                 # verify tests pass
```

## Branching

- `feature/<name>` for new features
- `fix/<name>` for bug fixes
- `docs/<name>` for documentation only

See the full guide for code style, commit message conventions, and PR requirements.
