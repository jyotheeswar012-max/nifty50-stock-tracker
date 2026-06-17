# ─────────────────────────────────────────────────────────────────────────────
# Nifty50 Stock Tracker  –  Multi-stage Docker build
# Stage 1 (builder): install all Python deps into a venv
# Stage 2 (runtime): copy only the venv + app source → minimal image
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: builder ──────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create an isolated venv so only it is copied to the final stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Nifty50 Stock Tracker" \
      org.opencontainers.image.description="Streamlit-based NSE/Nifty50 tracker with ML signals" \
      org.opencontainers.image.source="https://github.com/jyotheeswar012-max/nifty50-stock-tracker"

# Runtime OS libs only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser && useradd -r -g appuser appuser

# Copy the pre-built venv from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy application source
COPY --chown=appuser:appuser . .

# Data dir for watchlists + ML model cache (mount a volume here)
RUN mkdir -p /data && chown appuser:appuser /data

USER appuser

ENV DATA_DIR=/data \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ENABLE_STATIC_SERVING=true \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
             "--server.port=8501", \
             "--server.address=0.0.0.0", \
             "--server.fileWatcherType=none"]
