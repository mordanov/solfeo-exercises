# Production deployment

This document describes the production Compose configuration and the remaining VPS deployment work.

Prerequisites:
- Use Docker with Compose v2.
- Prepare tested backend and frontend images for the VPS architecture.
- Keep `postgres-init.sh` alongside the Compose file, with its executable bit.
- Read `docs/developer/env-variables.md` and `docs/developer/data-model.md`.
- Preserve the existing Telegram worker, PWA prototype, and unrelated VPS services.

## Current boundary

`deploy/compose.prod.yaml` is a separate project, not an override of the development stand.
It uses supplied images and never builds application code on the server.
It publishes only the frontend on `127.0.0.1:18090` by default.
PostgreSQL and the backend have no published ports.
Only PostgreSQL, the backend, and the migration service join the private database network.

The configuration passes isolated container checks locally and in CI.
This task does not publish product images, configure public routing, or deploy to the VPS.
The following production procedure requires the later CD and nginx integration task.
Do not invoke the shared infrastructure's general deployment.

## Prepare configuration

Do not reuse a development database volume or copy development or prototype passwords.
Do not overwrite an existing production configuration file.

1. Create `.env.production` from `.env.example` with mode `0600`.
2. Set separate values for `DATABASE_PASSWORD`, `MIGRATION_DATABASE_PASSWORD`, and `POSTGRES_ADMIN_PASSWORD`.
3. Select distinct application and migration usernames.
4. Set `BACKEND_IMAGE` and `FRONTEND_IMAGE` to tested registry references.
5. Prefer registry digests instead of mutable tags.

The intended image names are `ghcr.io/mordanov/solfeo-backend` and `ghcr.io/mordanov/solfeo-frontend`.
Image publication remains unimplemented.
Compose requires nonempty references but does not enforce their immutability; CD must supply the tested digests.
Frontend language and timeout settings are build-time values within the frontend image.
Changing those values in the server environment does not rebuild that image.

Do not print `docker compose config` output because it contains passwords.
Use `config --quiet` to validate the configuration without printing values.
Keep the configuration file and registry credentials outside Git.

## Database roles

The PostgreSQL bootstrap script runs only against an empty data directory.
It creates all application roles, grants, and schemas in one transaction.

| Role | Rights |
|---|---|
| `postgres` | Bootstrap administrator; its password stays in the PostgreSQL service |
| Migration role | Owns the database and schemas; no superuser, database-creation, or role-creation privileges |
| Application role | Connects and performs table DML; cannot create, alter, or drop tables |

The backend receives only application credentials.
The migration service receives only migration credentials.
The PostgreSQL bootstrap service needs all 3 passwords to create the roles.
The application role has no membership in the migration role.
Default grants apply to future tables and sequences created by the migration role in `public`.

Alembic stores its version in the private `migrations` schema by default.
The application role cannot access this schema.
The development stand retains its existing `public.alembic_version` table.
Changing the configured schema does not move an existing version table.

Changing environment values does not update roles or passwords inside an initialized volume.
Plan credential rotation explicitly.
If first initialization fails, inspect the error before taking any action on the volume.
Never remove an existing production volume as an automatic recovery step.

## Start and verify

Run these commands only after the image release and targeted VPS integration are ready.

```sh
docker compose --env-file .env.production -f deploy/compose.prod.yaml config --quiet
docker compose --env-file .env.production -f deploy/compose.prod.yaml pull
docker compose --env-file .env.production -f deploy/compose.prod.yaml up -d --wait
docker compose --env-file .env.production -f deploy/compose.prod.yaml run --rm --no-deps migrate alembic -c backend/alembic.ini current --check-heads
curl --fail http://127.0.0.1:18090/api/health
```

PostgreSQL must accept TCP connections before the migration service starts.
The backend starts only after the migration service exits successfully.
The frontend starts after the backend healthcheck passes.
The HTTP healthcheck remains a liveness check, not proof of database readiness.
Check the schema revision separately through the migration service.

Compose dependencies do not make a running release update atomic.
An old backend can remain running while a new migration fails.
The migration failure test stops the backend first and proves that the failed migration blocks its next start.
CD must define release order, compatibility, and rollback before the first live update.

## TLS and VPS integration

The existing shared nginx terminates TLS for `solfeo.miveralta.ru`.
Reuse its certificate and renewal mechanism instead of requesting another certificate in this project.
Preserve the `/prototype-share/` route until a separate cleanup task.
The production frontend serves internal HTTP behind that TLS boundary.

A containerized shared nginx cannot reach the host through its own `127.0.0.1`.
The integration task must connect only the frontend to an appropriate shared proxy network.
It must use an unambiguous upstream name and retain database network isolation.
Review trusted forwarded headers before authentication starts in PHASE 1.

The CD task must specify SSH host, port, user, private key, and pinned known-host keys through GitHub secrets.
It must also configure registry pull access when images are private.
The pipeline needs `packages: write` to publish through `GITHUB_TOKEN`.
Secret names, publication workflow, rollout script, and rollback remain part of that task.

## Reproduce the isolated checks

These commands require Docker and the locked developer dependencies.
The tests use locally built images instead of unpublished registry images.

```sh
docker compose --env-file .env -f deploy/compose.yaml build backend frontend
uv run --locked pytest deploy/tests -q
```

Each run creates a unique `solfeo-prod-check-*` project with generated credentials and a temporary host port.
The checks cover role privileges, private ports, schema persistence, migration failure, recovery, and password-free logs.
The test cleanup removes only its disposable project and volume.
It does not change the development volume or contact the VPS.
