# Production deployment

This document describes verified releases, targeted VPS deployment, and safe rollback.

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
PostgreSQL, the backend, migration service, and product workers join the private database network.

The configuration passes isolated container checks locally and in CI.
The separate publication workflow supplies verified product images and a versioned release bundle.
`cd.yml` downloads that bundle and runs `deploy/rollout.py` through pinned SSH.
The shared nginx routes the existing TLS hostname to the product frontend.
Do not invoke the shared infrastructure's general deployment.

## OMR capacity

The rollout checks Linux `MemAvailable` before pulling images or stopping services when OMR is enabled.
It requires `OMR_MEMORY_MB + OMR_HOST_RESERVE_MB`, normally 1536 MiB.
`OMR_MEMORY_INSUFFICIENT` leaves the active release and database unchanged.
Do not disable this protection to fit a busy shared host.
Provision more RAM or arrange an operator-reviewed capacity change before retrying.
Swap alone does not satisfy this check; the OMR container does not use swap.

The 2026-09-30 VPS check finds approximately 116 MiB available RAM and no swap.
Disk cleanup leaves approximately 18 GiB free, but does not resolve the RAM constraint.
The SSH account has no noninteractive sudo access.
PHASE 5 production activation therefore requires operator action.
Setting `OMR_ENABLED=false` is an explicit maintenance option, not successful OMR deployment.

Rollout stops OMR before migration and includes it in health checks and compatible rollback.
The existing release bundle still contains 2 images; OMR runs from the backend image.

## Prepare configuration

Do not reuse a development database volume or copy development or prototype passwords.
Do not overwrite an existing production configuration file.

1. Create `.env.production` from `.env.example` with mode `0600`.
2. Set separate values for `DATABASE_PASSWORD`, `MIGRATION_DATABASE_PASSWORD`, and `POSTGRES_ADMIN_PASSWORD`.
3. Select distinct application and migration usernames.
4. Keep the private configuration at `~/solfeo-production/.env.production`.
5. Keep its database names and credentials stable after initialization.
6. Set `AUTH_ALLOWED_ORIGINS=["https://solfeo.miveralta.ru"]`.
7. Set `SESSION_COOKIE_SECURE=true`.
8. Configure both emergency credentials privately for first-user creation.

The local example intentionally disables Secure cookies for HTTP.
Do not retain that value or localhost origins in production.
See `auth.md` for emergency synchronization and ordinary manager setup.

The intended image names are `ghcr.io/mordanov/solfeo-backend` and `ghcr.io/mordanov/solfeo-frontend`.
Use image digests from a successful publication run's `release.json`.
See `docs/developer/ci-cd.md` for the publication gate and artifact contents.
CD supplies immutable references through each release's `images.env`.
It validates image names, source provenance, archive members, and deployment-file hashes before activation.
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

## Targeted deployment

The product uses the `solfeo-production` Compose project.
The server root is `~/solfeo-production`.
The operator prepares its private configuration once; CD never generates replacement database passwords.
CD requires Python 3.12 or newer and Docker Compose v2 or newer.
The existing server uses Python 3.13 for orchestration; application containers use Python 3.12.

Successful publication calls the reusable `cd.yml` workflow.
CD rejects a source commit that no longer matches `main`.
SSH uses a dedicated identity, `BatchMode`, and `StrictHostKeyChecking=yes`.
Private GHCR access uses temporary `GITHUB_TOKEN` credentials, removed by the final workflow step.
The workflow never runs the shared deployment script.

The rollout performs these operations:
1. Validate the bundle against the expected source commit and CI run.
2. Store the deployment files under `releases/<archive-sha256>/`.
3. Validate Compose and pull immutable image references.
4. Start PostgreSQL and wait for its healthcheck.
5. Stop only the product backend and frontend.
6. Run `alembic upgrade head` with the migration role.
7. Start the backend and frontend with container healthchecks.
8. Check Alembic heads, public HTTPS health JSON, and the frontend HTML.
9. Atomically record the current and previous release in `state.json`.

A host file lock prevents overlapping activations.
The stable `runtime/deploy/postgres-init.sh` path avoids unnecessary PostgreSQL recreation between releases.
A changed bootstrap script requires operator review before deployment.
The release files remain on the VPS after the Actions artifact expires.
The script keeps Compose errors in private `last-error.log`, not public Actions output.
Do not share that file without removing credentials.

### Failure and rollback

A migration or health failure stops the candidate backend and frontend.
If a previous release exists, the script checks its Alembic heads against the current database.
It restarts the previous images only when that check succeeds.
It then checks the previous release's schema and HTTP health.
Successful recovery still fails the deployment job with `DEPLOY_FAILED_ROLLED_BACK`.
The successful release record does not change.

