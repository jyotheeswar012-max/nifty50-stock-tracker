---
title: Installation
---

# Installation

## Prerequisites

| Requirement | Minimum Version | Notes |
|---|---|---|
| Python | 3.10 | 3.11+ recommended |
| pip | 23.0 | `pip install --upgrade pip` |
| Git | any | For cloning the repo |

---

## 1. Clone the Repository

```bash
git clone https://github.com/jyotheeswar012-max/nifty50-stock-tracker.git
cd nifty50-stock-tracker
```

---

## 2. Create a Virtual Environment

=== "macOS / Linux"

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

=== "Windows (PowerShell)"

    ```powershell
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    ```

=== "conda"

    ```bash
    conda create -n nse-tracker python=3.11 -y
    conda activate nse-tracker
    ```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

For running the test suite, also install:

```bash
pip install -r requirements-test.txt
```

### Core Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web UI framework |
| `yfinance` | Primary market data source (Yahoo Finance) |
| `pandas` | DataFrame manipulation |
| `plotly` | Interactive charts |
| `pytz` | IST timezone handling |
| `streamlit-autorefresh` | Auto-refresh during market hours |

### Optional Dependencies

| Package | Purpose |
|---|---|
| `nselib` | NSE India fallback data source — install with `pip install nselib` |

!!! tip "nselib is optional"
    The app starts without `nselib` and uses Yahoo Finance exclusively. Install it only if you want the NSE India fallback when Yahoo Finance is unavailable.

---

## 4. Run Locally

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## 5. Deploy to Streamlit Cloud

1. Push your fork to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select your repo, branch `main`, and main file `app.py`
4. Click **Deploy**

Streamlit Cloud reads `requirements.txt` automatically — no extra configuration needed.

!!! note "Log files on Streamlit Cloud"
    Streamlit Cloud has an ephemeral filesystem. `logs/app.log` will be created each session but does not persist between cold starts. Use the **Live Logs** sidebar expander to read logs during the current session.

---

## 6. Build the Docs Site Locally

```bash
pip install mkdocs-material
mkdocs serve          # live preview at http://127.0.0.1:8000
mkdocs build          # builds static site into site/
```
