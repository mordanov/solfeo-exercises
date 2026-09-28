FROM eclipse-temurin:25-jdk@sha256:119a3d18f160a3e7655a66034d0f43beee31cd7b3b9142d57a5de29772011de6

LABEL org.opencontainers.image.source="https://github.com/Audiveris/audiveris" \
      org.opencontainers.image.version="5.11.0" \
      org.opencontainers.image.revision="9e1e55cd2746037d059345881c53e6a6754bffbd"

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

ENV HOME=/tmp \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
WORKDIR /output
USER 1000:1000
ENTRYPOINT ["/opt/audiveris/bin/Audiveris"]
