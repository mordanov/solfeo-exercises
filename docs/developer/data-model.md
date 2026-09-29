# Database and migrations

This document explains the PostgreSQL foundation and the empty initial schema.

Prerequisites:
- Prepare private configuration with `docs/developer/setup.md`.
- Start the local PostgreSQL service.
- Read the synchronous SQLAlchemy decision in `docs/DECISIONS.md`.

## Current schema

The initial revision is `0001_initial`.
It creates no product tables.
Alembic maintains its own `alembic_version` table.
Development uses `public`; production uses a private version schema, normally `migrations`.
The configured schema must already exist before migration execution.
Users, sessions, exercises, the journal, and worker jobs belong to later phases.

`backend/app/models/__init__.py` provides the typed declarative base.
Its naming convention gives indexes and constraints stable names.
Give check constraints explicit names when adding them.
Do not call `Base.metadata.create_all()` from product startup code.

## Transactions

`Database` owns a synchronous SQLAlchemy engine and session factory.
The connection pool checks connections before reuse and uses configurable capacity and timeouts.
Each request or worker operation owns one session.
The session context closes connections and rolls back uncommitted work.
Only an explicit transaction commits changes.

Use `with session.begin():` around a business operation that must commit atomically.
Do not swallow a database error or replace it with a successful result.
SQLAlchemy hides bound parameter values in its error reports.

## Apply migrations

Run commands from the repository root.
The commands use `.env`; `alembic.ini` contains no database URL or password.

```sh
uv run alembic -c backend/alembic.ini upgrade head
uv run alembic -c backend/alembic.ini current --check-heads
uv run alembic -c backend/alembic.ini check
```

Compose runs `upgrade head` through its `migrate` service before backend startup.
Repeat execution must be safe when the database already has the current revision.
A failed migration prevents a new backend start.
The local migration service is not a replacement for production rollback orchestration.

## Check persistence

These commands affect only the local development database.
Do not remove the data volume.

1. Check the current revision.

   ```sh
   docker compose --env-file .env -f deploy/compose.yaml run --rm migrate alembic -c backend/alembic.ini current --check-heads
   ```

2. Restart only PostgreSQL.

   ```sh
   docker compose --env-file .env -f deploy/compose.yaml restart postgres
   docker compose --env-file .env -f deploy/compose.yaml up -d --wait postgres
   ```

3. Repeat the revision command.
   Alembic reports `0001_initial (head)`.
4. Open the local health page.
   Its existing behavior remains unchanged.

## Add future schema changes

1. Add typed models and register their imports in `backend/app/models/__init__.py`.
2. Generate a migration with `alembic revision --autogenerate` using the configuration above.
3. Review both upgrade and downgrade operations.
4. Run Ruff and strict mypy on the new migration.
5. Test an empty database and the previous schema revision.

Use only the disposable test database for downgrade tests.
The current test suite creates an empty schema and checks upgrade, repeated upgrade, downgrade, upgrade, and model drift.
No SQLite or database mocks replace PostgreSQL.

## Production boundary

The local stand uses the PostgreSQL bootstrap role for both application and migration connections.
The separate production configuration creates restricted application and migration roles.
The application role receives table DML and sequence access in `public`, but no schema ownership.
The private Alembic schema remains inaccessible to the application role.
Production bootstrap runs only on an empty, independent volume.
See `docs/developer/deploy.md` for role grants, migration order, and remaining CD requirements.
