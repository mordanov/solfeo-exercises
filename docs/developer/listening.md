# Listening and journal

This document explains selection, playback events, persistence, and the PHASE 3 permission boundaries.

Prerequisites:
- Read `auth.md`, `api.md`, and `storage.md`.
- Apply migration `0004_listening`.
- Use Chrome or Safari through the nginx stand.

## Selection

`student_progress` stores a sequential next-exercise pointer and the last random selection per student.
The current endpoint reads the saved pointer or falls back to the first active exercise.
An empty catalog returns a null exercise.
Selection mutations serialize through a per-student advisory lock.
Both sequence directions wrap.
Deleted pointers fall back safely.

Completion advances the saved pointer only once and only when it still identifies that exercise or an unavailable exercise.
The player remains on its current exercise until explicit navigation.
Next includes the displayed exercise ID, preventing a second advance after completion.
Random selection excludes the displayed exercise when alternatives exist.
It does not change the sequential pointer.
Random Previous uses validated IDs from the current page's history.

The browser starts each page in sequential mode.
Image-only exercises remain selectable but produce no listening session.
Manager previews remain outside student journaling.
Only students can use selection and event endpoints.

## Event lifecycle

Playback creates a client UUID and sends `start`.
The client sends heartbeats every 5 seconds by default, only while playing.
Pause flushes a heartbeat and keeps the same UUID.
Resume continues that session.
Crossing 90 % sends an immediate heartbeat.
Native `ended` sends a terminal event; replay uses a new UUID.

Next, Previous, mode changes, and logout finish the current session before their normal operation.
The player never starts audio automatically.
On `pagehide`, it pauses playback and submits a complete terminal event through `sendBeacon`.
A rejected beacon queue uses a keepalive request.
Delivery failures appear explicitly and pause active playback.
Exit delivery remains best-effort; no client can guarantee delivery after a crash or network loss.

Each event includes the UUID, exercise ID, audio ID, mode, event type, maximum position, and CSRF token.
Only this endpoint accepts the session-bound CSRF token in the JSON body.
Cookie authentication, active student permissions, and the exact Origin allowlist remain mandatory.
The body token is necessary because `sendBeacon` cannot set a custom header.
It never enters URLs, application logs, or local storage.
Other mutation endpoints retain their header-based token checks.

## Durable rows

An advisory lock serializes events for the same UUID.
The UUID has a unique database constraint.
The first accepted event creates the row, even when an end event arrives before start.
Later events cannot change its student, exercise, or audio identity.
Duplicate start cannot reopen a terminal session.
Lower positions never reduce the maximum.

The first event snapshots the exercise title, audio reference, and server-known duration.
Positions clamp to that duration.
Completion is monotonic: maximum position at least 90 % of duration, or an `ended` event.
The server records receipt timestamps; clients cannot supply arbitrary timestamps or durations.
Late heartbeats can update the maximum after end without reopening the session.
The first terminal receipt sets `ended_at`.

An existing session can finish after exercise deletion or audio replacement.
New sessions require an active exercise with current audio.
Versioned student audio URLs reject a replacement rather than serving different bytes during seeking.
The exercise, user, and audio foreign keys never cascade journal deletion.
No journal deletion API exists.

## Manager queries

Only managers can read journal rows and filter options.
Filters accept student ID, exercise ID, and timezone-aware start boundaries.
The lower time boundary is inclusive; the upper boundary is exclusive.
The UI converts inclusive local calendar dates into these UTC boundaries.
Pagination defaults to 50 rows and permits at most 100.
Rows sort by descending start time and ID.

Filter options include recorded students and exercises, including inactive accounts and deleted exercises.
Rows retain the original exercise title and duration while showing current student names.
No end event is a valid state, not proof of ongoing playback.
The UI does not invent a completion result for a lost tab.
