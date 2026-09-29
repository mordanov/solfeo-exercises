# Architecture

This document describes the current product skeleton and its boundaries.

Prerequisites:
- Read `docs/PRODUCT_BRIEF.md` and `docs/PHASES.md`.

The browser loads the React application from nginx.
Requests to `/api/health` pass through nginx to FastAPI.
The local stand publishes only nginx on loopback.
The backend does not access PostgreSQL or external systems yet.

| Path | Responsibility |
|---|---|
| `backend/app/api/` | HTTP routes and response schemas |
| `backend/app/main.py` | Application creation and HTTP error codes |
| `backend/app/settings.py` | Backend configuration |
| `backend/tests/` | Backend behavior tests |
| `frontend/src/api/` | Typed HTTP client |
| `frontend/src/features/health/` | Health query and status presentation |
| `frontend/src/i18n/` | Translations and locale checks |
| `deploy/` | Local Compose and nginx configuration |
| `prototypes/` | Independent risk prototypes |

TanStack Query owns server state.
The health request has a deadline and follows query cancellation.
The page does not show old successful data after a failed recheck.
Errors appear explicitly in the selected language.

Health is public by design.
The skeleton exposes no exercise, user, upload, media, or bot operation.
API documentation routes remain disabled.
Authentication and emergency manager synchronization belong to PHASE 1.
The database task must choose sync or async SQLAlchemy before implementation.

The local Docker images use non-root users and read-only filesystems.
The frontend uses temporary nginx files under `/tmp`.
No product container shares a prototype volume or credentials.
The worker directory will accompany worker implementation, not an empty placeholder.
