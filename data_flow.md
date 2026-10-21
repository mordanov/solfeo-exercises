# Data Flow — Solfège Trainer

> Where data enters the system, how it changes, and where it ends up.

## Guess the Note round creation

**Source:** Setup sends `clef_mode`, difficulty, note count, and assistance flags to `POST /api/game/rounds`.
**Sink:** A round and 7 saved task attempts; the response contains the first task.
**Transformations:** The API validates the mode. The service generates only the selected clef or shuffles a balanced 3-and-4 split.
**Shape at each step:** UI `GameOptions.clefMode` becomes request `clef_mode`, defaulting to `both` on omission.
Each saved attempt contains its generated `clef` and notes. Later submissions issue these saved tasks without another clef selection.
**Notes:** Setup retains the selection between rounds in local state. Scoring and XP do not consume this setting.
**Source:** `frontend/src/features/game/setup/GameSetup.tsx`; `frontend/src/features/game/api/hooks.ts`; `backend/app/game/api/rounds.py`; `backend/app/game/services/rounds.py:90-178`.

## Exercise creation and update

**Source:** Manager multipart request to `POST /api/exercises` or `PUT /api/exercises/{id}`.
**Sink:** `exercises`, `media_files`, and, when an image changes, `omr_jobs`. The API returns `ExerciseOutput`.
**Transformations:** The API validates the title and category. The service validates media, stores files, and updates exercise references.
**Shape at each step:** `ExerciseInput` contains text fields and optional image/audio uploads. `ExerciseOutput` includes exercise fields, `chapter_id`, `chapter_number`, media metadata, and OMR state.
**Source:** `backend/app/api/exercises.py:25-98`; `backend/app/services/exercises.py:54-99`.

## Exercise listing and protected media

**Source:** Frontend query to `GET /api/exercises`, followed by an authenticated media request.
**Sink:** The frontend exercise list and the browser image/audio element.
**Transformations:** The API lists active exercises and resolves chapter numbers in one query. The file route checks access before returning an internal nginx redirect.
**Shape at each step:** `ExerciseListOutput` contains `exercises` and `total`. Each exercise includes chapter identity and media metadata. The media route returns `X-Accel-Redirect` after authorization.
**Source:** `backend/app/api/exercises.py:54-111,169-188`; `backend/app/services/exercises.py:28-47`; `frontend/src/api/exercises.ts:5-52`.

## Student exercise selection and listening

**Source:** The student UI first requests `GET /api/listening/run`; when no active run exists, it requests `GET /api/listening/chapters`. Starting, navigating, and cancelling use `POST /api/listening/run`, `POST /api/listening/run/{id}/navigate`, and `POST /api/listening/run/{id}/cancel`. Playback uses `POST /api/listening/events`.
**Sink:** `listening_runs`, `listening_run_chapters`, `listening_run_items`, and `listening_sessions`.
**Transformations:** The backend samples up to 10 exercises from selected chapters, saves their randomized order, and returns the active run on reload. The UI displays that exact queue and requires an explicit Resume action. Previous and Next operate on saved positions without autoplay. Before cancellation or navigation, the player ends the current listening session; on `pagehide`, the tracker sends the terminal event with `sendBeacon`.
**Shape at each step:** Run responses contain status, selected chapter-number snapshots, current position, and ordered exercise items. Listening events contain `run_id`, `session_id`, exercise, audio, event, position, and CSRF fields; the session stores progress and its chapter-number snapshot.
**Source:** `backend/app/api/listening_runs.py:101-150`; `backend/app/services/listening_runs.py:75-230`; `backend/app/api/listening.py:72-98`; `backend/app/services/listening.py:16-125`; `frontend/src/features/listening/Listening.tsx:22-310`; `frontend/src/features/listening/tracker.ts:13-107`.

## Exercise image to OMR score

**Source:** Exercise image upload or replacement.
**Sink:** `omr_jobs`, the protected score directory, and the OMR API response.
**Transformations:** The service creates a current pending job. The worker claims it with a lease, reads the image, runs recognition, and submits MusicXML. The service validates MusicXML and records review status.
**Shape at each step:** The job stores exercise and image identifiers, status, attempts, and lease fields. The worker claim contains the job, exercise, image, and filename.
**Source:** `backend/app/services/exercises.py:87-95`; `backend/app/services/omr.py:54-133,199-243`; `worker/omr.py:18-32`.

## Chapter migration and exercise contract

**Source:** Alembic upgrade from `0012_player_role` to `0013_exercise_chapters`.
**Sink:** `chapters`, `exercises.chapter_id`, `listening_sessions.chapter_number`, and the listening-run tables.
**Transformations:** The migration creates Chapter 1, assigns existing exercises to it, snapshots Chapter 1 on existing listening rows, and adds run tables. The exercise API includes chapter identity in its responses.
**Shape at each step:** Chapter rows contain an ID and stable number. Exercise rows contain a required `chapter_id`; listening rows contain a chapter-number snapshot.
**Source:** `backend/migrations/versions/0013_exercise_chapters_and_listening_runs.py:1-170`; `backend/app/api/exercises.py:54-98`.

## Chapter management

**Source:** Manager requests to `GET /api/chapters`, `POST /api/chapters`, and `DELETE /api/chapters/{id}`, and multipart exercise create/update requests with `chapter_id`.
**Sink:** `chapters` and `exercises.chapter_id`.
**Transformations:** Chapter numbers are assigned monotonically. Deletion is rejected while any active or soft-deleted exercise is assigned. Students receive only chapters with active exercises through `GET /api/listening/chapters`.
**Shape at each step:** Chapter responses include stable ID/number and active/assigned exercise counts. Exercise responses include `chapter_id` and `chapter_number`.
**Source:** `backend/app/api/chapters.py:28-53`; `backend/app/api/exercises.py:25-111`; `backend/app/services/chapters.py`; `frontend/src/api/chapters.ts`.

## Manager journal and chapter filters

**Source:** Manager requests to `GET /api/journal` with optional student, exercise, chapter, and date filters, and to `GET /api/journal/options`.
**Sink:** The journal response rows and filter controls in the manager UI.
**Transformations:** The service filters `ListeningSession.chapter_number`, which records the chapter at playback time. Options combine current chapter numbers with historical chapter snapshots, including numbers from deleted chapters.
**Shape at each step:** Journal rows include `chapter_number`. The options response includes student, exercise, and chapter-number choices. The UI shows the translated chapter label for each row.
**Source:** `backend/app/api/listening.py:40-160`; `backend/app/services/listening.py:100-165`; `frontend/src/api/journal.ts:1-105`; `frontend/src/features/journal/Journal.tsx:15-220`.
