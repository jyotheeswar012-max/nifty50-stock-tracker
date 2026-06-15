# Installation

## Prerequisites

- Python **3.10** or higher
- `pip` (comes with Python)
- Git

## 1. Clone the Repository

```bash
git clone https://github.com/jyotheeswar012-max/nifty50-stock-tracker.git
cd nifty50-stock-tracker
```

## 2. Create a Virtual Environment

=== "macOS / Linux"

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

=== "Windows"

    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    ```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

For development (tests + docs):

```bash
pip install -r requirements.txt -r requirements-test.txt
pip install mkdocs-material
```

## 4. Run the App

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## 5. (Optional) Run the Docs Site Locally

```bash
mkdocs serve
```

Docs open at `http://localhost:8000`.

---

## Troubleshooting

!!! warning "`streamlit_autorefresh` not found"
    Auto-refresh is optional. The app works without it. Install with:
    ```bash
    pip install streamlit-autorefresh
    ```

!!! warning "yfinance rate limiting"
    If you see HTTP 429 errors, yfinance is being rate-limited by Yahoo Finance. Wait 1–2 minutes and try again. The app uses Streamlit's `@st.cache_data` to minimize API calls.
