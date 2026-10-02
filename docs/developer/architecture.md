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
| `frontend/src/features/omr/` | Review, lazy score rendering, and localized note-name lyrics |
| `frontend/src/features/spoken/` | Shared vocabulary, strict sequence parser, approved-only controls, and Web Audio scheduling |
| `worker/generate_spoken.py` | Offline generation and verification of public speech clips |
| `worker/omr.py` | PostgreSQL job claims, Audiveris execution, failure recovery, and readiness |
| `frontend/src/i18n/` | Translations and locale checks |
| `deploy/` | Development and production Compose, database bootstrap, and nginx configuration |
| `deploy/tests/` | Isolated production container checks |
| `prototypes/` | Independent risk prototypes |

TanStack Query owns server state.

Material UI `9.4.0` supplies visual components through Emotion.
Community DataGrid `9.14.0` shows users and the journal on larger screens.
Fontsource supplies local Roboto assets without external font requests.
React and React DOM remain at `19.3.0`.

The application requires Chrome 117+ and Safari 17+, following the official Material UI v9 guide.
Native date controls remain because Date Pickers requires an additional, unapproved date library.

`frontend/src/theme.ts` defines the shared palettes, typography, radius, shadows, and component overrides.
`AppTheme` surrounds the existing providers' application content without recreating the query client.
`ThemeToggle` uses Material UI color schemes and stores its presentation preference in `solfeo-theme`.
It does not call the settings API or replace the application tree.
Text colors meet 4.5:1 contrast; input outlines meet 3:1 contrast.

`frontend/src/appearance.ts` defines the approved paired schemes, fonts, sizes, and typed appearance defaults.
The original classic scheme remains the migration and anonymous-interface default.
`AppTheme` creates the selected theme without replacing application children.
Authenticated profile changes synchronize through its appearance context; logout restores the anonymous appearance.
Light/dark mode retains `solfeo-theme` browser storage independently of account preferences.

`AppearanceForm` keeps a local draft and renders an isolated example without changing the active page theme.
The example includes page and panel backgrounds, text, a native input, and primary and secondary buttons.
Its light/dark selector does not change the application's mode.
Saving sends only appearance fields through the existing protected settings endpoint.
Failed saving retains the draft and shows an explicit error.
Reset selects the standard appearance; the user must save it.

Base font sizes set root typography to 16, 18, or 20 px; relative interface sizes scale proportionally.
Roboto remains locally hosted; system and serif choices use installed browser fonts.
The score keeps its engraving, white surface, renderer, and playback lifecycle.

`frontend/src/components/Ui.tsx` adapts native control attributes to Material components.
Its explicit labels preserve keyboard access and form validation.
Native selects retain their event types, option elements, and selection behavior.
The native file controls and date controls preserve file selection and date boundaries.
The native tempo slider preserves speech cancellation on every change.
The obsolete shared CSS file no longer exists; component styling uses the theme and `sx`.

`ReadOnlyGrid` keeps the existing 50-row server pages and external Previous and Next handlers.
It disables sorting, filtering, selection, column menus, resizing, and dynamic evaluation.
All page rows remain available without virtualization.
Built-in grid text follows the selected interface language.

Below the theme's 600 px breakpoint, the component shows a semantic list of labeled cards.
Both presentations use the same typed column renderers, including permitted actions and localized values.
Changing the presentation does not change the server query, page size, filters, or inline editor.
Inline editors, confirmations, and OMR review remain inline.

Mobile theme overrides reduce heading sizes and repeated card padding.
Navigation uses 2 columns; links, buttons, and checkboxes provide targets of at least 44 px.
Forms use a shrinkable grid track; native selects retain their options and event handlers.
The layout does not hide horizontal overflow to conceal oversized content.

The score observes its host with `ResizeObserver`.
Width changes of at least 1 px trigger reflow; zero-width containers do not trigger rendering.
OSMD uses 75 % zoom below 600 px and the original scale on larger screens.
The renderer recalculates line breaks instead of scaling a fixed, wide SVG.
Rerendering restores the current cursor without fetching MusicXML again or replacing spoken controls.
Cleanup disconnects the observer; rendering errors retain the translated error and original image fallback.

Native audio, score refs, rendering effects, and speech scheduling remain unchanged.
The score surface remains white in dark mode.

Browser preferences initialize the anonymous interface; saved account language takes priority after authentication.
Localized manifests and original favicon, phone, and iPad icons support optional online installation.
`InstallApp` offers native mobile installation after a click, or browser-specific manual guidance.
Standalone applications suppress the offer; dismissal and installation listeners preserve existing authentication and playback trees.
No service worker or protected-file cache exists.
Docker context rules explicitly include only the public voice assets and installation assets.
nginx serves manifests with `application/manifest+json`.

The health panel appears only on Settings; other pages do not request health.
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
The OMR worker also shares the backend image and private media volume.
Production gives it only the private database network.
Its subprocess receives no application secrets.
See `omr-pipeline.md` for leases, review, resource limits, and measured recognition failures.
Spoken notes use approved MusicXML and pre-generated public vocabulary, not runtime TTS requests.
See `spoken-notes.md` for the committed vocabulary, timing, authorization, and browser acceptance.
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
The worker directory contains product OMR, Telegram, and offline speech generation.
The PostgreSQL development container uses the official image initialization and a writable data volume.
Its bootstrap database role is a local-development convenience, not the production role design.

Production separates the application and database networks.
PostgreSQL has no host port.
The backend, migration service, and both product workers share its private network.
The frontend exposes loopback HTTP and joins the dedicated shared-nginx proxy network.
Application and migration credentials are distinct and cannot create databases or roles.
The migration role owns schemas; the application role has data access only.
The private version schema prevents runtime changes to Alembic metadata.
Production containers use bounded Docker logs and persistent database storage.

The backend and workers emit structured logs with fixed event fields.
HTTP records contain methods, route templates, response statuses, and durations.
They exclude query strings, client addresses, request bodies, cookies, and tokens.
Exception records keep types and frame locations, not exception values.
nginx emits JSON access records without request URLs or client identities.
Docker rotates production logs using the configured size and file limits.
Existing worker healthchecks reject stale readiness markers and incomplete processing cycles.
See `troubleshooting.md` for inspection and recovery.
