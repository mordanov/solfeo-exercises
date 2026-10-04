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

Treble questions use natural pitches C4–A5; bass questions use E2–C4.
Round creation accepts `show_sound_hint` and `show_correct_answer`, defaulting to `true` and `false`.
The backend stores these immutable options with rules version 2.
Each disabled option adds 1 point once at completion, including losing rounds.
The final result includes `score_bonus`; XP and the winning threshold do not change.
Answers retain `name` and `octave`; version 2 grading compares names and order only.
The frontend plays each selected name in the current question note's written octave.
The existing submission response supplies authoritative `correct_answers` for optional feedback.
Submitted option changes or bonus amounts cannot affect stored settings or scoring.
Submission locks the round before checking its status, preventing concurrent finalization and duplicate XP or bonus awards.
Existing version 1 rounds retain strict octave grading without assistance bonuses.
Completed totals use `max(0, sum(task_score) + assistance_bonus)`.
Raw incorrect-answer scores remain -1.
Player locks serialize XP updates when different rounds complete concurrently.
Each new attempt stores its submission reply as JSON.
Identical retries return the stored reply, including the original next question and final result.
Each question includes `issued_at`, `deadline_at`, `server_time`, and `time_limit_ms`.
The frontend retains the initial server clock difference instead of recalculating it from delayed or cached replies.
Feedback uses `GAME_FEEDBACK_MS` rather than a separate client duration.
Practice hints contain structured expected and entered note names, or null.
The frontend localizes the pair using the selected language and note-naming setting.
Final results include nullable `average_score` from previous completed rounds at the same difficulty and note count across seasons.
The average excludes the current round; null means no matching history.
The frontend formats this value in the selected language.
Publish the backend and frontend together with migration `0011_game_rewards_review`.
Reload previously open game tabs after publication.

## Game statistics and seasons

The player selector links to `/game/profile/{id}`.
Managers also see **Player management**, which opens `/game/admin`.
Its detail route, `/game/admin/{id}`, includes profile statistics and mistake analysis.
Direct links and browser navigation retain these routes.
Students cannot render manager controls or read another account's statistics.

| Method | Path | Access and result |
|---|---|---|
| GET | `/api/game/players/{id}` | Owner or manager; profile, XP, level, and actual all-time trophy thresholds |
| GET | `/api/game/players/{id}/stats?season_id={season}` | Owner or manager; completed-round matrix by difficulty and note count |
| GET | `/api/game/players/{id}/seasons` | Owner or manager; read-only season history |
| GET | `/api/game/players/{id}/confusion?season_id={season}&clef=bass` | Manager; season heatmap, top confusions, latest-round confusions, and missed notes |
| POST | `/api/game/players/{id}/seasons/reset` | Manager and CSRF; close the current season and create the next |
| POST | `/api/game/seasons/reset-all` | Manager and CSRF; reset all players in one transaction |

Omit `season_id` to use the current season.
A positive supplied identifier must belong to the selected player.
An unavailable season returns `404 SEASON_NOT_FOUND`.
An unavailable or unowned player returns `404 PLAYER_NOT_FOUND`.
The optional `clef` accepts `treble` or `bass`; omission includes both.
Invalid query values return `422`.

The matrix retains `rounds`, `total_correct`, and `avg_score`.
Each cell also includes `total_score`, `wins`, and percentage `win_rate`.
Wins require at least 5 correct answers, independent of assistance bonuses.
The client uses score totals for exact weighted summaries across groups.
Unfinished and expired rounds do not enter summaries or mistake analysis.
SQL aggregates note positions; it does not load every attempt into application memory.
`round_top_confusions` uses the latest completed round in the selected season.
`missed_notes` counts expected notes from timeouts separately from wrong note names.

Both reset bodies require `{"confirmation":"RESET"}`.
Other text returns `400 CONFIRMATION_REQUIRED`.
Resets lock player rows and preserve monotonically increasing season numbers.
Bulk resets acquire locks in player-ID order.
Neither reset removes rounds, attempts, XP, trophies, or saved avatars.
Lifetime prizes also survive both reset operations.

An in-progress round retains its original season after a reset.
Its eventual completion updates that season and all-time progress.

The client refreshes seasons, statistics, and confusion caches after successful resets.
A failed reset keeps its confirmation window open and shows the translated error.
Completed rounds also invalidate profile and statistics caches.
Publish the backend and frontend together; this change needs no new schema revision.

## Lifetime game prizes

