FROM python:3.10-slim

# Dépendances système pour psycopg2 (PostgreSQL)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Utilisateur non-root (bonne pratique)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Copie et install des dépendances d'abord (layer cache Docker)
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copie du code
COPY --chown=user . /app

# Expose le port Flask
EXPOSE 5000

# Lancement avec Gunicorn (production) au lieu de uvicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "main:app"]