If schema compatibility fails, both application services remain stopped.
The job reports `ROLLBACK_FAILED_MANUAL_RECOVERY_REQUIRED`.
The operator must select a compatible forward fix or an explicitly reviewed database recovery.
The script never automatically downgrades a schema or removes a volume.
Future migrations must preserve compatibility or explicitly require a maintenance deployment.
The PHASE 4 schema head is `0005_telegram`; earlier images cannot pass its compatibility check.
After that migration, recovery from a failed healthcheck requires a compatible PHASE 4 image.
The rollout includes the Telegram worker in stop, start, health, and compatible rollback operations.
Stop the legacy prototype poller before enabling the same bot token in the product worker.
Preserve the prototype's files and optional Compose service.
See `telegram-import.md` for configuration and readiness.

A failed first deployment has no previous release.
It leaves PostgreSQL and its volume intact and reports `FIRST_DEPLOY_FAILED_SERVICES_STOPPED`.
Correct the cause before retrying the verified release.
After a host crash or forced cancellation, inspect the saved state and containers before retrying.
The script does not claim automatic recovery from a power failure.

### Operator inspection

Read `state.json` to select the current release directory.
Use its Compose files and `images.env` together with the stable runtime directory.

```sh
cd ~/solfeo-production
release="releases/$(python3 -c 'import json; print(json.load(open("state.json"))["current"])')"
docker compose --project-name solfeo-production \
  --project-directory "$PWD/runtime/deploy" \
  --env-file .env.production --env-file "$release/images.env" \
  -f "$release/deploy/compose.prod.yaml" -f "$release/deploy/compose.proxy.yaml" ps
curl --fail http://127.0.0.1:18090/api/health
curl --fail https://solfeo.miveralta.ru/api/health
```

PostgreSQL must accept TCP connections before the migration service starts.
The backend starts only after the migration service exits successfully.
The frontend starts after the backend healthcheck passes.
The HTTP healthcheck remains a liveness check, not proof of database readiness.
Check the schema revision separately through the migration service.

Compose dependencies do not make a running release update atomic.
An old backend can remain running while a new migration fails.
The migration failure test stops the backend first and proves that the failed migration blocks its next start.
The rollout script implements the explicit stop, migration, start, and recovery order above.

## TLS and VPS integration

The existing shared nginx terminates TLS for `solfeo.miveralta.ru`.
Reuse its certificate and renewal mechanism instead of requesting another certificate in this project.
Preserve the `/prototype-share/` route until a separate cleanup task.
The production frontend serves internal HTTP behind that TLS boundary.

A containerized shared nginx cannot reach the host through its own `127.0.0.1`.
The external `solfeo-proxy` network connects only shared nginx and the product frontend.
`deploy/compose.proxy.yaml` gives the frontend the unique alias `solfeo-product-frontend`.
Shared nginx resolves this alias dynamically and proxies to port `8080`.
The backend and PostgreSQL do not join this network.
The shared Compose file preserves nginx's network attachment after recreation.
Only the prototype location retains its GET/HEAD restriction; product requests reach the application.
PHASE 1 uses the trusted header chain documented in `auth.md`.
Keep the backend private when using `API_FORWARDED_ALLOW_IPS=*`.
PHASE 2 adds the private `media_data` volume.
The backend writes this volume; frontend nginx mounts it read-only.
Keep this volume across releases and rollbacks.
See `storage.md` for ownership, file delivery, and retention.
The shared product route streams uploads to the private proxy without its default 1 MiB limit.
Its 600-second timeout permits conversion; the private proxy enforces configured file and request limits.
Keep the historical prototype route unchanged.

This dedicated product project is an exception to shared database onboarding.
Do not register its database or services under the shared stack's `compose_services`.
The existing hostname entry remains responsible for the certificate and prototype.
The shared workflow guide links to the authoritative paired product workflows instead of a generic deployment template.

The first live integration uses shared commit `ac76b1c`.
The operator builds the shared nginx image, copies only the Solfège templates into the running container, and renders the active HTTPS configuration.
The operator validates with `nginx -t` before a graceful reload.
The existing container joins `solfeo-proxy` without recreation.
The committed Compose network definition preserves this attachment during future recreation.
These targeted operations preserve all 44 existing container IDs and start times.
Do not substitute the shared infrastructure's general deployment for these scoped operations.

The deployment prerequisite report checks `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, and `VPS_KNOWN_HOSTS`.
The rollout accepts optional `VPS_PORT`, with port 22 as its default.
Host-key entries must match the configured host and port.
The pipeline needs `packages: write` to publish through `GITHUB_TOKEN`.

## Reproduce the isolated checks

These commands require Docker and the locked developer dependencies.
The tests use locally built images instead of unpublished registry images.

```sh
docker compose --env-file .env -f deploy/compose.yaml build backend frontend
uv run --locked pytest deploy/tests -q
```

Each run creates a unique `solfeo-prod-check-*` project with generated credentials and a temporary host port.
The checks cover privileges, private ports, schema persistence, failed migrations, failed healthchecks, previous-image recovery, and password-free logs.
Account checks cover real nginx login, user creation, settings, role denial, backend restart persistence, and proxy-resistant login throttling.
The rollout test maps synthetic digest references to CI-built images; all migrations and service operations use real containers.
It also verifies that only the frontend joins its disposable proxy network.
The test cleanup removes only its disposable project and volume.
It does not change the development volume or contact the VPS.