`GET /api/game/players/{id}/achievements` requires ownership or manager access.
It returns `earned` entries with `code` and `awarded_at`, plus a `catalog` containing stable prize codes.
The profile response also includes earned `achievements` codes.
Round completion returns `new_achievements` codes for the localized result view.
The backend returns no translated prize names or descriptions.
The frontend uses `game.prizes.codes.<code>` for names and `game.prizes.descriptions.<code>` for conditions.
See `docs/PRODUCT_BRIEF.md` for all 20 conditions.
Each prize is lifetime and adds no XP.
Existing 20, 100, 200, and 500-round trophies remain separate.

## Game avatars

Player responses include `avatar_animal`, `custom_avatar_id`, `xp`, and derived `avatar_level` from 1 to 10.
They also include `avatar_review_job_id` and `avatar_review_status` for the waiting or rejected selection.
Students access only their own players.
Managers can choose avatars for any player without changing the existing player-management permissions.

| Method | Path | Access and result |
|---|---|---|
| GET | `/api/game/avatars/catalog` | Authenticated member; all 11 built-in identifiers |
| POST | `/api/game/players/{id}/avatar` | Owner or manager, with CSRF; body contains `avatar_animal`; clears custom selection |
| GET | `/api/game/avatars?player_id={id}` | Owner or manager; up to 5 recent generation jobs, excluding the selected job |
| GET | `/api/game/avatars/saved?player_id={id}&offset=0` | Owner or manager; `jobs` and `total`, 12 ready avatars per page |
| GET | `/api/game/avatars/quota` | Authenticated member; quota, generation availability, reason, and image count |
| POST | `/api/game/avatars/generate` | Owner or manager, with CSRF; description and player ID; configured service required |
| GET | `/api/game/avatars/{id}/status` | Job creator, player owner, or manager; status and durable progress |
| POST | `/api/game/avatars/{id}/use` | Job creator, player owner, or manager, with CSRF; selects a complete approved job |
| DELETE | `/api/game/avatars/{id}` | Job creator, player owner, or manager, with CSRF; discards a nonpending job |
| GET, HEAD | `/api/game/avatars/{id}/files/{state}` | Job creator, player owner, or manager; private PNG through nginx |
| GET | `/api/game/avatars/review?offset=0` | Manager; `jobs` and `total`, 12 ready pending results per page |
| POST | `/api/game/avatars/{id}/review` | Manager and CSRF; `{"decision":"approved"}` or `{"decision":"rejected"}` |
| GET, HEAD | `/api/game/avatars/{id}/review-sheet` | Manager; protected original generated sheet |

File states use `neutral`, `happy`, and `sad`.
The optional `level` query accepts 1–10 and defaults to 1.
Version 2 uses a separate file for each level and emotion; version 1 retains 3 shared emotion files.
Responses include `asset_version`, `review_status`, `phase`, image counts, and `estimated_seconds_remaining`.
Review status is `pending`, `approved`, or `rejected`, independently of generation status.
Automatic moderation checks both the description and generated image before manager review.
The interface translates phases, states, errors, accessible names, and review actions in the selected language.
The remaining time is approximate; `null` means unknown, overdue, or failed.
Ready jobs report 0 remaining seconds.
The quota response includes `generation_available`, `generation_reason`, and `image_count:30`.
An identical pending description returns the existing `job_id` without consuming quota.
Another pending description or a pending discard returns `409 AVATAR_JOB_BUSY`.
Incomplete version 2 storage prevents selection with `409 AVATAR_ASSETS_MISSING`.
Invalid paths and missing files return `FILE_NOT_FOUND`.
Unconfigured creation returns status `503` with `AVATAR_GENERATION_UNAVAILABLE`.
Saved-avatar access does not require a configured provider.
Student image requests before approval return `403 AVATAR_NOT_APPROVED`.
Unapproved status responses omit private image paths.
Managers can inspect all 10 levels and 3 emotions through the protected frame endpoints.
The queue also includes `player_id`, `player_name`, `account_id`, `description`, and `created_at`.
The queue lists the oldest jobs first.
Repeated identical decisions return the existing result.
A different decision after review returns `409 AVATAR_REVIEW_CONFLICT`.
Invalid decision values return validation errors or `AVATAR_REVIEW_INVALID`.
Approval activates the waiting player selection in the same transaction.
It activates only when `players.avatar_review_job_id` still identifies that job.
A later explicit built-in choice remains unchanged.
Rejection removes the unapproved custom selection and retains the question-mark fallback.
Neither decision makes another provider request.
Migration marks existing ready avatars approved to retain earlier selections.
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
