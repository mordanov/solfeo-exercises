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
| `VITE_HEALTH_TIMEOUT_MS` | `5000` | Request deadline in milliseconds; integer from 1 to 2147483647 |
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

The language selector changes only the current page.
The application does not save a user language until PHASE 1 implements user settings.
Authentication, storage, and product bot variables will accompany their implementation.
The prototype environment files remain separate.
