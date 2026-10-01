# Solfège Trainer: product brief

This file is the full requirement set. When it conflicts with a decision in DECISIONS.md, DECISIONS.md wins.

## Purpose
A web app for solfège homework. An exercise = sheet-music image and/or audio file + text description.
A child looks at the notes and listens to the audio.

## Roles
- manager: manages exercises (add/edit/delete/reorder), manages users (create, reset password, deactivate), reads the listening journal.
- student: can only listen to exercises (in order, or random) and change own settings.

## Stack (fixed, do not change)
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x (typed), Alembic, PostgreSQL, pytest, ruff, mypy (strict).
- Frontend: React + TypeScript + Vite, react-i18next, Vitest + Testing Library, ESLint, Prettier.
- Infra: nginx (reverse proxy, TLS, serves protected files via X-Accel-Redirect), Docker Compose.
- Workers: OMR worker container (Audiveris, Java) + a Postgres-based job queue (SELECT ... FOR UPDATE SKIP LOCKED). No Redis.
- CI/CD: GitHub Actions. CI = pre-commit (ruff, ruff-format, mypy, eslint, prettier, tsc) + backend unit tests + frontend unit tests.
  CD = build Docker images -> push to GHCR -> deploy to VPS via SSH (docker compose pull/up, alembic upgrade, healthcheck, rollback to previous tag on failure).
- Target browsers: Chrome and Safari only. Backups are OUT OF SCOPE.

## Configuration
- ALL settings live in .env (pydantic-settings). Keep .env.example complete and documented. No secrets in git.
- Emergency manager: EMERGENCY_MANAGER_USERNAME / EMERGENCY_MANAGER_PASSWORD (plus first/last name).
  On EVERY backend start:
  - If both variables are set: create or update this user (role=manager, active, password reset to the .env value, flag is_emergency=true).
  - If they are not set: the user with is_emergency=true is deactivated (cannot log in).
  This is the first-user mechanism AND the disaster-recovery mechanism.

## Users and auth
- User: username (unique login), first_name, last_name, role (manager|student), password, is_active, is_emergency, settings.
- No email. Simple username+password. Hash passwords with a standard library scheme (bcrypt via passlib, or hashlib.scrypt). Never store plaintext. No Argon2.
- Session: httpOnly, Secure, SameSite=Lax cookie with a server-side session token, sliding expiry, long lifetime (env-configurable, default 90 days).
  The web application retains its session on mobile browsers.
- Login rate limit (per username+IP) in backend, plus nginx limit_req on /api/auth/login.
- Manager can create users and reset passwords. Optional flag "must change password on next login".
- Per-user settings (available to every role, stored on server): ui_language (ru|en|es), note_naming (letters|solfege). Defaults: env DEFAULT_LANGUAGE, note_naming=letters (C-D-E).

## i18n
- Every UI string goes through react-i18next. Ship ru, en, es from day one. A test must fail if any key is missing in any language.
- Backend returns stable error codes (not translated text); frontend translates them.

## Exercises
- Fields: id, title, description (text), category/level (optional string), position (integer, manager can reorder), image (optional), audio (optional), score (optional, see OMR), deleted_at (soft delete).
- Validation: at least one of image or audio is required.
- Soft delete only. The journal must keep working for deleted exercises.
- Student progress: per-student "next exercise" pointer for sequential mode. Random mode never repeats the immediately previous exercise (if more than one exists).

## Files
- Stored on a Docker volume. Never served directly. nginx internal location + X-Accel-Redirect after backend auth check. Range requests must work (audio seeking in Safari).
- Upload checks: size limits from .env, MIME check by magic bytes (not by extension or client header), allowed types only.
- Audio: accept anything ffmpeg can read (WhatsApp/Telegram .opus/.ogg/.m4a/.mp3/.wav/.aac). Always convert to AAC in an MP4 container (.m4a, audio/mp4). Keep only the converted file. Store duration in seconds.
- Images: png/jpeg/webp. Keep the ORIGINAL image always (needed for OMR review and as fallback).

