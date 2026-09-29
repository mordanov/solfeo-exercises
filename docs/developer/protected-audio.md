# Protected-audio risk prototype

This document explains the PHASE 0.5 file-delivery prototype, its measured results, and the remaining Safari checks.

Prerequisites:
- Install Docker Compose, Python 3.12, uv, ffmpeg, ffprobe, and curl.
- Start Docker.
- Obtain the local `examples/ejercicio_1.opus` sample.
- Read `docs/PRODUCT_BRIEF.md` and `docs/DECISIONS.md`.

## Scope

The disposable stand lives in `prototypes/files/`.
FastAPI checks authorization and returns `X-Accel-Redirect`.
nginx reads the protected file and handles byte ranges.
The backend has no media volume and never reads audio bytes.
Only nginx publishes a port, bound to `127.0.0.1`.

**Caution:** Basic authentication does not encrypt credentials.
Use only generated, disposable credentials on this localhost-only HTTP stand.
Do not expose it on a public or shared network.
Do not use a product username or password.

Basic authentication is a prototype assumption, not a new product decision.
It permits a native Safari login prompt without a product login page.
The product still requires server-side sessions and an httpOnly cookie.
This stand has no users, database, upload API, or product frontend.

The backend joins an internal Docker network.
nginx also joins a separate network for host port publication.
The nginx file location uses `internal` and accepts no client-selected file path.
The public endpoint maps to exactly 1 local file.

## Setup

1. Open the prototype directory.

   ```sh
   cd prototypes/files
   ```

2. Install the locked dependencies.

   ```sh
   uv sync --frozen
   ```

3. Create a private `.env` file with generated credentials.

   ```sh
   uv run --frozen python - <<'PY'
   import os
   import secrets
   from pathlib import Path

   content = Path(".env.example").read_text().replace(
       "GENERATE_A_RANDOM_LOCAL_TOKEN_BEFORE_USE", secrets.token_urlsafe(32)
   )
   fd = os.open(".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
   with os.fdopen(fd, "w") as stream:
       stream.write(content)
   PY
   ```

   The command refuses to overwrite an existing `.env`.
   The application rejects the placeholder credential.

4. Convert the local audio sample.

   ```sh
   uv run --frozen python prepare.py
   ```

   The command creates `media/sample.m4a` and `output/audio-metadata.json`.
   It retains the original sample and refuses to overwrite an existing conversion.
   ffmpeg produces AAC audio with fast start in an MP4 container.

5. Start the stand.

   ```sh
   docker-compose up --build -d --wait
   ```

6. Confirm that nginx responds.

   ```sh
   curl --fail --silent --show-error --retry 5 --retry-connrefused \
     --retry-delay 1 http://127.0.0.1:18085/api/health
   ```

   The response is `{"status":"ok"}`.
   Colima can need a short delay before its host port becomes available.

The measured environment uses standalone `docker-compose`.
Use `docker compose` instead when that plugin is available.
The application image uses a pinned Python base and hashed runtime dependencies.
The nginx image also uses a pinned digest.
The Docker build context excludes `.env`, media, tests, and captured responses.

### Configuration

`Settings` reads runtime configuration through `pydantic-settings`.
Docker Compose reads the same `.env` for host ports and bind mounts.
Paths are relative to `prototypes/files/`.

| Variable | Default | Purpose |
|---|---|---|
| `FILES_USERNAME` | `prototype` | Disposable local username. |
| `FILES_PASSWORD` | Required | Generated credential with at least 32 characters. |
| `FILES_PORT` | `18085` | Host port on `127.0.0.1`. |
| `FILES_MEDIA_DIR` | `media` | Directory for the converted audio. |
| `FILES_OUTPUT_DIR` | `output` | Local metadata and curl evidence. |
| `FILES_SOURCE_AUDIO` | `../../examples/ejercicio_1.opus` | Local conversion input. |
| `FILES_FFMPEG_TIMEOUT_SECONDS` | `60` | Timeout for ffmpeg and ffprobe. |
| `FILES_AUDIO_BITRATE` | `128k` | Target AAC bitrate. |

