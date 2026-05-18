# ─── Build stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Runtime stage ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="ChurnGuard API"
LABEL description="Customer Churn Prediction API with ML"
LABEL version="1.0.0"

# Security: run as non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/
COPY ml/ ./ml/
COPY templates/ ./templates/

# Create required directories with correct permissions
RUN mkdir -p /app/data /app/ml && \
    chown -R appuser:appuser /app

# Train model at build time
RUN python -c "\
import sys; \
sys.path.insert(0, '/app'); \
from ml.train_model import train; \
train() \
"

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WORKERS=2 \
    PORT=8000

# Start with Gunicorn + Uvicorn workers for production
CMD ["sh", "-c", "python -m gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers ${WORKERS} \
  --bind 0.0.0.0:${PORT} \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -"]
