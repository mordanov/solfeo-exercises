# Environment variables

This document lists every setting used by the current product slice.

Prerequisites:
- Copy the root `.env.example` into `.env` for a new checkout.
- Read `docs/developer/setup.md`.

Never commit `.env` or copy prototype tokens into it.
The backend uses one `Settings` class from `backend/app/settings.py`.
Environment variables override `.env` values.
Frontend build values are public; never put a secret in `VITE_*`.

| Variable | Default | Use |
|---|---|---|
| `API_HOST` | `127.0.0.1` | Native backend bind address |
| `API_PORT` | `18081` | Native backend port; integer from 1 to 65535 |
| `API_LOG_LEVEL` | `info` | Backend logging: critical, error, warning, info, debug, or trace |
| `API_FORWARDED_ALLOW_IPS` | `127.0.0.1` | Trusted forwarding sources; private Compose deployments use `*` |
| `AUTH_ALLOWED_ORIGINS` | Localhost origins on port 18080 | JSON array of exact origins; production requires `https://solfeo.miveralta.ru` |
| `SESSION_COOKIE_SECURE` | `true` | HTTPS-only session cookie; use `false` only for local HTTP |
| `SESSION_LIFETIME_DAYS` | `90` | Sliding session lifetime, from 1 to 365 days |
| `PASSWORD_MIN_LENGTH` | `12` | Minimum password length, from 8 to 128 characters |
| `LOGIN_USERNAME_LIMIT` | `5` | Failed attempts per normalized username within the window |
| `LOGIN_IP_LIMIT` | `30` | Login attempts per client IP within the window |
| `LOGIN_WINDOW_SECONDS` | `900` | Login-budget window, from 1 to 86400 seconds |
| `LOGIN_NGINX_RATE_PER_SECOND` | `5` | Frontend login limit, from 1 to 1000 requests per second |
| `LOGIN_NGINX_BURST` | `10` | Frontend login burst, from 1 to 1000 requests |
| `DEFAULT_LANGUAGE` | `en` | Initial stored language for new accounts: ru, en, or es |
| `EMERGENCY_MANAGER_USERNAME` | Empty | Configured recovery username; requires a password |
| `EMERGENCY_MANAGER_PASSWORD` | Empty | Recovery password; requires a username and configured password length |
| `EMERGENCY_MANAGER_FIRST_NAME` | `Emergency` | Recovery account first name |
| `EMERGENCY_MANAGER_LAST_NAME` | `Manager` | Recovery account last name |
| `MEDIA_ROOT` | `/app/media` | Native storage directory; Compose fixes the shared mount to this path |
| `IMAGE_MAX_BYTES` | `20971520` | Maximum original image bytes |
| `AUDIO_MAX_BYTES` | `52428800` | Maximum input and converted audio bytes |
| `UPLOAD_MAX_BYTES` | `74448896` | Maximum complete HTTP request, including multipart overhead |
| `IMAGE_MAX_PIXELS` | `40000000` | Maximum width multiplied by height |
| `AUDIO_MAX_SECONDS` | `1800` | Maximum accepted audio duration |
| `MEDIA_TIMEOUT_SECONDS` | `120` | Deadline for each file, ffprobe, or ffmpeg process |
| `AUDIO_BITRATE_KBPS` | `128` | AAC target bitrate, from 32 to 320 kbit/s |
| `FFMPEG_BINARY` | `ffmpeg` | Conversion executable; arguments never use a shell |
| `FFPROBE_BINARY` | `ffprobe` | Audio inspection executable |
| `FILE_BINARY` | `file` | Signature-based MIME inspection executable |
| `DATABASE_HOST` | `127.0.0.1` | PostgreSQL host for native execution |
| `DATABASE_PORT` | `15432` | PostgreSQL port for native execution; integer from 1 to 65535 |
| `DATABASE_NAME` | `solfeo` | Development database name |
| `DATABASE_USER` | `solfeo` | Database login |
| `DATABASE_PASSWORD` | Required | Nonempty private password; no fallback password |
| `DATABASE_POOL_SIZE` | `5` | Persistent connections per backend process; minimum 1 |
| `DATABASE_MAX_OVERFLOW` | `5` | Extra concurrent connections per process; minimum 0 |
| `DATABASE_POOL_TIMEOUT_SECONDS` | `10` | Maximum wait for a pooled connection; minimum 1 second |
| `DATABASE_CONNECT_TIMEOUT_SECONDS` | `5` | Driver connection timeout; minimum 1 second |
| `ALEMBIC_VERSION_SCHEMA` | `public` | Alembic version schema for native/development commands |
| `POSTGRES_HOST_PORT` | `15432` | Loopback host port for the development database |
| `TEST_POSTGRES_HOST_PORT` | `15433` | Loopback host port for the disposable test database |
| `FRONTEND_HOST` | `127.0.0.1` | Vite development bind address |
| `FRONTEND_PORT` | `18080` | Vite development port; integer from 1 to 65535 |
| `API_PROXY_TARGET` | `http://127.0.0.1:18081` | Native backend origin for the Vite proxy |
| `VITE_DEFAULT_LANGUAGE` | `en` | Initial page language: en, ru, or es |
| `VITE_HEALTH_TIMEOUT_MS` | `5000` | Shared health/account HTTP deadline in milliseconds; integer from 1 to 2147483647 |
| `VITE_UPLOAD_TIMEOUT_MS` | `600000` | Multipart upload deadline, including conversion, in milliseconds |
| `WEB_BIND_ADDRESS` | `127.0.0.1` | Local Compose host bind address |
| `WEB_PORT` | `18080` | Local Compose host port |
| `BACKEND_IMAGE` | Required for production | Tested backend image reference; use an immutable digest |
| `FRONTEND_IMAGE` | Required for production | Tested frontend image reference; use an immutable digest |
| `PRODUCTION_WEB_PORT` | `18090` | Production frontend loopback port |
| `PRODUCTION_PROXY_NETWORK` | `solfeo-proxy` | External network shared only by TLS nginx and the product frontend |
| `POSTGRES_ADMIN_PASSWORD` | Required for production | Separate bootstrap administrator password |
| `MIGRATION_DATABASE_USER` | `solfeo_migrator` | Production schema owner; different from the application user |
| `MIGRATION_DATABASE_PASSWORD` | Required for production | Separate schema owner password |
| `PRODUCTION_MIGRATION_SCHEMA` | `migrations` | Private production Alembic version schema |
| `DOCKER_LOG_MAX_SIZE` | `10m` | Production Docker log size limit |
| `DOCKER_LOG_MAX_FILE` | `3` | Maximum rotated Docker log files per production container |

