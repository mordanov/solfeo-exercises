# API

This document describes the endpoints available in the current product slice.

Prerequisites:
- Start the local stand with `docs/developer/setup.md`.

## Health

`GET /api/health` returns status `200` and `{"status":"ok"}`.
`HEAD /api/health` returns the same status without a response body.
Both methods set `Cache-Control: no-store`.
The endpoint needs no authentication and creates no session cookie.

This endpoint checks the FastAPI process only.
It does not establish database readiness, bot operation, or worker health.
The frontend validates both the HTTP status and the JSON body.

## Errors

| HTTP status | Body |
|---|---|
| 404 | `{"error":"NOT_FOUND"}` |
| 405 | `{"error":"METHOD_NOT_ALLOWED"}` |
| 401 | `{"error":"AUTH_REQUIRED"}` or `{"error":"INVALID_CREDENTIALS"}` |
| 403 | `{"error":"FORBIDDEN"}`, `{"error":"CSRF_FAILED"}`, or a protected-account error |
| 409 | `{"error":"USERNAME_TAKEN"}` |
| 422 | `{"error":"VALIDATION_ERROR"}`, `{"error":"INVALID_USERNAME"}`, or `{"error":"WEAK_PASSWORD"}` |
| 429 | `{"error":"RATE_LIMITED"}` |

The API returns codes, not translated messages.
The frontend reports health failures through localized client error codes.
nginx can return a gateway error when the backend stops; the frontend treats that response as a failure.
`/docs`, `/redoc`, and `/openapi.json` are not public routes.

## Authentication and authorization

Only health and login are public API endpoints.
All API responses use `Cache-Control: no-store`.
All mutations require an `Origin` from `AUTH_ALLOWED_ORIGINS`.
Authenticated mutations also require the current session's `X-CSRF-Token`.
JSON inputs reject unknown fields; validation errors do not echo passwords or request bodies.

| Method and path | Permission | Input and result |
|---|---|---|
| `POST /api/auth/login` | Public, allowed origin | `username`, `password`; returns `user` and `csrf_token`, sets the session cookie |
| `GET /api/auth/me` | Active session | Returns `user` and `csrf_token`; renews the sliding expiry |
| `POST /api/auth/logout` | Active session, CSRF | Revokes this session and expires its cookie |
| `PUT /api/auth/password` | Active session, CSRF | `current_password`, `new_password`; revokes all sessions and creates a replacement session |
| `PATCH /api/settings` | Student or manager, CSRF | `ui_language` and `note_naming`; returns the updated user |
| `GET /api/users` | Manager | `offset` and `limit`; returns `users` and `total` |
| `POST /api/users` | Manager, CSRF | Creates a user; returns the user with status 201 |
| `PATCH /api/users/{id}` | Manager, CSRF | Updates supplied `first_name`, `last_name`, `role`, or `is_active` |
| `POST /api/users/{id}/password` | Manager, CSRF | `password`, optional `must_change_password`; returns `{"status":"ok"}` |

User responses contain identity, names, role, active/emergency flags, password-change flag, language, and note naming.
They never contain password hashes or session-cookie values.
Create-user input requires `username`, `password`, `first_name`, `last_name`, and `role`.
Its optional `must_change_password` defaults to `true`.
New settings use `DEFAULT_LANGUAGE` and `letters`.
Usernames use 3–64 ASCII letters, digits, dots, underscores, or hyphens, starting with a letter or digit.
The service normalizes usernames to lowercase.
First and last names contain 1–100 nonblank characters.
Passwords contain at most 256 characters; `PASSWORD_MIN_LENGTH` controls their minimum length.

Users with `must_change_password=true` can access only identity, logout, and password-change operations.
Other protected operations return `PASSWORD_CHANGE_REQUIRED`.
An incorrect current password returns `CURRENT_PASSWORD_INVALID`.
Inactive and unknown users both receive `INVALID_CREDENTIALS` during login.
Expired, revoked, and inactive-account sessions receive `AUTH_REQUIRED`.
The manager interface prohibits self-administration and emergency-account changes.
These operations return `SELF_CHANGE_FORBIDDEN` or `EMERGENCY_USER_PROTECTED`.

User-list pagination defaults to 50 rows and allows at most 100.
The backend returns `Retry-After` when a PostgreSQL login budget expires in the future.
The nginx burst limit also returns `RATE_LIMITED`, without a precise retry deadline.
See `auth.md` for session storage, proxy trust, and recovery.
