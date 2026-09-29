FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg file \
    && rm -rf /var/lib/apt/lists \
    && mkdir -p /data \
    && chown 1000:1000 /data \
    && chmod 700 /data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
COPY bot.py .
USER 1000:1000
CMD ["python", "bot.py"]
