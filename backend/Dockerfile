FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg file \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --require-hashes -r requirements.txt \
    && useradd --uid 1000 --create-home app \
    && mkdir /app/media && chown 1000:1000 /app/media && chmod 755 /app/media
COPY backend/app backend/app
COPY backend/alembic.ini backend/alembic.ini
COPY backend/migrations backend/migrations
USER 1000:1000
CMD ["python", "-m", "app"]
