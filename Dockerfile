# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Nifty 50 Stock Tracker  —  Production Docker image
# ---------------------------------------------------------------------------
# Build:  docker build -t nifty50-tracker .
# Run:    docker run -p 8501:8501 -v nifty50-data:/app/data nifty50-tracker
# ---------------------------------------------------------------------------

# ---- Stage 1: dependency builder ----------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps needed to compile some wheels (e.g. cryptography, lxml)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip wheel \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# ---- Stage 2: slim runtime image ----------------------------------------
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="Nifty 50 Stock Tracker"
LABEL org.opencontainers.image.description="Streamlit dashboard for Nifty 50 analysis"
LABEL org.opencontainers.image.source="https://github.com/jyotheeswar012-max/nifty50-stock-tracker"

# Runtime system deps only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Install pre-built wheels from builder stage
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

# Copy application source
COPY . .

# SQLite data volume — persists the price cache, model cache, watchlists
VOLUME ["/app/data"]

# Streamlit config (headless, no telemetry)
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Drop to non-root user
USER appuser

EXPOSE 8501

# Health-check: hits Streamlit's built-in health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

ENTRYPOINT ["streamlit", "run", "app.py", \
             "--server.port=8501", \
             "--server.address=0.0.0.0"]
