# Exercise Chapters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add manager-created numbered chapters and saved randomized listening runs of up to 10 exercises.

**Architecture:** Store chapters, runs, selected chapter snapshots, and ordered run items in PostgreSQL. Keep listening journal rows per audio session and snapshot the chapter number on each row. Use manager and student APIs with the existing role, CSRF, localization, and file-access boundaries.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, React, TypeScript, TanStack Query, react-i18next, pytest, Vitest.

---

Purpose: Guide implementation of the approved chapter-based listening design.

Prerequisites:
- Review `docs/superpowers/specs/2026-10-19-exercise-chapters-design.md`.
- Use a disposable PostgreSQL database named `solfeo_test` for backend tests.
- Keep the existing staged and untracked owner files unchanged.

## Assumptions and contracts

- The student role listens to exercises. The game-only player role receives no exercise access.
- A manager creates numbered chapters. The app assigns the next unused number and never reuses numbers.
- A chapter contains active or soft-deleted exercises. The manager can delete it only when none remain assigned.
- A student selects one or more chapters. The backend samples at most 10 active exercises without replacement and saves the sample's randomized order.
- One active run exists per student. The server stores the queue and current index for cross-device resume.
- A run ends after its last item. A student must cancel it before choosing new chapters.
- Keep image-only exercises eligible. Do not create a journal row unless audio playback starts.
- Preserve the optional exercise category and manager exercise ordering.
- Do not add dependencies or change OMR, protected files, spoken notes, or journal granularity.
- If a queued exercise becomes soft-deleted, skip it. Keep its existing journal history.
- A listening-session row snapshots the chapter number from the run item, not the exercise's later chapter assignment.

## File map

| File | Responsibility |
|---|---|
| `backend/app/models/__init__.py` | Chapter, listening-run, run-item, exercise, and journal models |
| `backend/migrations/versions/0013_exercise_chapters_and_listening_runs.py` | Seed Chapter 1, create the never-reused chapter-number sequence, backfill rows, and create run tables |
| `backend/app/services/chapters.py` | Chapter listing, creation, numbering, and empty-only deletion |
| `backend/app/api/chapters.py` | Manager chapter endpoints and explicit schemas |
| `backend/app/services/exercises.py` | Require a chapter on exercise creation and update |
| `backend/app/api/exercises.py` | Chapter input and output fields |
| `backend/app/services/listening_runs.py` | Run creation, randomized sampling, navigation, resume, and cancellation |
| `backend/app/api/listening_runs.py` | Student run endpoints and explicit schemas |
| `backend/app/api/listening.py` | Run-bound journal events and chapter-filtered journal endpoints |
| `backend/app/main.py` | Register new API routers |
| `backend/tests/test_database.py` | Empty-database and previous-release migration checks |
| `backend/tests/test_exercises.py` | Chapter assignment and manager boundaries |
| `backend/tests/test_listening.py` | Run lifecycle, journal snapshots, and student boundaries |
| `backend/tests/test_chapters.py` | New chapter endpoint and service tests |
| `backend/tests/test_listening_runs.py` | New run service and API tests |
| `frontend/src/api/chapters.ts` | Typed chapter client and response parsing |
| `frontend/src/api/chapters.test.ts` | Chapter response parsing and API requests |
| `frontend/src/api/listeningRuns.ts` | Typed run client and response parsing |
| `frontend/src/api/listeningRuns.test.ts` | Run response parsing and API requests |
| `frontend/src/api/exercises.ts` | Exercise chapter fields |
| `frontend/src/api/listening.ts` | Run-bound listening event type |
| `frontend/src/api/journal.ts` | Chapter filter and chapter options |
| `frontend/src/api/journal.test.ts` | Journal chapter query and parsing tests |
| `frontend/src/features/exercises/Exercises.tsx` | Chapter assignment in exercise forms |
| `frontend/src/features/exercises/Exercises.test.tsx` | Exercise form chapter behavior |
| `frontend/src/features/exercises/ChapterManager.tsx` | Manager chapter creation and deletion controls |
| `frontend/src/features/exercises/ChapterManager.test.tsx` | Manager chapter controls |
| `frontend/src/features/listening/Listening.tsx` | Replace sequential/random selection with run flow |
| `frontend/src/features/listening/Listening.test.tsx` | Chapter selection, resume, navigation, and cancellation |
| `frontend/src/features/listening/tracker.ts` | Attach run identity to each listening event |
| `frontend/src/features/listening/tracker.test.ts` | Preserve event delivery and run identity |
| `frontend/src/features/journal/Journal.tsx` | Chapter filter and chapter column |
| `frontend/src/features/journal/Journal.test.tsx` | Journal chapter filter behavior |
| `frontend/src/i18n/locales/{en,ru,es}.json` | Matching translated chapter, run, and error strings |
| `docs/PRODUCT_BRIEF.md`, `docs/PHASES.md`, `docs/DECISIONS.md` | Record product requirements and the approved behavior change |
| `docs/user/manager.md`, `docs/user/student.md` | Explain chapter management and student runs |
| `docs/developer/data-model.md`, `docs/developer/api.md`, `docs/developer/listening.md` | Document schema, endpoints, and run lifecycle |
| `docs/developer/glossary.md`, `CONTEXT.md`, `docs/STATUS.md` | Keep project terms and session status current |

