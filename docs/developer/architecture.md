# Architecture

This document describes the current product skeleton and its boundaries.

Prerequisites:
- Read `docs/PRODUCT_BRIEF.md` and `docs/PHASES.md`.

The browser loads the React application from nginx.
Requests to `/api/` pass through nginx to FastAPI.
The local stand publishes nginx and PostgreSQL on loopback.
PostgreSQL uses a separate persistent volume.
The migration service completes before the backend starts.

| Path | Responsibility |
|---|---|
| `backend/app/api/` | HTTP routes and response schemas |
| `backend/app/main.py` | Application creation and HTTP error codes |
| `backend/app/settings.py` | Backend configuration |
| `backend/app/database.py` | Synchronous engine and database sessions |
| `backend/app/models/` | Typed accounts, exercises, media, student progress, and listening sessions |
| `backend/app/services/` | Account operations, exercise transactions, conversion, selection, and journal persistence |
| `backend/migrations/` | Versioned Alembic migrations |
| `backend/tests/` | Backend behavior tests |
| `frontend/src/api/` | Typed HTTP client |
| `frontend/src/features/health/` | Health query and status presentation |
| `frontend/src/features/auth/` | Session restoration, login, logout, password change, and route guards |
| `frontend/src/features/users/` | Manager-only user administration |
| `frontend/src/features/settings/` | Persisted language and note naming |
| `frontend/src/features/exercises/` | Manager forms, upload progress, protected previews, and reordering |
| `frontend/src/features/listening/` | Student selection, player, heartbeat queue, and exit delivery |
| `frontend/src/features/journal/` | Manager journal filters and pagination |
| `frontend/src/i18n/` | Translations and locale checks |
| `deploy/` | Development and production Compose, database bootstrap, and nginx configuration |
| `deploy/tests/` | Isolated production container checks |
| `prototypes/` | Independent risk prototypes |

TanStack Query owns server state.
The health request has a deadline and follows query cancellation.
The page does not show old successful data after a failed recheck.
Errors appear explicitly in the selected language.

Health is public by design.
Login is the only other public API operation.
User administration is manager-only; all roles can change their own settings.
Managers create, edit, delete, and reorder exercises.
Authenticated members can read active exercises and their current attachments.
Students use the listening interface; managers alone read the journal.
The product Telegram worker supplies manager-owned staged imports.
It shares the backend image and private media volume, but not the public proxy network.
See `telegram-import.md` for account linking and recovery.
API documentation routes remain disabled.
PHASE 1 implements authentication and emergency manager synchronization.
Database operations use synchronous SQLAlchemy 2.0 and psycopg 3.
The application creates one connection pool during startup and disposes it during shutdown.
Pool creation remains lazy, but startup now connects for mandatory emergency synchronization.
Database or schema failures prevent startup instead of silently skipping recovery.
The health route remains a liveness check.

Database-dependent handlers use synchronous functions.
Each request receives its own session through `get_session`.
The dependency closes the session but never commits automatically.
Business operations must use explicit transaction boundaries.
An exception or an uncommitted session causes a rollback.

Future workers create their own engines and sessions.
They must not share sessions or inherit active connection pools between processes.
Register future model imports in `backend/app/models/__init__.py` so Alembic sees their metadata.
Use migrations, not application startup, to create product tables.

The backend and frontend Docker images use non-root users and read-only filesystems.
The frontend and backend use temporary files under `/tmp`.
The backend writes media to the persistent `media_data` volume; frontend nginx mounts it read-only.
Authenticated file routes return an internal nginx redirect, not file bytes.
See `storage.md` for file limits, conversion, retention, and byte-range delivery.
No product container shares a prototype volume or credentials.
The worker directory will accompany worker implementation, not an empty placeholder.
The PostgreSQL development container uses the official image initialization and a writable data volume.
Its bootstrap database role is a local-development convenience, not the production role design.

Production separates the application and database networks.
PostgreSQL has no host port; only the backend and migration service share its network.
The frontend exposes loopback HTTP and joins the dedicated shared-nginx proxy network.
Application and migration credentials are distinct and cannot create databases or roles.
The migration role owns schemas; the application role has data access only.
The private version schema prevents runtime changes to Alembic metadata.
Production containers use bounded Docker logs and persistent database storage.