## Listening journal
- One row per listening session: id, user_id, exercise_id, session_id (uuid from client), started_at, last_heartbeat_at, ended_at (nullable), max_position_sec, audio_duration_sec, completed (bool).
- Client sends: start, heartbeat every 5 s while playing, end. Also navigator.sendBeacon on pagehide.
- completed = max_position_sec >= 90% of duration OR the "ended" event. A closed tab must still leave a valid row.
- Only managers can read the journal (filter by student, exercise, date; pagination).

## OMR (part of MVP)
- On image upload, enqueue an OMR job. Worker runs Audiveris in batch mode -> MusicXML. Engine sits behind a Python interface (OmrEngine) so it can be replaced (for example by oemer).
- Score status: none | pending | processing | needs_review | approved | rejected | failed.
- Manager reviews: original image and rendered score side by side; actions Approve / Reject / Re-run.
- Students see the rendered score ONLY if status = approved. Otherwise they see the original image.
- Rendering: OpenSheetMusicDisplay in the browser.
- Toggle "show note names" on the staff: client-side, inject <lyric> elements into the MusicXML before rendering. Naming from user setting (letters: C D E F G A B; solfege: do re mi fa sol la si; localized).
- Assumptions: printed, monophonic, single-staff exercises. Complex scores may fail; the fallback (image) covers this.

### Photo quality requirements
A low-quality photo is the main cause of OMR errors. Follow these rules before upload:
- Frame one exercise only. Two staff systems in one photo can look like a second movement to the engine.
- Keep the page flat. Avoid page curl and camera angle. A curved or tilted staff often fails staff detection.
- Use even, direct light. Avoid shadows and glare. Low contrast between ink and paper hides the staff lines.
- Take the photo in focus. Keep noteheads separate. A blurry or noisy photo can look like extra chords.
- Check every note, rest, and measure before approval, even for a clear photo. The engine can still misread notes.
- Reject a score with a wrong note, a missing measure, or an extra chord. Reshoot the image instead.
- The spoken notes feature also refuses a score with these errors. It reports code `SPOKEN_UNSUPPORTED_SCORE`.

## Spoken notes
- Not singing. Notes are SPOKEN (do-re-mi or C-D-E per user setting and UI language).
- Note duration is respected: whole note = long, quarter = short, etc., from MusicXML durations and a tempo (default 72 bpm, user-adjustable slider).
- Implementation: pre-generated syllable clips (script calls OpenAI TTS once, output committed to frontend/public/solfege/<lang>/<naming>/), played with Web Audio API. Fit each note to its duration (playbackRate clamped to a sane range, silence for the rest). Rests = silence. Sharps/flats = extra suffix clip.
- Available only when score status = approved.

## Telegram audio import

The owner replaces PWA audio sharing with a Telegram bot on 2026-09-29.
The web application remains the interface for exercises, users, listening, and the journal.
Product delivery no longer requires an Android share target, IndexedDB share hand-off, or PWA installation.

- A manager sends or forwards an audio attachment to the bot in a private Telegram chat.
- Accept `audio`, `voice`, and audio sent as `document`; text or a link alone is not an audio file.
- Authorize the Telegram sender against an active manager before accepting an import.
- Students and unknown senders cannot create exercises or attach files through the bot.
- Reuse the product file pipeline: size limits, magic-byte checks, AAC `.m4a` conversion, duration, and protected storage.
- Preserve the manager's choice: create an exercise or attach audio to an existing exercise, with title and description.
- Confirm completion only after persistence; retries must not duplicate imported files or exercises.
- Keep tokens and configuration in `.env`; do not expose tokens or received media in logs or public URLs.
- Document the hosted Telegram API download limit and reject oversized attachments explicitly.
- For WhatsApp audio, transfer the actual file into Telegram or save it before attaching it to the bot.
- Select the manager-account linking method and import interaction during PHASE 4 planning.

The risk prototype's numeric sender allowlist is not a replacement for product role checks.
The bot does not replace website login or grant manager access by Telegram username.
The failed PWA prototype remains historical evidence, not an acceptance requirement for the replacement flow.
