# CI and deployment scope

This document explains the checks and deployment boundaries for the current product skeleton.

Prerequisites:
- Read `docs/developer/setup.md`.
- Read `docs/STATUS.md` before deployment work.

## Current CI

`.github/workflows/ci.yml` runs on relevant pull requests, pushes to `main`, and manual dispatch.
It uses read-only repository permissions.
The `checks` job runs `.pre-commit-config.yaml` with `--all-files`.
It checks Ruff, formatting, strict mypy, ESLint, Prettier, and TypeScript with the same commands used before local commits.
Python tools come from `uv.lock`; frontend tools come from `package-lock.json`.
The JavaScript hooks use isolated Node.js 22.23.3 and npm 12.1.0.
Changes to the hook configuration trigger CI.

The backend job checks tests and the hashed dependency export.
It starts pinned PostgreSQL 17 with a disposable `solfeo_test` database.
The test fixture refuses any other database name.
The job verifies migration upgrade, downgrade, repeated upgrade, the current revision, and model drift.
Its fixed test password belongs only to the disposable CI service, not a deployed database.
The frontend job checks tests and the production build, including its TypeScript compilation.
The container job generates a private password, builds both images, and runs the migration service.
It verifies the schema revision and health through nginx.
It also runs `deploy/tests` against a separate production Compose project using the freshly built images.
Those checks verify restricted database roles, private ports, migration metadata isolation, persistence, and failed-migration recovery.
It stops its Compose project after the checks.

The HTTP health endpoint remains independent of database readiness.
Pre-commit selects product files only; prototype workflows remain independent.
All 6 hooks reject deliberate defects during local verification and pass after removal of those temporary files.

## Deployment boundary

This workflow neither publishes images nor connects to the VPS.
The existing prototype publishing workflows remain separate.
`deploy/compose.prod.yaml` provides a separate, image-based production configuration.
See `docs/developer/deploy.md` for its role boundaries and operational requirements.
Product CD, GHCR publication, production migration orchestration, rollback, and VPS acceptance remain unfinished PHASE 0 tasks.

Do not run the shared infrastructure's general deployment for a scoped product change.
Plan the named services, nginx routes, migration order, and rollback before the first product deployment.
Preserve the active Telegram prototype, its data, and unrelated services.
