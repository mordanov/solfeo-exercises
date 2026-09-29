# Protected media storage

This document explains PHASE 2 uploads, conversion, retention, and authenticated file delivery.

Prerequisites:
- Read `api.md`, `auth.md`, and `env-variables.md`.
- Use the nginx container stand for playback and seeking.
- Install `file`, ffmpeg, and ffprobe for native media tests.

## Upload pipeline

Only managers submit exercise forms.
Every mutation requires the session cookie, allowed origin, and session-bound CSRF token.
The complete request has a configured byte limit before parsing.
Streaming requests without `Content-Length` have the same limit.
Separate image and audio limits apply while copying each upload.
Temporary files remain outside the public web root.

The `file` utility detects MIME types from signatures, not client filenames or headers.
Pillow verifies and decodes PNG, JPEG, and WebP images within the pixel limit.
The service keeps the original image bytes without resizing or recompression.
Audio signatures and supported container signatures pass to ffprobe.
ffprobe requires a positive finite duration and an audio stream.
Unsupported signatures, damaged inputs, and excessive duration return explicit error codes.

ffmpeg selects the first audio stream and removes video, metadata, and chapters.
It always encodes AAC in an MP4 container with fast-start metadata.
The pipeline checks the converted duration and size.
Only converted audio enters permanent storage.
External processes have deadlines and never use a shell.
The file protocol allowlist excludes network access.

Default limits are 20 MiB for images, 50 MiB for audio, 40 million pixels, and 1800 seconds.
The complete request limit is 71 MiB.
The browser reports byte-transfer progress, then shows processing until the server confirms persistence.
Do not close the page during processing.
After a connection failure, refresh the list before retrying to avoid duplicate creation.

## Persistence and retention

Compose mounts `media_data` at `/app/media`.
The backend owns this directory as UID 1000.
Generated UUID filenames contain no client-controlled path segments.
Files use mode `0644`; frontend nginx mounts the volume read-only.
No public static route mounts this volume.

The service prepares files before acquiring the exercise transaction lock.
It inserts media records before updating exercise foreign keys.
Failed transactions remove their newly prepared files.
The original exercise remains unchanged when validation or conversion fails.
A process crash can leave unreferenced files; no automatic deletion risks original images.
An operator must compare database references before any separate cleanup.

Soft deletion preserves the exercise and all files.
Replacing attachments also preserves old media records and files.
The API no longer exposes deleted exercises or superseded attachments.
Later journal operations can retain exercise foreign keys.
Do not remove `media_data` or use Compose `down --volumes` on persistent stands.

## Authenticated delivery

`GET` or `HEAD /api/exercises/{id}/files/{image|audio}` checks the current session and exercise.
The endpoint rejects inactive, expired, or revoked sessions.
It returns `X-Accel-Redirect` only for the current attachment of an active exercise.
The response includes the trusted MIME type and a generated inline filename.
FastAPI does not read file bytes for delivery.

nginx resolves the redirect through its `internal` location `/_protected_media/`.
Direct external requests to that location return 404.
Responses use `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`.
nginx supports normal, suffix, and unsatisfiable byte ranges.
Authenticated seeking returns 206 with `Content-Range`; invalid ranges return 416.
HEAD returns the file length without a body.
Student audio URLs include the selected media UUID as `version`.
A replaced attachment returns 404 for that old version instead of mixing audio bytes during seeking.
Existing journal rows keep their original audio reference and duration.

The shared TLS proxy disables request buffering only for the product route.
It delegates size enforcement to the private product nginx and preserves Range headers.
Prototype locations remain unchanged.
Native Vite does not implement internal redirects; use Compose to verify media delivery.
