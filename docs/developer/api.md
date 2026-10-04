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

## OMR and scores

Exercise responses include `omr`: `job_id`, `image_id`, `status`, `attempts`, and `last_error`.
Status is `none`, `pending`, `processing`, `needs_review`, `approved`, `rejected`, or `failed`.
The manager review panel resides on `/manager/exercises`; it does not introduce another page route.

| Method | Path | Access and result |
|---|---|---|
| GET | `/api/exercises/{id}/omr` | Authenticated member; current image recognition state |
| POST | `/api/exercises/{id}/omr/rerun` | Manager and CSRF; enqueue a new version, or return the existing active job |
| POST | `/api/exercises/{id}/omr/review` | Manager and CSRF; body contains `job_id` and `action` (`approve` or `reject`) |
| GET, HEAD | `/api/exercises/{id}/score?version={job_id}` | Manager review output, or current approved output for a student |

Score retrieval uses `X-Accel-Redirect`, `no-store`, and the MusicXML content type.
The internal `/_protected_scores/` location rejects direct requests.
The score version is mandatory.
Replacing the image or rerunning recognition makes an old version return `OMR_STALE`.
Students receive `FORBIDDEN` for current unapproved output.
Deleted exercises return `EXERCISE_NOT_FOUND`.
Worker failures expose stable `OMR_*` codes for translated UI errors.

## Game profiles

Game profiles remain separate from user accounts.
The application does not create them during startup, account creation, or login.

| Method | Path | Access and result |
|---|---|---|
| GET | `/api/game/players` | Manager sees all profiles; student sees only owned profiles |
| GET | `/api/game/players/accounts?offset=0` | Manager only; eligible accounts, filtered total, 50 per page |
| POST | `/api/game/players` | Manager and CSRF; creates a player and an active season |

Creation accepts `name`, optional `avatar_animal`, and optional positive `account_id`.
An omitted or null `account_id` assigns the profile to the requesting manager.
An explicit account must exist, be active, and not be the emergency manager.
Missing or inactive accounts return `404` with `PLAYER_ACCOUNT_NOT_FOUND`.
The emergency manager returns `422` with `PLAYER_EMERGENCY_ACCOUNT`.
A second profile returns `409` with `PLAYER_ACCOUNT_TAKEN`.
An identical existing profile name retains `409` with `PLAYER_NAME_TAKEN`.
Creation locks the owner account row before checking existing profiles.
Concurrent requests can create only one profile and one season.
Existing profiles and progress remain unchanged.
Rejected requests create neither a player nor a season.
Students receive `403` when they request creation.
Starting another account's round returns `404`, without disclosing that profile.

The eligible-account response contains `users` and the filtered `total`.
Each user contains only `id`, `username`, `first_name`, and `last_name`.
The query excludes inactive accounts, the emergency manager, and accounts with any player profile.
`offset` must be nonnegative; pages use a stable account-ID order.
The frontend refreshes this query after creation, including rejected attempts caused by concurrent changes.

Rounds use 14 natural pitches from C4 through B5 in either clef.
Answers contain the actual selected `name` and `octave` for every note.
The existing submission response supplies authoritative `correct_answers` for optional feedback.
Sound-hint and answer-revelation choices affect only the interface; they do not change scoring or permissions.

## Game avatars

Player responses include `avatar_animal`, `custom_avatar_id`, `xp`, and derived `avatar_level` from 1 to 10.
Students access only their own players.
Managers can choose avatars for any player without changing the existing player-management permissions.

| Method | Path | Access and result |
|---|---|---|
| GET | `/api/game/avatars/catalog` | Authenticated member; all 11 built-in identifiers |
| POST | `/api/game/players/{id}/avatar` | Owner or manager, with CSRF; body contains `avatar_animal`; clears custom selection |
| GET | `/api/game/avatars?player_id={id}` | Owner or manager; up to 5 recent generation jobs, excluding the selected job |
| POST | `/api/game/avatars/generate` | Owner or manager, with CSRF; description and player ID; configured service required |
| GET | `/api/game/avatars/{id}/status` | Job creator or manager; pending, ready, or failed |
| POST | `/api/game/avatars/{id}/use` | Job creator or manager, with CSRF; selects a ready job |
| DELETE | `/api/game/avatars/{id}` | Job creator or manager, with CSRF; discards a job and clears its active selection |
| GET, HEAD | `/api/game/avatars/{id}/files/{state}` | Job creator, player owner, or manager; private PNG through nginx |

File states use `neutral`, `happy`, and `sad`.
The neutral state uses the generated base image.
Invalid paths and missing files return `FILE_NOT_FOUND`.
Unconfigured creation returns status `503` with `AVATAR_GENERATION_UNAVAILABLE`.
See `game-avatars.md` for artwork correspondence, progression, and worker operation.

## Error responses

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

Unknown application pages return HTTP 404 with the localized React page and a home link.
This nginx fallback does not intercept API errors or direct protected-file denial.
GET and HEAD retain the same status; HEAD has no body.

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
| `PATCH /api/settings` | Student or manager, CSRF | Nonempty partial language, note-naming, or appearance update; returns the complete updated user |
| `GET /api/users` | Manager | `offset` and `limit`; returns `users` and `total` |
| `POST /api/users` | Manager, CSRF | Creates a user; returns the user with status 201 |
| `PATCH /api/users/{id}` | Manager, CSRF | Updates supplied `first_name`, `last_name`, `role`, or `is_active` |
| `POST /api/users/{id}/password` | Manager, CSRF | `password`, optional `must_change_password`; returns `{"status":"ok"}` |

User responses include `light_scheme`, `dark_scheme`, `ui_font`, and `ui_font_size`.
Schemes accept classic, forest, warm, or plum; fonts accept roboto, system, or serif.
Font size accepts the JSON numbers 16, 18, and 20.
Settings reject empty updates, explicit nulls, unsupported values, and unknown fields.
Omitted fields retain their current values; validation occurs before any changes.
The endpoint changes only the authenticated account and retains the existing origin and CSRF checks.

Example appearance update:

```json
{
  "light_scheme": "forest",
  "dark_scheme": "plum",
  "ui_font": "serif",
  "ui_font_size": 20
}
```

User responses contain identity, names, role, active/emergency flags, password-change flag, language, note naming, and appearance.
They never contain password hashes or session-cookie values.
Create-user input requires `username`, `password`, `first_name`, `last_name`, and `role`.
Its optional `must_change_password` defaults to `true`.
New settings use `DEFAULT_LANGUAGE`, `letters`, and the configured appearance defaults.
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