Only nginx mounts `sample.m4a`, read-only.
The backend receives only the prototype credentials.
Changing credentials requires recreating the backend container.

## Automated checks

1. Run the unit tests without Docker.

   ```sh
   uv run --frozen pytest -q -m "not integration"
   ```

2. Run all checks with the stand running.

   ```sh
   uv run --frozen pytest -q -s
   uv run --frozen ruff check app.py prepare.py tests
   uv run --frozen ruff format --check app.py prepare.py tests
   uv run --frozen mypy app.py prepare.py tests
   docker-compose exec -T nginx nginx -t
   ```

The integration tests execute curl against nginx, not a mocked HTTP server.
They compare downloaded bytes with the corresponding local file slices.
They also verify that HEAD responses download no body.
Each run creates an ignored `output/curl-<timestamp>-<identifier>/` directory.

Each case records response headers, response bytes, and a JSON result.
Credentials reach curl through standard input, not command arguments or saved evidence.
The application returns stable error codes; nginx returns its standard protocol errors.

To update runtime dependencies after an intentional manifest change:

1. Regenerate the lock.

   ```sh
   uv lock
   ```

2. Export the hashed runtime requirements.

   ```sh
   uv export --frozen --no-dev --no-emit-project \
     --format requirements-txt -o requirements.txt
   ```

3. Rebuild the stand.

   ```sh
   docker-compose up --build -d --wait
   ```

## Curl reproduction

The following commands use the default port and username.
Use the configured values if `.env` differs.
`curl --user prototype` prompts for the password without placing it in shell history.

1. Request the first 2 bytes.

   ```sh
   curl --user prototype --basic --silent --show-error \
     --dump-header output/manual-range.headers \
     --output output/manual-range.bin \
     --header 'Range: bytes=0-1' \
     http://127.0.0.1:18085/api/audio
   ```

   Relevant response headers:

   ```http
   HTTP/1.1 206 Partial Content
   Content-Type: audio/mp4
   Content-Length: 2
   Content-Range: bytes 0-1/430145
   Cache-Control: private, no-store
   ```

2. Request the final 128 bytes.

   ```sh
   curl --user prototype --basic --silent --show-error \
     --dump-header output/manual-suffix.headers \
     --output output/manual-suffix.bin \
     --header 'Range: bytes=-128' \
     http://127.0.0.1:18085/api/audio
   ```

   The response contains `Content-Range: bytes 430017-430144/430145`.

3. Request a range beyond the measured file.

   ```sh
   curl --user prototype --basic --silent --show-error --include \
     --header 'Range: bytes=430145-' \
     http://127.0.0.1:18085/api/audio
   ```

   The response has status `416` and `Content-Range: bytes */430145`.

4. Request audio without credentials.

   ```sh
   curl --silent --show-error --include http://127.0.0.1:18085/api/audio
   ```

   The response has status `401` and body `{"error":"AUTH_REQUIRED"}`.

5. Request the internal file directly.

   ```sh
   curl --silent --show-error --include \
     http://127.0.0.1:18085/_protected/sample.m4a
   ```

   The response has status `404`.

## Measured results: 2026-09-28

The input is `ejercicio_1.opus`, with a duration of 25.7065 s.
The conversion is AAC-LC in `.m4a`, with a duration of 25.693 s and a size of 430145 bytes.
The MP4 `moov` box precedes `mdat`, confirming fast start.

| Component | Measured version |
|---|---|
| Docker client / server | `28.2.2` / `27.4.0` |
| Docker architecture | `linux/arm64` |
| Docker Compose | `2.37.1` |
| nginx | `1.30.5` |
| ffmpeg | `7.1.1` |
| FastAPI | `0.141.1` |
| Uvicorn | `0.54.0` |

The backend image ID is `sha256:e86e1a327fa4f64fbb9bf2b4c9dd7300c84b1b065bd382d6ddfb758835924273`.
The source sample, converted audio, and downloaded responses remain local and uncommitted.

