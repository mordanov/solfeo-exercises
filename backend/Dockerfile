FROM eclipse-temurin:25-jdk@sha256:119a3d18f160a3e7655a66034d0f43beee31cd7b3b9142d57a5de29772011de6 AS audiveris
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends \
        git ca-certificates fonts-dejavu-core libgomp1 libfreetype6 fontconfig \
        tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
RUN git init /opt/audiveris-build \
    && cd /opt/audiveris-build \
    && git remote add origin https://github.com/Audiveris/audiveris.git \
    && git fetch --depth 1 origin 9e1e55cd2746037d059345881c53e6a6754bffbd \
    && git checkout --detach FETCH_HEAD \
    && ./gradlew --no-daemon --max-workers=2 :app:installDist \
    && mv app/build/install/app /opt/audiveris \
    && cp LICENSE /opt/audiveris/LICENSE \
    && cd /opt \
    && rm -rf /opt/audiveris-build /root/.gradle

FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg file \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --require-hashes -r requirements.txt \
    && useradd --uid 1000 --create-home app \
    && mkdir /app/media && chown 1000:1000 /app/media && chmod 755 /app/media
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-dejavu-core libgomp1 libfreetype6 fontconfig tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
COPY --from=audiveris /opt/java/openjdk /opt/java/openjdk
COPY --from=audiveris /opt/audiveris /opt/audiveris
COPY backend/app backend/app
COPY backend/alembic.ini backend/alembic.ini
COPY backend/migrations backend/migrations
COPY worker worker
USER 1000:1000
CMD ["python", "-m", "app"]
