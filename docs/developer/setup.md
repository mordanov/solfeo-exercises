# Developer setup

This document explains how to run and check the current product skeleton.

Prerequisites:
- Install Python 3.12 and `uv`.
- Install Node.js 22.12 or later within version 22, with npm 12.1.0.
- Install Docker and Compose v2 for container checks.
- Read `docs/developer/env-variables.md`.

## Prepare configuration

Do not overwrite an existing `.env` file.
Do not copy credentials from the VPS or prototype configuration.

1. Copy `.env.example` to `.env` in a new checkout.
2. Adjust the documented values if necessary.
3. Keep `.env` outside Git.

## Run without containers

1. Run the backend from the repository root.

   ```sh
   uv sync --locked --python 3.12
   PYTHONPATH=backend uv run python -m app
   ```

2. Open a second terminal at the repository root.
3. Start the frontend.

   ```sh
   npm install --global npm@12.1.0
   npm ci
   npm run dev
   ```

4. Open `http://127.0.0.1:18080/`.
   Vite forwards `/api` requests to `http://127.0.0.1:18081`.
5. Press `Ctrl+C` in both terminals to stop the servers.

The backend reads the root `.env` through `Settings`.
Vite reads the same file but exposes only `VITE_*` values to browser code.
Changing a frontend build value requires a new build or development server restart.

## Run with containers

The local stand publishes only nginx on the loopback address.
The backend uses the private Compose network.
It has no database, file volume, or Telegram credentials.

1. Start the isolated stand from the repository root.

   ```sh
   docker compose --env-file .env -f deploy/compose.yaml up --build --wait
   ```

2. Open `http://127.0.0.1:18080/`.
3. Check the public endpoint.

   ```sh
   curl --fail http://127.0.0.1:18080/api/health
   ```

   The endpoint returns `{"status":"ok"}`.

4. Stop the stand.

   ```sh
   docker compose --env-file .env -f deploy/compose.yaml down
   ```

Use `docker-compose` if the standalone v2 executable is installed.
Do not run the container stand and Vite on the same host port simultaneously.
Do not use this local configuration to change the shared VPS.

## Check failure and recovery

Use these commands only for the local stand.
The frontend remains running during this check.

1. Stop the local backend.

   ```sh
   docker compose --env-file .env -f deploy/compose.yaml stop backend
   ```

2. Click the status-check button in the browser.
   The page shows an error.
3. Restart the local backend.

   ```sh
   docker compose --env-file .env -f deploy/compose.yaml up -d --no-deps --wait backend
   ```

4. Click the status-check button again.
   The page confirms that the backend is available.

## Run checks

Run these commands from the repository root.

```sh
uv run pytest
uv run ruff check backend
uv run ruff format --check backend
uv run mypy --config-file pyproject.toml
npm test
npm run lint
npm run format:check
npm run build
```

Backend health tests do not need PostgreSQL because the endpoint makes no database calls.
Later database tests must use real PostgreSQL, not SQLite.
Frontend tests cover translations, language changes, request failures, timeout, cancellation, and explicit retry.
The first implementation follows failing tests for the API, health page, and locale completeness.

## Update dependencies

Keep `uv.lock`, `requirements.txt`, and `package-lock.json` consistent with their manifests.
Use npm 12.1.0 for dependency updates; npm 10 fails during fresh workspace resolution in this environment.

1. Update the relevant manifest.
2. Resolve the dependencies with `uv lock` or `npm install`.
3. Export Python runtime dependencies after Python changes.

   ```sh
   uv export --locked --no-dev --no-emit-project --no-header --no-annotate --output-file requirements.txt
   ```

4. Run the checks and container build.

Docker installs Python dependencies with hashes and JavaScript dependencies with `npm ci`.
Base image digests are fixed in both Dockerfiles.
