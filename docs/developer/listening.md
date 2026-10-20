# Listening and journal

This document explains saved Chapter runs, playback events, persistence, and journal queries.

Prerequisites:
- Read `auth.md`, `api.md`, and `storage.md`.
- Apply migration `0013_exercise_chapters`.
- Use Chrome or Safari through the nginx stand.

## Chapter selection and saved runs

Managers assign each exercise to one numbered chapter.
The migration assigns existing exercises and listening sessions to Chapter 1.
Chapter numbers use a sequence and are not reused after deletion.

Students select one or more chapters that contain active exercises.
The backend samples up to 10 distinct exercises without replacement and saves a randomized order.
One active run per student stores chapter numbers, ordered items, status, and current position.
PostgreSQL enforces the active-run limit with a partial unique index.

The same run remains available after reload or sign-in on another device.
The player requires an explicit Resume action for an existing run.
Previous and Next update the saved position without starting playback.
The final Next action completes the run; Cancel ends it and allows a new sample.
Image-only exercises remain eligible and create no listening session without audio playback.
The old `student_progress` pointers remain in the schema but do not drive student selection.

## Event lifecycle

Playback creates a client UUID and sends `start`.
The client sends heartbeats every 5 seconds by default, only while playing.
Pause flushes a heartbeat and keeps the same UUID.
Resume continues that session.
Crossing 90 % sends an immediate heartbeat.
Native `ended` sends a terminal event; replay uses a new UUID.

Next, Previous, cancellation, and logout finish the current session before their normal operation.
The player never starts audio automatically.
On `pagehide`, it pauses playback and submits a complete terminal event through `sendBeacon`.
A rejected beacon queue uses a keepalive request.
Delivery failures appear explicitly and pause active playback.
Exit delivery remains best-effort; no client can guarantee delivery after a crash or network loss.

Each event includes the run ID, session UUID, exercise ID, audio ID, event type, maximum position, and CSRF token.
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

The first event snapshots the exercise title, chapter number, audio reference, and server-known duration.
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
Filters accept student ID, exercise ID, chapter number, and timezone-aware start boundaries.
The lower time boundary is inclusive; the upper boundary is exclusive.
The UI converts inclusive local calendar dates into these UTC boundaries.
Pagination defaults to 50 rows and permits at most 100.
Rows sort by descending start time and ID.

Filter options include recorded students and exercises, including inactive accounts and deleted exercises.
Chapter options combine current chapter numbers with historical session snapshots.
Rows retain the original exercise title, duration, and chapter number while showing current student names.
No end event is a valid state, not proof of ongoing playback.
The UI does not invent a completion result for a lost tab.
