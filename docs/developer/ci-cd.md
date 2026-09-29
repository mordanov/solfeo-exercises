# CI and deployment scope

This document explains the checks and deployment boundaries for the current product skeleton.

Prerequisites:
- Read `docs/developer/setup.md`.
- Read `docs/STATUS.md` before deployment work.

## Current CI

`.github/workflows/ci.yml` runs on relevant pull requests, pushes to `main`, and manual dispatch.
It uses read-only repository permissions.
The backend job checks tests, Ruff, formatting, strict mypy, and the hashed dependency export.
It starts pinned PostgreSQL 17 with a disposable `solfeo_test` database.
The test fixture refuses any other database name.
The job verifies migration upgrade, downgrade, repeated upgrade, the current revision, and model drift.
Its fixed test password belongs only to the disposable CI service, not a deployed database.
The frontend job checks tests, ESLint, Prettier, TypeScript, and the production build.
The container job generates a private password, builds both images, and runs the migration service.
It verifies the schema revision and health through nginx.
It stops its Compose project after the checks.

The HTTP health endpoint remains independent of database readiness.
Pre-commit integration remains a separate PHASE 0 task.

## Deployment boundary

This workflow neither publishes images nor connects to the VPS.
The existing prototype publishing workflows remain separate.
The local Compose file is not the production deployment configuration.
Product CD, GHCR publication, production migration orchestration, rollback, and VPS acceptance remain unfinished PHASE 0 tasks.

Do not run the shared infrastructure's general deployment for a scoped product change.
Plan the named services, nginx routes, migration order, and rollback before the first product deployment.
Preserve the active Telegram prototype, its data, and unrelated services.
