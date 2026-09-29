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

## Exercises and files

| Method and path | Permission | Input and result |
|---|---|---|
| `GET /api/exercises` | Member | `offset`, `limit`; returns ordered `exercises` and `total` |
| `GET /api/exercises/{id}` | Member | Returns one active exercise |
| `POST /api/exercises` | Manager, CSRF | Multipart form; creates an exercise with status 201 |
| `PUT /api/exercises/{id}` | Manager, CSRF | Multipart form; replaces metadata and selected attachments |
| `DELETE /api/exercises/{id}` | Manager, CSRF | Soft-deletes the exercise; returns `{"status":"ok"}` |
| `PUT /api/exercises/order` | Manager, CSRF | JSON `{"ids":[...]}` containing every active exercise exactly once |
| `GET /api/exercises/{id}/files/{kind}` | Member | Internal nginx redirect for `image` or `audio`; supports Range |
| `HEAD /api/exercises/{id}/files/{kind}` | Member | Same authorization and headers without file bytes |

Multipart fields are `title`, `description`, `category`, `image`, `audio`, `remove_image`, and `remove_audio`.
Title requires 1–200 nonblank characters.
Description permits 10000 characters; category permits 100 and normalizes an empty value to null.
Description defaults to empty; both removal flags default to false.
Omitted file fields preserve existing attachments during updates.
A removal flag and replacement file for the same kind conflict.
Every saved exercise requires at least one image or audio attachment.

Responses contain `id`, `title`, `description`, `category`, `position`, `image`, and `audio`.
Each non-null attachment contains its UUID, `mime_type`, `size_bytes`, and nullable `duration_seconds`.
Responses never contain storage paths or client filenames.
The list defaults to 10000 rows and permits at most 10000 per request.
A partial or changed list cannot replace the global order.
Order conflicts return 409 `EXERCISE_ORDER_CONFLICT`.

Deleted exercises return 404 `EXERCISE_NOT_FOUND`.
Missing attachments return 404 `FILE_NOT_FOUND`.
Missing required attachments return 422 `EXERCISE_MEDIA_REQUIRED`.
Oversized requests or files return 413 `FILE_TOO_LARGE`.
Unsupported signatures return 415 `UNSUPPORTED_MEDIA`.
Invalid files, excessive duration, and processor timeouts return specific 422 codes.
Unavailable processors and storage failures return specific 503 codes.
See `storage.md` for conversion and retention details.

## Student listening and manager journal

| Method and path | Permission | Input and result |
|---|---|---|
| `GET /api/listening/current` | Student | Returns `{"exercise": ...}` or a null exercise |
| `POST /api/listening/select` | Student, header CSRF | `mode`, `direction`, optional `current_id` and `previous_id`; returns selected exercise |
| `POST /api/listening/events` | Student, body CSRF | Records start, heartbeat, end, or ended; returns UUID, completion, and terminal time |
| `GET /api/journal` | Manager | Filtered `sessions` and `total` |
| `GET /api/journal/options` | Manager | Recorded `students` and `exercises` with IDs, labels, and deletion flags |

Selection mode is `sequential` or `random`; direction is `current`, `next`, or `previous`.
The optional `previous_id` supports random history navigation.
Random and sequential choices do not start audio.

Events require `session_id` as UUID, positive `exercise_id`, event type, nonnegative finite `position_seconds`, and `csrf_token`.
The player also sends `audio_id` as UUID and the mode.
An audio mismatch returns 409 `AUDIO_CHANGED`.
A UUID with another exercise returns 409 `LISTENING_SESSION_CONFLICT`; another student's UUID returns 403.
Image-only exercises return 422 `EXERCISE_HAS_NO_AUDIO`.
The optional `version` UUID on protected file routes rejects stale media versions with 404.

Journal filters are `student_id`, `exercise_id`, `started_from`, and `started_to`.
Date boundaries require time zones; an invalid range returns 422.
`offset` defaults to 0; `limit` defaults to 50 and permits at most 100.
Each row includes student identity, exercise snapshot and deletion flag, timestamps, maximum position, duration, and completion.
See `listening.md` for idempotency, beacon delivery, and pointer behavior.

## Manager Telegram imports

Every endpoint below requires an active manager with no pending password change.
Mutations also require the ordinary header CSRF token and allowed Origin.
Import access is restricted to its owning manager.

| Method and path | Result |
|---|---|
| `GET /api/telegram` | Association status, worker availability, public bot username |
| `POST /api/telegram/link` | Single-use `code` and `expires_at` |
| `DELETE /api/telegram/link` | Revoke the association and outstanding codes |
| `GET /api/telegram/imports` | `imports` and `total`; offset and limit, default 50, maximum 100 |
| `GET /api/telegram/imports/{id}/audio` | Protected staged audio; HEAD also supported |
| `POST /api/telegram/imports/{id}/retry` | Requeue a failed import |
| `POST /api/telegram/imports/{id}/apply` | Save the exercise and return `exercise_id` |

Apply accepts optional `exercise_id`, required nonblank `title`, and optional `description`.
Omitting the exercise ID creates a new exercise.
Replacing audio preserves other attachments and the journal.
Identical retries return the same exercise ID; different repeated choices return 409 `IMPORT_ALREADY_APPLIED`.
The API never exposes Telegram tokens, file IDs, or sender IDs.
See `telegram-import.md` for state, linking, and worker recovery.
