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

# ⚠️ CHANGEMENT 1 : Exposer le port 7860 (port par défaut HF)
EXPOSE 7860

# ⚠️ CHANGEMENT 2 : Health check adapté au port 7860
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request, os; port = os.environ.get('PORT', '7860'); urllib.request.urlopen(f'http://localhost:{port}/health')" || exit 1

# ⚠️ CHANGEMENT 3 : PORT par défaut = 7860
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WORKERS=2 \
    PORT=7860

# Start with Gunicorn + Uvicorn workers for production
# ⚠️ CHANGEMENT 4 : timeout augmenté pour HF
CMD ["sh", "-c", "python -m gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers ${WORKERS} \
  --bind 0.0.0.0:${PORT} \
  --timeout 120 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile -"]