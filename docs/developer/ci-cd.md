# CI and deployment scope

This document explains the checks and deployment boundaries for the first product slice.

Prerequisites:
- Read `docs/developer/setup.md`.
- Read `docs/STATUS.md` before deployment work.

## Current CI

`.github/workflows/ci.yml` runs on relevant pull requests, pushes to `main`, and manual dispatch.
It uses read-only repository permissions.
The backend job checks tests, Ruff, formatting, strict mypy, and the hashed dependency export.
The frontend job checks tests, ESLint, Prettier, TypeScript, and the production build.
The container job builds both images and verifies health through nginx.
It stops its Compose project after the checks.

The health-only backend has no database dependency.
The database task will add PostgreSQL services and migration checks.
Pre-commit integration remains a separate PHASE 0 task.

## Deployment boundary

This workflow neither publishes images nor connects to the VPS.
The existing prototype publishing workflows remain separate.
The local Compose file is not the production deployment configuration.
Product CD, GHCR publication, migrations, rollback, and production acceptance remain unfinished PHASE 0 tasks.

Do not run the shared infrastructure's general deployment for a scoped product change.
Plan the named services, nginx routes, migration order, and rollback before the first product deployment.
Preserve the active Telegram prototype, its data, and unrelated services.
