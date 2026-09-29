# Phase plan

Rules for every phase:
- Work on ONE phase at a time. Do not start the next phase.
- Order inside a phase: plan -> failing tests -> code -> all checks green -> docs -> update STATUS.md -> stop.
- A phase is done only when: CI is green, the app is deployable, docs are updated, and the manual checklist passes.

---

## PHASE 0.5: Risk prototypes (throwaway code, in /prototypes)
Goal: find out early if the three risky parts work. Do not build product code here.

1. OMR: run Audiveris in Docker on 5-10 real exercise images (the owner provides them in /prototypes/omr/samples).
   Output: a table per image (recognized fully / partly / failed), the MusicXML, and a recommendation: continue, or change the engine.
2. Files: a minimal nginx + backend stand with X-Accel-Redirect and Range for an .m4a file.
   Output: curl commands and results for a Range request, and a manual Safari seek test checklist.
3. Audio ingestion: assess the Android PWA share target, then test the owner-approved Telegram replacement.
   PWA result: the real Android receiver gets an empty form; this path fails acceptance.
   Telegram result: the owner confirms receipt and successful playback of a real `.m4a` file.
   The owner confirms the remaining manual checks and closes PHASE 0.5 on 2026-09-29.
   Keep the failed PWA report; do not claim that Telegram success fixes PWA sharing.
   Output: the bot report, real-message checklist, and the replacement decision in `DECISIONS.md`.
Done when: the owner reads the report and confirms the decisions in DECISIONS.md.

## PHASE 0: Walking skeleton and CI/CD
- Monorepo layout. pre-commit (ruff, ruff-format, mypy, eslint, prettier, tsc). pyproject, package.json.
- FastAPI with `/api/health`. React page with i18n (ru, en, es) and the missing-key test.
- Postgres, Alembic (empty first migration), pydantic-settings, complete `.env.example`.
- Docker images for backend and frontend. Compose for dev and prod. nginx. Healthchecks.
- GitHub Actions: `ci.yml` (pre-commit, backend tests with a Postgres service, frontend tests) and `cd.yml` (build, push to GHCR, SSH deploy, alembic upgrade, healthcheck, rollback to the previous tag).
- Docs: developer setup, deploy guide (VPS prerequisites, GitHub secrets list, certbot and Let's Encrypt).
Done when: the health page opens on the VPS after a CD run, and CI is green.

## PHASE 1: Users, auth, settings
- Models and migrations: users, sessions. Endpoints: login, logout, me. Login rate limit. Password hashing.
- Emergency manager sync at startup, exactly as in the brief. Tests for all four cases.
- Manager UI: user list, create user, reset password, activate/deactivate, "must change password" flag.
- Settings page (all roles): language and note naming. Language change applies at once and persists on the server.
- Route guards on the frontend and permission dependencies on the backend. Tests for every boundary.
- Docs: user (login, settings, manage users), developer (auth, recovery with the emergency manager).
Done when: manager creates a student, the student logs in, changes the language, and cannot open manager pages.

## PHASE 2: Exercises and files
- Exercise model (soft delete, position, category). CRUD API. Reorder API. Validation: image or audio.
- Upload pipeline: size and magic-byte checks, ffmpeg to AAC (.m4a), duration, original image kept.
- Protected file serving with X-Accel-Redirect and Range.
- Manager UI: list, create, edit, delete, drag-and-drop reorder, upload with progress.
- Docs: user (manage exercises), developer (storage, conversion, nginx config).
Done when: manager uploads an .opus file and an image, and the audio plays and seeks in Chrome and Safari.

## PHASE 3: Listening module and journal
- Student UI: sequential mode (pointer per student), random mode (no immediate repeat), image and audio player, next/previous.
- Events API: start, heartbeat, end, beacon-safe. The "completed" rule.
- Manager journal UI with filters (student, exercise, date) and pagination.
- Tests: closed tab (no end event), deleted exercise in the journal, completed threshold at 90 %.
- Docs: user (student listening, manager journal), developer (event model).
Done when: a student listens to two exercises, closes the tab during the second, and the journal shows one completed and one incomplete session.

## PHASE 4: Telegram audio import
- Plan secure linking between Telegram sender IDs and active manager accounts before implementation.
- Receive private audio, voice, and document attachments through the Telegram bot.
- Reuse the PHASE 2 file pipeline, storage, and exercise operations.
- Let the manager create an exercise or attach audio to an existing exercise, with title and description.
- Persist import state and handle retries without duplicate files or exercises.
- Enforce manager permissions, including rejection of students, unknown senders, and deactivated managers.
- Test unauthorized input, unsupported files, size limits, conversion errors, retries, and restart recovery.
- Document the real Telegram flow and the WhatsApp file-transfer step, without requiring PWA installation.
- Keep secrets in `.env` and deploy the bot on the existing VPS without changing unrelated services.
Done when: an authorized manager imports real Telegram audio into an exercise and the saved audio plays correctly.
The PWA share target and browser share hand-off are no longer part of this phase.

## PHASE 5: OMR, review, rendering, note names
- Postgres job queue (SKIP LOCKED). Worker container with Audiveris behind the `OmrEngine` interface. Retries and failure state.
- On image upload: enqueue a job. Show status in the manager UI. Store MusicXML and status.
- Review screen: original image and rendered score side by side. Actions: Approve, Reject, Re-run.
- Student view: approved score rendered with OpenSheetMusicDisplay, otherwise the original image.
- "Show note names" toggle: inject `<lyric>` elements by the user's naming setting.
- Tests: queue concurrency, status transitions, lyric injection. Use 2-3 sample scores as fixtures.
- Docs: developer (OMR pipeline, limits, how to replace the engine), user (review a recognized score).
- Report the real recognition quality on the fixtures. Do not hide failures.
Done when: a real exercise image is recognized, approved, and shown with note names.

## PHASE 6: Spoken notes
- Script that generates syllable clips with OpenAI TTS for each language and naming. Commit the output.
- MusicXML -> note sequence parser (pitch, duration, rests, ties, accidentals). Unit tests.
- Web Audio scheduler: tempo slider, play/stop, highlight of the current note if OSMD allows.
- Docs: developer (regenerate the clips), user (use the spoken notes).
Done when: an approved score is spoken with correct note names and durations in all three languages.

## PHASE 7: Hardening and documentation review
- Security: cookie flags, CSRF, upload limits, nginx headers, dependency audit in CI.
- Log rotation, structured logs, worker healthcheck.
- Full documentation review against the rules in docs.instructions.md. Complete `.env` variable reference. Troubleshooting.
- Manual end-to-end smoke checklist for the full flow.
Done when: the smoke checklist passes on the VPS from a clean deploy.
