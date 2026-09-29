# Solfège Trainer: Copilot instructions

## Product
Web app for solfège homework. An exercise = sheet-music image and/or audio + text description.
Two roles:
- manager: manages exercises and users, resets passwords, reads the listening journal, reviews OMR results.
- student: listens to exercises (in order or random), changes own settings. Nothing else.

## Read first
- docs/PRODUCT_BRIEF.md: full requirements (OMR, journal, Telegram audio import, spoken notes).
- docs/PHASES.md: phase plan. Work on ONE phase at a time.
- docs/STATUS.md: current state. Update it at the end of every session.
- docs/DECISIONS.md: past decisions. Do not reverse them without asking.

## Fixed stack (do not change)
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x (typed), Alembic, PostgreSQL, pytest, ruff, mypy strict.
- Frontend: React, TypeScript, Vite, react-i18next, Vitest, Testing Library, ESLint, Prettier.
- Infra: nginx, Docker Compose. No Redis: the job queue is in Postgres (SELECT ... FOR UPDATE SKIP LOCKED).
- CI: GitHub Actions (pre-commit with ruff/mypy/eslint/prettier/tsc, backend tests, frontend tests).
  CD: build image, push to GHCR, deploy to VPS by SSH, alembic upgrade, healthcheck, rollback.
- Browsers: Chrome and Safari only. Backups are out of scope.

## Hard rules
- Config: ALL settings come from .env (pydantic-settings). Keep .env.example complete. No secrets in git.
- Emergency manager: on every backend start, if EMERGENCY_MANAGER_* variables are set, create/update
  that user (manager, active, password reset). If they are not set, deactivate the user with is_emergency=true.
- Auth: username + password, no email. Hash with bcrypt or scrypt (no Argon2, never plaintext).
  httpOnly session cookie, long lifetime, login rate limit.
- i18n: every UI string uses react-i18next. Languages: ru, en, es. A test fails if a key is missing.
  Backend returns error codes, not translated text.
- User settings (all roles): ui_language, note_naming (letters = C-D-E by default, or solfege = do-re-mi).
- Exercises: at least one of image or audio. Soft delete only (the journal must survive deletion).
- Files: never served directly. nginx X-Accel-Redirect after a backend auth check, with Range support.
  Check size and MIME (magic bytes). Convert all audio to AAC (.m4a) with ffmpeg. Always keep the original image.
- Journal: one row per listening session (start, heartbeat, end). A closed tab must still leave a valid row.
  completed = reached 90% of duration or "ended" event.
- OMR: async job (Audiveris behind an OmrEngine interface) -> MusicXML. Manager must approve.
  Students see the rendered score only if approved, otherwise the original image.
- Spoken notes: notes are spoken (not sung), with duration from the score. Pre-generated syllable clips, Web Audio API.

## Engineering rules
- Repo layout: /backend, /frontend, /worker, /deploy, /docs/user, /docs/developer, /.github/workflows.
- TDD: write the failing test first. Type hints everywhere. No `Any` without a comment.
- Small commits, Conventional Commits. Every phase leaves the app deployable and CI green.
- Do only the requested task. Do not refactor unrelated code. Do not add dependencies without saying why.
- When a requirement is unclear, ask. Do not guess.
- Update docs in the same phase as the feature. See .github/instructions/docs.instructions.md.

## Session protocol
1. Plan first (checklist, assumptions, questions). Wait for approval.
2. One task at a time: failing tests, code, all checks green, commit, then STOP.
3. At the end: update docs/STATUS.md and list what I must verify manually.
