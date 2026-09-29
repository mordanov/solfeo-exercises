# Database and migrations

This document explains the PostgreSQL account, exercise, and media schemas.

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
Revision `0002_auth` adds the PHASE 1 tables.
Revision `0003_exercises` adds exercises and media.
Revision `0004_listening` adds student progress and the listening journal.
Revision `0005_telegram` adds account associations, hashed linking codes, durable imports, and bot state.
The Telegram worker uses these tables; OMR jobs remain in PHASE 5.

| Table | Contents and constraints |
|---|---|
| `users` | Unique lowercase username, names, role, password hash, active/emergency flags, obligatory password change, language, note naming |
| `login_sessions` | Hashed token primary key, user foreign key, CSRF token, creation time, expiry |
| `login_limits` | Hashed username/IP budget key, attempt count, expiry |
| `media_files` | UUID, generated filename, MIME type, positive byte count, optional positive duration, creation time |
| `exercises` | Title, description, optional category, nonnegative position, image/audio foreign keys, deletion time, creation time |
| `student_progress` | User primary key, sequential next-exercise reference, last random exercise reference |
| `listening_sessions` | Unique client UUID, user/exercise/audio references, title snapshot, receipt timestamps, duration, maximum position, completion |
| `telegram_links` | User primary key and unique numeric Telegram sender |
| `telegram_link_codes` | User primary key, unique token hash, expiry |
| `telegram_updates` | Telegram update primary key, owner, file reference, status, attempts, errors, converted media, applied exercise |
| `telegram_state` | Bot identity, durable next offset, last successful heartbeat |

Exercises require at least one media foreign key.
Create, delete, and reorder operations share a transaction-level advisory lock.
Positions remain contiguous across active exercises.
Deletion sets `deleted_at`; it does not remove rows or files.
Replacements preserve previous media records and original images.
The API exposes only current attachments of active exercises.
Journal references do not cascade deletion.
The journal retains exercise titles and audio durations after later changes.
Indexes cover student, exercise, and start-time filters.
Advisory locks serialize session UUID updates and student pointer changes.

Database checks constrain roles, languages, and note naming.
A partial unique index permits at most 1 emergency account.
Sessions reference users without cascading deletion.
Manager operations deactivate users instead of deleting them.
Expiry indexes support session and login-budget cleanup.

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
   Alembic reports `0005_telegram (head)`.
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