## Task 1: Define backend and frontend contracts

**Files:**
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/services/chapters.py`
- Create: `backend/app/services/listening_runs.py`
- Create: `backend/app/api/chapters.py`
- Create: `backend/app/api/listening_runs.py`
- Modify: `backend/app/api/exercises.py`
- Modify: `backend/app/api/listening.py`
- Create: `frontend/src/api/chapters.ts`
- Create: `frontend/src/api/listeningRuns.ts`

- [ ] **Step 1: Define the database and API shapes without behavior**

Define the SQLAlchemy fields before adding service logic:

```python
from typing import Literal

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, Field, field_validator

class Chapter(Base):
    __tablename__ = "chapters"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(unique=True)

class ListeningRun(Base):
    __tablename__ = "listening_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(10))
    current_index: Mapped[int] = mapped_column(default=0)

class ListeningRunChapter(Base):
    __tablename__ = "listening_run_chapters"
    __table_args__ = (UniqueConstraint("run_id", "chapter_number"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("listening_runs.id"))
    chapter_number: Mapped[int]

class ListeningRunItem(Base):
    __tablename__ = "listening_run_items"
    __table_args__ = (
        UniqueConstraint("run_id", "position"),
        UniqueConstraint("run_id", "exercise_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("listening_runs.id"))
    position: Mapped[int]
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    chapter_number: Mapped[int]
```

Add `Exercise.chapter_id` as a non-null foreign key. Add `ListeningSession.chapter_number` as a required snapshot. Constrain run status to `active`, `completed`, or `cancelled`.

Define these Pydantic shapes in the API modules. Reuse `ExerciseOutput` from `backend/app/api/exercises.py`:

```python
RunStatus = Literal["active", "completed", "cancelled"]

class ChapterOutput(BaseModel):
    id: int
    number: int
    active_exercise_count: int
    assigned_exercise_count: int

class ChapterListOutput(BaseModel):
    chapters: list[ChapterOutput]

class RunStartInput(Input):
    chapter_ids: list[int] = Field(min_length=1)

    @field_validator("chapter_ids")
    @classmethod
    def unique_positive_chapters(cls, value: list[int]) -> list[int]:
        if any(chapter_id <= 0 for chapter_id in value):
            raise ValueError("INVALID_CHAPTER_ID")
        if len(set(value)) != len(value):
            raise ValueError("DUPLICATE_CHAPTER_ID")
        return value

class RunNavigationInput(Input):
    direction: Literal["next", "previous"]

class RunItemOutput(BaseModel):
    position: int
    chapter_number: int
    exercise: ExerciseOutput

class ListeningRunOutput(BaseModel):
    id: int
    status: RunStatus
    chapter_numbers: list[int]
    current_index: int
    items: list[RunItemOutput]

class JournalChapterOption(BaseModel):
    chapter_number: int
```

Define the final event input without `mode`:

```python
class RunEventInput(Input):
    run_id: int = Field(gt=0)
    session_id: UUID
    exercise_id: int = Field(gt=0)
    audio_id: UUID | None = None
    event: listening.Event
    position_seconds: float = Field(ge=0, allow_inf_nan=False)
    csrf_token: str = Field(min_length=1, max_length=128, repr=False)
```

Require at least 1 unique positive `chapter_id` in exercise create and update inputs. Return `chapter_id` and `chapter_number` in exercise outputs. Keep the existing event handler unchanged until Task 5. Add `chapter_number` to journal rows and filters. Add `chapters: list[JournalChapterOption]` to the existing manager journal options response. Validate that run input contains at least 1 unique positive chapter ID.

Add matching `Chapter`, `ListeningRun`, and run-status TypeScript types to the new API modules. Keep existing frontend parsers unchanged until Task 6.

- [ ] **Step 2: Define service signatures before implementation**

Define these exact typed service boundaries:

- `list_chapters(session: Session, *, nonempty_only: bool) -> list[Chapter]`
- `create_chapter(session: Session) -> Chapter`
- `delete_chapter(session: Session, chapter_id: int) -> None`
- `active_run(session: Session, user_id: int) -> ListeningRun | None`
- `start_run(session: Session, user_id: int, chapter_ids: list[int]) -> ListeningRun`
- `move_run(session: Session, user_id: int, direction: Literal["next", "previous"]) -> ListeningRun`
- `cancel_run(session: Session, user_id: int) -> ListeningRun`

Add these typed declarations to the new service modules:

```python
# Import Session from sqlalchemy.orm, Chapter and ListeningRun from app.models,
# and Literal from typing.
def list_chapters(session: Session, *, nonempty_only: bool) -> list[Chapter]:
    raise NotImplementedError

def create_chapter(session: Session) -> Chapter:
    raise NotImplementedError

def delete_chapter(session: Session, chapter_id: int) -> None:
    raise NotImplementedError

def active_run(session: Session, user_id: int) -> ListeningRun | None:
    raise NotImplementedError

def start_run(
    session: Session, user_id: int, chapter_ids: list[int]
) -> ListeningRun:
    raise NotImplementedError

def move_run(
    session: Session, user_id: int, direction: Literal["next", "previous"]
) -> ListeningRun:
    raise NotImplementedError

def cancel_run(session: Session, user_id: int) -> ListeningRun:
    raise NotImplementedError
```

Replace each stub with behavior only in its implementation task.

- [ ] **Step 3: Define the TypeScript response contracts**

Add exported types before implementing network calls:

```ts
import type { Exercise } from "./exercises";

export type RunStatus = "active" | "completed" | "cancelled";

export type Chapter = {
  id: number;
  number: number;
  active_exercise_count: number;
  assigned_exercise_count: number;
};

export type RunStartRequest = { chapter_ids: number[] };
export type ChapterExercise = Exercise & {
  chapter_id: number;
  chapter_number: number;
};

export type ListeningRun = {
  id: number;
  status: RunStatus;
  chapter_numbers: number[];
  current_index: number;
  items: Array<{
    position: number;
    chapter_number: number;
    exercise: ChapterExercise;
  }>;
};
```

- [ ] **Step 4: Run backend and frontend type checks**

Run: `uv run --locked mypy --config-file pyproject.toml`
Expected: PASS with contracts only.

Run: `npm run typecheck --workspace frontend`
Expected: PASS with exported types and no new behavior.

## Task 2: Write and run failing migration and chapter tests

**Files:**
- Modify: `backend/tests/test_database.py`
- Create: `backend/tests/test_chapters.py`
- Modify: `backend/tests/test_exercises.py`

- [ ] **Step 1: Add the migration backfill test**

Add `test_chapter_migration_backfills_exercises_and_listening_rows` to `test_database.py`. Reset the disposable database to base and upgrade it to `0012_player_role`. Insert a student user with all required columns, a media row with a UUID, filename, MIME type, and positive size, and 2 exercises with titles and distinct positions that reference the media as audio. Set `deleted_at` only on the second exercise. Insert a listening row for the first exercise with UUIDs, an exercise title, start and heartbeat timestamps, duration `1`, position `0`, and `completed=False`. Upgrade to head. Assert that the migration creates Chapter 1, assigns both exercises to it, and stores journal chapter number 1. Extend the existing empty-database migration test to assert that Chapter 1 exists after a fresh upgrade. Update every head-revision expectation to `0013_exercise_chapters_and_listening_runs` and assert that revision's parent is `0012_player_role`.

- [ ] **Step 2: Add chapter API tests**

Test manager creation returns the next stable number, list ordering, refusal to delete a chapter with active or soft-deleted exercises, and student/player access boundaries. Reject create and delete requests without valid CSRF tokens. Test that deleting an empty chapter does not allow its number to be reused.

- [ ] **Step 3: Add exercise assignment tests**

Test that manager create and update require a valid chapter. Test that exercise output returns the chapter ID and number. Test that deleting an exercise does not remove its chapter relation.

- [ ] **Step 4: Add guarded downgrade tests**

Verify that an empty Chapter 1 schema downgrades safely. Verify that an additional chapter or any listening-run record blocks downgrade with the stable migration error code.

- [ ] **Step 5: Run the focused tests and confirm failure**

Run: `cd backend && pytest -q tests/test_database.py tests/test_chapters.py tests/test_exercises.py`
Expected: FAIL because the migration and chapter behavior are not implemented.

## Task 3: Implement chapter persistence and migration

**Files:**
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/0013_exercise_chapters_and_listening_runs.py`
- Modify: `backend/tests/test_database.py`

- [ ] **Step 1: Create the migration**

Create the chapter table, seed number 1, and create `chapter_number_seq` starting at 2. Use the sequence so deleted numbers are never reused. Add nullable exercise and journal chapter columns, backfill all existing rows, then make exercise ownership non-null. Create the run, selected-chapter, and ordered-item tables. Add unique chapter number, unique item position and exercise per run, and a partial unique index for one active run per student.

- [ ] **Step 2: Add safe downgrade behavior**

Permit downgrade when the database contains only Chapter 1 and no run records. Raise a stable migration error if the downgrade would discard additional chapter assignments or any run records.

- [ ] **Step 3: Match SQLAlchemy metadata to the migration**

Use typed `Mapped[...]` fields and named constraints. Add indexes for student active-run lookup, chapter membership, run item order, and journal chapter filtering.

- [ ] **Step 4: Run migration tests**

Run: `cd backend && pytest -q tests/test_database.py`
Expected: PASS for empty upgrade, previous-release backfill, repeat upgrade, metadata parity, and guarded downgrade.

- [ ] **Step 5: Commit the schema change**

```bash
git add backend/app/models/__init__.py backend/migrations/versions/0013_exercise_chapters_and_listening_runs.py backend/tests/test_database.py
git commit -m "feat(database): add exercise chapters and listening runs" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 4: Implement manager chapter and exercise APIs

**Files:**
- Modify: `backend/app/services/chapters.py`
- Modify: `backend/app/api/chapters.py`
- Modify: `backend/app/services/exercises.py`
- Modify: `backend/app/api/exercises.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_chapters.py`
- Modify: `backend/tests/test_exercises.py`

- [ ] **Step 1: Add failing chapter service and endpoint tests**

Test `GET /api/chapters`, `POST /api/chapters`, and `DELETE /api/chapters/{id}`. Verify automatic numbering uses the next unused number and does not reuse deleted numbers.

- [ ] **Step 2: Verify the tests fail**

Run: `cd backend && pytest -q tests/test_chapters.py`
Expected: FAIL because the service functions are still stubs and the router has no chapter endpoints.

- [ ] **Step 3: Implement chapter service behavior**

Use `nextval('chapter_number_seq')` to allocate a permanent number. Reject deletion while any active or soft-deleted exercise remains assigned. Return stable errors for missing chapters and non-empty chapters. Rely on the exercise foreign key to prevent a concurrent assignment from racing with deletion.

- [ ] **Step 4: Implement manager chapter routes**

Add explicit input and output schemas. Require `Manager` and CSRF for create and delete. Register the router in `backend/app/main.py`.

- [ ] **Step 5: Add required exercise ownership**

Add `chapter_id` to multipart input and exercise output. Validate the chapter before media preparation and persist the assignment in the existing exercise transaction.

- [ ] **Step 6: Run backend chapter and exercise tests**

Run: `cd backend && pytest -q tests/test_chapters.py tests/test_exercises.py`
Expected: PASS, including manager-only mutation and invalid chapter rejection.

- [ ] **Step 7: Commit chapter management**

```bash
git add backend/app/services/chapters.py backend/app/api/chapters.py backend/app/services/exercises.py backend/app/api/exercises.py backend/app/main.py backend/tests/test_chapters.py backend/tests/test_exercises.py
git commit -m "feat(exercises): assign exercises to numbered chapters" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 5: Implement saved listening-run behavior

**Files:**
- Modify: `backend/app/services/listening_runs.py`
- Modify: `backend/app/api/listening_runs.py`
- Modify: `backend/app/api/listening.py`
- Modify: `backend/app/services/listening.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_listening_runs.py`
- Modify: `backend/tests/test_listening.py`

- [ ] **Step 1: Add failing run service tests**

Test one active run per student, stale chapter validation, all items when the pool has at most 10 exercises, a distinct 10-item sample from larger pools, fixed saved order after reload, and empty chapter selection rejection. Include active and soft-deleted exercises, and include an image-only exercise.

- [ ] **Step 2: Run the service tests and confirm failure**

Run: `cd backend && pytest -q tests/test_listening_runs.py`
Expected: FAIL because run service behavior does not exist.

- [ ] **Step 3: Implement run creation and resume**

Lock the student row before looking up or creating a run. Lock the run row during navigation and cancellation. Validate all selected chapter IDs. Gather active exercises from the selected chapters and sample them with `secrets.SystemRandom().sample(ids, k=min(10, len(ids)))`.

```python
selected = secrets.SystemRandom().sample(
    exercise_ids, k=min(10, len(exercise_ids))
)
```

Use the sample result as the saved randomized order, including when it samples the full pool. Return the existing active run on a repeated start request. Reject stale or unavailable chapter IDs with stable error codes. Reject a selection that has no active exercises.

- [ ] **Step 4: Implement navigation and cancellation**

Move the saved index within the queue. Keep Previous at the first item. Mark the run completed after Next passes the last item. Mark the run cancelled after the student requests cancellation. Skip soft-deleted queue items without exposing their metadata or files. Mark the run completed if every remaining item is soft-deleted. Add a regression test for that case.

- [ ] **Step 5: Add student API routes**

Add `GET /api/listening/chapters`, `GET /api/listening/run`, `POST /api/listening/run`, `POST /api/listening/run/{run_id}/navigate`, and `POST /api/listening/run/{run_id}/cancel`. Replace and remove the old `/api/listening/current` and `/api/listening/select` routes. Return `null` from the active-run endpoint when no run exists. Require the student role on every route and CSRF on mutations.

- [ ] **Step 6: Bind listening events to the active run**

Require `run_id` on student listening events and remove the old `mode` field. Validate that the run belongs to the student and the exercise matches its current run item. Snapshot that item's chapter number on the first journal event. Remove sequential-pointer advancement from event recording. Remove the old current/choose service functions and their selection types. Retain the old progress columns without using them for student selection.

- [ ] **Step 7: Test cancellation, journal, and boundaries**

Verify that cancellation ends active playback without deleting its journal row. Preserve the existing 90 % and natural-ended completion rules. Test CSRF on run mutations, foreign-student run IDs, player access, stale items, idempotent events, concurrent navigation, and removal of the old selection routes.

- [ ] **Step 8: Run focused backend tests**

Run: `cd backend && pytest -q tests/test_listening_runs.py tests/test_listening.py tests/test_chapters.py tests/test_exercises.py`
Expected: PASS against disposable PostgreSQL.

- [ ] **Step 9: Commit listening runs**

```bash
git add backend/app/services/listening_runs.py backend/app/api/listening_runs.py backend/app/api/listening.py backend/app/services/listening.py backend/app/main.py backend/tests/test_listening_runs.py backend/tests/test_listening.py
git commit -m "feat(listening): add resumable randomized chapter runs" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 6: Implement typed frontend API clients

**Files:**
- Create: `frontend/src/api/chapters.ts`
- Create: `frontend/src/api/chapters.test.ts`
- Create: `frontend/src/api/listeningRuns.ts`
- Create: `frontend/src/api/listeningRuns.test.ts`
- Create: `frontend/src/api/journal.test.ts`
- Modify: `frontend/src/api/exercises.ts`
- Modify: `frontend/src/api/listening.ts`
- Modify: `frontend/src/api/journal.ts`

- [ ] **Step 1: Add failing parser and request tests**

Test valid chapter and run responses, malformed response rejection, selected chapter request bodies, navigation direction, cancellation, and journal chapter filter serialization.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `npm run test --workspace frontend -- src/api/chapters.test.ts src/api/listeningRuns.test.ts`
Expected: FAIL because the contract modules do not yet export API client functions.

- [ ] **Step 3: Implement chapter and run API clients**

Use `request` and `ApiError` from `frontend/src/api/auth.ts`. Parse every response field; reject invalid status, ID, chapter number, index, and exercise data with `INVALID_RESPONSE`.

- [ ] **Step 4: Update exercise, event, and journal clients**

Parse the required exercise chapter fields. Replace listening event `mode` with `run_id`. Remove the old current/select client functions. Add chapter number to journal entries and options. Serialize `chapter_number` in the journal filter query.

- [ ] **Step 5: Run API client tests**

Run: `npm run test --workspace frontend -- src/api/chapters.test.ts src/api/listeningRuns.test.ts src/api/listening.test.ts src/api/journal.test.ts`
Expected: PASS for API request and response behavior.

- [ ] **Step 6: Commit the typed API clients**

```bash
git add frontend/src/api/chapters.ts frontend/src/api/chapters.test.ts frontend/src/api/listeningRuns.ts frontend/src/api/listeningRuns.test.ts frontend/src/api/exercises.ts frontend/src/api/listening.ts frontend/src/api/journal.ts frontend/src/api/journal.test.ts
git commit -m "feat(frontend): add chapter and listening run clients" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 7: Implement manager chapter controls

**Files:**
- Create: `frontend/src/features/exercises/ChapterManager.tsx`
- Create: `frontend/src/features/exercises/ChapterManager.test.tsx`
- Modify: `frontend/src/features/exercises/Exercises.tsx`
- Modify: `frontend/src/features/exercises/Exercises.test.tsx`
- Modify: `frontend/src/i18n/locales/en.json`
- Modify: `frontend/src/i18n/locales/ru.json`
- Modify: `frontend/src/i18n/locales/es.json`

- [ ] **Step 1: Add failing component tests**

Verify manager chapter creation, translated numbered labels, deletion of an empty chapter, disabled deletion for a chapter with exercises, and chapter selection in create and edit forms.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `npm run test --workspace frontend -- src/features/exercises/ChapterManager.test.tsx src/features/exercises/Exercises.test.tsx`
Expected: FAIL because chapter controls do not exist.

- [ ] **Step 3: Implement chapter controls and exercise assignment**

Use TanStack Query for chapter data and existing `ExerciseForm` patterns. Disable save until the manager selects a chapter. Keep category input and global manager exercise ordering unchanged.

- [ ] **Step 4: Add translated strings**

Add identical non-empty keys to all three locale files. Use “Chapter”, “Глава”, and “Unidad” with the stable number.

- [ ] **Step 5: Run manager UI and localization tests**

Run: `npm run test --workspace frontend -- src/features/exercises/ChapterManager.test.tsx src/features/exercises/Exercises.test.tsx src/i18n/locales.test.ts`
Expected: PASS.

- [ ] **Step 6: Commit manager chapter controls**

```bash
git add frontend/src/features/exercises/ChapterManager.tsx frontend/src/features/exercises/ChapterManager.test.tsx frontend/src/features/exercises/Exercises.tsx frontend/src/features/exercises/Exercises.test.tsx frontend/src/i18n/locales/en.json frontend/src/i18n/locales/ru.json frontend/src/i18n/locales/es.json
git commit -m "feat(frontend): manage chapters with exercises" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 8: Replace student mode selection with saved runs

**Files:**
- Modify: `frontend/src/features/listening/Listening.tsx`
- Modify: `frontend/src/features/listening/Listening.test.tsx`
- Modify: `frontend/src/features/listening/tracker.ts`
- Modify: `frontend/src/features/listening/tracker.test.ts`
- Modify: `frontend/src/api/listening.ts`
- Modify: `frontend/src/i18n/locales/en.json`
- Modify: `frontend/src/i18n/locales/ru.json`
- Modify: `frontend/src/i18n/locales/es.json`

- [ ] **Step 1: Add failing student behavior tests**

Test multiple chapter selection, a saved active run on load, Resume, Previous, Next, completion after the final item, Cancel, fresh selection after cancellation, no automatic audio playback, and image-only items.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `npm run test --workspace frontend -- src/features/listening/Listening.test.tsx`
Expected: FAIL because the component still offers sequential and random modes.

- [ ] **Step 3: Implement chapter selection and run controls**

Fetch an active run before showing chapter selection. Render translated chapter checkboxes when no run exists. Disable Start with no selection. Show the exact saved queue and current index when a run exists.

- [ ] **Step 4: Bind playback events to run items**

Pass `run_id` into `ListeningTracker` and remove `mode` from its context. Keep one UUID per playback session. Await the `end` event request before sending cancellation. Keep `pagehide` beacon delivery. Do not start audio from a response or navigation callback.

- [ ] **Step 5: Add run translations and verify student behavior**

Translate selection, run progress, Resume, Cancel, completion, and stable API error messages in all locales.

Run: `npm run test --workspace frontend -- src/features/listening/Listening.test.tsx src/features/listening/tracker.test.ts src/api/listeningRuns.test.ts src/i18n/locales.test.ts`
Expected: PASS.

- [ ] **Step 6: Commit the student listening flow**

```bash
git add frontend/src/features/listening/Listening.tsx frontend/src/features/listening/Listening.test.tsx frontend/src/features/listening/tracker.ts frontend/src/features/listening/tracker.test.ts frontend/src/api/listening.ts frontend/src/i18n/locales/en.json frontend/src/i18n/locales/ru.json frontend/src/i18n/locales/es.json
git commit -m "feat(frontend): select and resume chapter listening runs" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 9: Add Chapter journal filtering

**Files:**
- Modify: `backend/app/api/listening.py`
- Modify: `backend/tests/test_listening.py`
- Modify: `frontend/src/api/journal.ts`
- Modify: `frontend/src/api/journal.test.ts`
- Modify: `frontend/src/features/journal/Journal.tsx`
- Modify: `frontend/src/features/journal/Journal.test.tsx`
- Modify: `frontend/src/i18n/locales/en.json`
- Modify: `frontend/src/i18n/locales/ru.json`
- Modify: `frontend/src/i18n/locales/es.json`

- [ ] **Step 1: Add failing journal filter tests**

Verify that manager options include active chapters and historical chapter-number snapshots. Filter rows by the chapter number stored when playback began, not the exercise's current assignment.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `cd backend && pytest -q tests/test_listening.py`
Expected: FAIL because journal rows and filters lack chapter data.

Run: `npm run test --workspace frontend -- src/features/journal/Journal.test.tsx`
Expected: FAIL because the journal UI lacks the Chapter filter.

- [ ] **Step 3: Implement chapter filter API behavior**

Add `chapter_number` to journal input, output, and options. Filter `ListeningSession.chapter_number` without changing existing student, exercise, date, or pagination filters.

- [ ] **Step 4: Implement the manager filter and column**

Add a translated Chapter selector and a Chapter column that shows the localized chapter label and number. Include active chapters and historical snapshot numbers in the options. Preserve all current filters, pagination, date boundaries, and journal row meaning.

- [ ] **Step 5: Run focused journal tests**

Run: `cd backend && pytest -q tests/test_listening.py`
Expected: PASS.

Run: `npm run test --workspace frontend -- src/api/journal.test.ts src/features/journal/Journal.test.tsx src/i18n/locales.test.ts`
Expected: PASS.

- [ ] **Step 6: Commit the Chapter journal filter**

```bash
git add backend/app/api/listening.py backend/tests/test_listening.py frontend/src/api/journal.ts frontend/src/api/journal.test.ts frontend/src/features/journal/Journal.tsx frontend/src/features/journal/Journal.test.tsx frontend/src/i18n/locales/en.json frontend/src/i18n/locales/ru.json frontend/src/i18n/locales/es.json
git commit -m "feat(journal): filter listening records by chapter" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## Task 10: Update documentation and verify the complete feature

**Files:**
- Modify: `docs/PRODUCT_BRIEF.md`
- Modify: `docs/PHASES.md`
- Modify: `docs/DECISIONS.md`
- Modify: `docs/user/manager.md`
- Modify: `docs/user/student.md`
- Modify: `docs/developer/data-model.md`
- Modify: `docs/developer/api.md`
- Modify: `docs/developer/listening.md`
- Modify: `docs/developer/glossary.md`
- Modify: `CONTEXT.md`
- Modify: `docs/STATUS.md`

- [ ] **Step 1: Document the accepted behavior**

Update the product brief and phase plan. Record that chapter selection replaces the old student order modes. Preserve the earlier decisions as historical entries in `docs/DECISIONS.md`.

- [ ] **Step 2: Update user and developer guides**

Document manager chapter creation, exercise assignment, student selection, the 10-item cap, resume, cancel, and journal filtering. Keep documentation in English and use the required purpose and prerequisite format.

- [ ] **Step 3: Run documentation tests**

Run: `cd backend && pytest -q tests/test_documentation.py`
Expected: PASS.

- [ ] **Step 4: Run the complete backend and frontend suites**

Run: `cd backend && pytest -q`
Expected: PASS against disposable PostgreSQL.

Run: `npm run test --workspace frontend`
Expected: PASS for the full frontend suite.

- [ ] **Step 5: Run quality checks**

Run: `uv run --locked ruff check backend`
Run: `uv run --locked ruff format --check backend`
Run: `uv run --locked mypy --config-file pyproject.toml`
Run: `npm run lint --workspace frontend`
Run: `npm run typecheck --workspace frontend`
Run: `npm run format:check --workspace frontend`
Run: `npm run build --workspace frontend`

Expected: All commands pass.

- [ ] **Step 6: Refresh the code knowledge graph**

Run: `graphify update .`
Expected: The graph reflects the backend and frontend code changes. Report any semantic-update limitation; do not claim an update that did not complete.

- [ ] **Step 7: Review and commit the documentation**

Run: `git diff --check`
Run: `git status --short`

Commit only the documentation paths listed in this task. Use this command:

```bash
git add docs/PRODUCT_BRIEF.md docs/PHASES.md docs/DECISIONS.md docs/user/manager.md docs/user/student.md docs/developer/data-model.md docs/developer/api.md docs/developer/listening.md docs/developer/glossary.md docs/STATUS.md CONTEXT.md
git commit -m "docs: document chapter-based listening runs" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

Leave existing owner-staged and untracked files unchanged.

- [ ] **Step 8: Complete manual acceptance after deployment**

1. Use a disposable manager account. Create Chapter 2 and assign exercises. Confirm that assigned chapters cannot be deleted.
2. Use a disposable student account. Select Chapters 1 and 2. Confirm a maximum of 10 distinct exercises and the same order after reload and sign-in on another device.
3. Move backward and forward. Confirm that navigation does not start audio. Include an image-only exercise.
4. Cancel a run during playback. Confirm that playback stops and the journal row follows the existing completion rule.
5. Open the manager journal. Filter by Chapter 1 and a later chapter. Confirm that historical rows keep their saved chapter.
6. Check all 3 languages in Chrome and Safari.
