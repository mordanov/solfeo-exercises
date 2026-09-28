---
applyTo: "backend/**,worker/**"
---

# Backend rules

## Language and tooling
- Python 3.12. Use type hints on every function, method, and variable that is not obvious.
- mypy runs in strict mode. Do not add `# type: ignore` or `Any` without a comment that explains why.
- ruff for lint and format. Fix all warnings. Do not disable a rule globally.
- Dependencies: add to pyproject.toml with a pinned range. Say why in the commit message.

## Structure
- Layers: `api/` (routers, request/response schemas) -> `services/` (business logic) -> `repositories/` or `models/` (database).
- Routers contain no business logic. Services do not import FastAPI.
- One Pydantic schema per input and per output. Never return ORM objects directly.
- Configuration: only through one `Settings` class (pydantic-settings). Never call `os.environ` elsewhere.

## Database
- SQLAlchemy 2.x typed style (`Mapped[...]`, `mapped_column`). Use async or sync consistently, as decided in docs/DECISIONS.md.
- Every schema change has an Alembic migration. Migrations must run on an empty database and on the previous release.
- Exercises use soft delete (`deleted_at`). Journal rows keep a foreign key to the exercise. Never cascade delete journal rows.
- Job queue: table in Postgres. Claim jobs with `SELECT ... FOR UPDATE SKIP LOCKED`. A job has status, attempts, last_error, locked_at.

## API
- Errors: return a stable machine code, for example `{"error": "USERNAME_TAKEN"}`. Do not return translated text.
- Every endpoint has an explicit permission dependency (`require_manager`, `require_student_or_manager`). No endpoint is public except login and health.
- State-changing endpoints require the CSRF protection chosen in docs/DECISIONS.md.
- Protected files: the endpoint checks permission, then answers with `X-Accel-Redirect`. It never reads the file into memory.

## Security
- Password hash: bcrypt or scrypt. Never log passwords, tokens, or cookies.
- Login rate limit per username and IP.
- Upload: check size, then detect type by magic bytes. Reject all other types. Use generated file names, never client names.
- Run ffmpeg and Audiveris with a timeout and without a shell (`subprocess.run([...], shell=False)`).

## Tests
- TDD: write the failing test first, then the code.
- pytest. Unit tests for services. API tests with a real Postgres (service container in CI), not SQLite.
- Test every permission boundary: student cannot call manager endpoints, anonymous cannot call any protected endpoint.
- Test the emergency manager sync: created, password reset, deactivated when variables are removed, created again.
- Mock only external systems (OpenAI, Audiveris binary). Do not mock the database.
