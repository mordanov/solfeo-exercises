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
Revision `0006_omr` adds versioned OMR jobs and manager review.
Revision `0007_appearance` adds account appearance preferences with predefined choices and database checks.
Revision `0008_game` adds game profiles, seasons, rounds, attempts, trophies, and custom avatar jobs.
Revision `0009_avatar_sheets` adds persistent avatar versions, progress, leases, and linked quota records.
Revision `0010_round_rules` adds immutable assistance switches and the rules version to each round.
Existing rows retain version 1, strict octave grading, and their recorded totals.
New rounds use version 2, note-name grading, and one score bonus from the disabled switches.
The migration defaults alone do not upgrade existing or manually inserted rounds to version 2.
The round service sets the new version explicitly.
Finalization locks the round and awards XP and the score bonus once.

The migration chain runs `0008_game` → `0009_avatar_sheets` → `0010_round_rules`, with one head.
Upgrading from `0009_avatar_sheets` preserves active avatar jobs and saved metadata.

| Table | Contents and constraints |
|---|---|
| `users` | Unique lowercase username, names, role, password hash, active/emergency flags, obligatory password change, language, note naming, appearance |
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
| `omr_jobs` | Exercise/image versions, current-result flag, status, attempts, lease token, timing, errors, private score filename, reviewer |
| `players` | Account ownership, name, built-in or custom selection, total XP |
| `seasons` | Player, number, start/end times; a partial unique index permits one active season per player |
| `rounds` | Player and season, difficulty, note count, immutable rules, status, scores, and timestamps |
| `task_attempts` | Round and season, clef, expected/given notes, correctness, timeout, and response time |
| `trophies_awarded` | Player and completed-round threshold; a unique index prevents duplicate awards |
| `custom_avatars` | Creator/player references, description, status, asset version, phase, saved-image count, claim token, attempts, timing, errors |
| `avatar_generation_log` | Creator, creation time, moderation flag, billable quota record |

Game statistics use completed rounds only.
The round index covers player, season, difficulty, and note count.
The attempt index covers season and round.

Statistics resets lock player rows, close current seasons, and create new seasons in one transaction.
Season numbers continue from the largest recorded number, even without an active season.
XP, trophies, rounds, attempts, and avatar selections remain unchanged.

Historical seasons remain available through ownership-protected APIs.
No new migration accompanies the statistics interface.

New custom avatars use asset version 2 with 30 level/emotion files.
The saved-image constraint permits values from 0 through 30.
Each new job links its exact quota record through `generation_log_id`.
Account and player row locks serialize generation creation and quota consumption.
Worker claims use row locks with `SKIP LOCKED` and durable lease tokens.
Files reside in persistent private media storage, not database image columns.
Older ready avatars retain asset version 1 and 3 emotion files.
Migration closes older pending jobs as interrupted without another paid request.

A partial unique index permits one current OMR job per exercise.
Each job references an immutable original image.
Replacing or removing the image invalidates older jobs.
Approval applies only to the current job identifier.
Soft deletion preserves job records and files but denies their retrieval.

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
The `light_scheme` and `dark_scheme` columns accept classic, forest, warm, or plum independently.
The `ui_font` column accepts roboto, system, or serif; `ui_font_size` accepts 16, 18, or 20.
Migration backfills preserve the classic schemes, Roboto font, and 16 px base size.
New accounts use the configured environment defaults; emergency-manager updates preserve existing appearance preferences.
Downgrade removes only the appearance columns and their checks.
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
   Alembic reports `0010_round_rules (head)`.
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