Compose fixes the internal backend address to `0.0.0.0:8000` and nginx to port `8080`.
Those internal ports form the container network contract; `API_HOST` and `API_PORT` apply to native execution.
Compose passes `API_LOG_LEVEL` to the backend and frontend build values as build arguments.
Change `WEB_PORT` to select another published port.
Keep the host bind addresses on loopback for local development.

Compose fixes the database container address to `postgres:5432`.
Native application processes use `DATABASE_HOST` and `DATABASE_PORT`.
Keep `DATABASE_PORT` equal to `POSTGRES_HOST_PORT` for the documented native workflow.
The test command overrides `DATABASE_NAME` and `DATABASE_PORT`, not the development configuration file.
The test database always uses the name `solfeo_test`.

Production uses an independent `.env.production` file with the same example as its starting point.
It does not publish PostgreSQL or backend ports and fixes the frontend bind address to loopback.
The migration service maps its owner credentials into `DATABASE_USER` and `DATABASE_PASSWORD`.
It maps `PRODUCTION_MIGRATION_SCHEMA` into `ALEMBIC_VERSION_SCHEMA`.
The backend receives neither administrator nor migration credentials.
Use lowercase identifiers of at most 63 characters for the version schema.
The production version schema must not be `public`, `information_schema`, or start with `pg_`.
Keep role names and schema names stable after initialization.

`Settings` constructs a `postgresql+psycopg` URL from separate fields.
Passwords can contain URL punctuation without manual encoding.
Neither `.env.example` nor `alembic.ini` contains a usable database password.
Do not print resolved Compose configuration because it contains the private password.

PostgreSQL initialization variables apply only when its data directory is empty.
Changing a name, user, or password in `.env` does not change existing database objects.
Keep the credentials stable or perform an explicit database change.

Before login, language selection applies only to the current page.
Authenticated settings persist in PostgreSQL and apply immediately after a successful update.
Both emergency credentials must be empty or configured together.
Never copy the example's insecure-cookie and localhost-origin values into production without adjusting them.
Keep `SESSION_COOKIE_SECURE=true` and HTTPS-only allowed origins on the VPS.
See `auth.md` before changing trusted proxy settings or emergency credentials.
Product bot variables will accompany PHASE 4.
Keep `UPLOAD_MAX_BYTES` above the sum of both file limits plus multipart overhead.
The product proxy waits `4 * MEDIA_TIMEOUT_SECONDS + 30` seconds for processing.
The shared VPS proxy has a 600-second transport ceiling and delegates upload-size enforcement to the product proxy.
Keep processing and browser deadlines consistent with that transport ceiling.
The prototype environment files remain separate.