| Request | Status | Content-Range | Verified response |
|---|---:|---|---|
| Authorized GET | 200 | None | All 430145 bytes match. |
| Authorized HEAD | 200 | None | Length 430145; no downloaded body. |
| `bytes=0-1` | 206 | `bytes 0-1/430145` | Exact 2 bytes. |
| `bytes=100-199` | 206 | `bytes 100-199/430145` | Exact 100 bytes. |
| `bytes=-128` | 206 | `bytes 430017-430144/430145` | Exact 128 bytes. |
| `bytes=430017-` | 206 | `bytes 430017-430144/430145` | Exact 128 bytes. |
| HEAD with `bytes=0-1` | 206 | `bytes 0-1/430145` | Length 2; no downloaded body. |
| `bytes=430145-` | 416 | `bytes */430145` | Unsatisfiable range. |
| Anonymous GET | 401 | None | Stable authorization error. |
| Anonymous Range GET | 401 | None | Stable authorization error. |
| Incorrect password | 401 | None | Stable authorization error. |
| Direct internal URL, authorized | 404 | None | Direct file access denied. |
| Direct internal URL, anonymous | 404 | None | Direct file access denied. |

Successful responses use `audio/mp4` and `Cache-Control: private, no-store`.
Full responses advertise `Accept-Ranges: bytes`.
nginx consumes `X-Accel-Redirect`; clients do not receive that header.
All 17 unit tests and 13 curl integration cases pass.
The owner confirms completion of the manual step on 2026-09-29.
The report contains no device versions or details of the owner's test setup.

Evidence locations:

- `output/curl-20260928T204244Z-ec7ed479/`: final curl responses and assertions.
- `output/audio-metadata.json`: ffprobe output.
- `output/runtime.json`: versions, sample checksum, image ID, and MP4 box positions.
- `output/compose-up.log`: build and startup output.

## Manual Safari checklist

The owner confirms completion of the manual step on 2026-09-29.
The instructions below remain available for repeat checks.

**Caution:** Physical iOS/iPadOS devices cannot access this stand through their own `localhost`.
A separate approved network or HTTPS setup is necessary for those devices.
The prototype does not modify the VPS or expose credentials beyond this computer.

### macOS Safari

1. Start the stand with the setup procedure.
2. Open `http://127.0.0.1:18085/api/audio` in Safari.
3. Enter the disposable credentials from the local `.env`.
4. Confirm that Safari opens its native audio controls.
5. Confirm that the duration is approximately 26 s.
6. Start playback.
7. Seek to approximately 20 s.
8. Confirm that playback resumes near that position.
9. Seek backward to approximately 5 s.
10. Confirm that playback resumes without downloading errors.
11. Pause playback.
12. Resume playback.
13. Allow playback to reach the end.
14. Open the internal URL `http://127.0.0.1:18085/_protected/sample.m4a`.
15. Confirm that nginx returns `404`, even after authentication.
16. Record the Safari version and the result.

Safari can serve a seek from its existing buffer.
A new network request is not necessary for every seek.
When Safari sends a Range request, confirm a `206` response in Web Inspector.

### iOS/iPadOS Safari

1. Obtain approval for an accessible HTTPS test URL.
2. Repeat the playback and seeking steps on an iPhone or iPad.
3. Record the device, operating-system version, Safari version, and result.

Use the same playback steps in Chrome for the supported-browser comparison.
Record browser and device versions when repeating these checks.

## Stop the stand

1. Stop only this prototype's containers and networks.

   ```sh
   docker-compose down
   ```

The command retains local credentials, audio, and evidence.
No other Compose project belongs to this cleanup.

## Recommendation

Continue with X-Accel-Redirect and nginx byte-range delivery.
The owner confirms completion of the manual step on 2026-09-29.
The curl evidence confirms protocol behavior, not device playback.
Keep the product session-cookie design unchanged.
PHASE 0.5 remains open until the remaining prototypes and owner decisions finish.
