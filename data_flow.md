# Data Flow — Solfège Trainer

> Where data enters the system, how it changes, and where it ends up.

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

**Source:** Frontend requests to `GET /api/listening/current`, `POST /api/listening/select`, and `POST /api/listening/events`.
**Sink:** `student_progress` and `listening_sessions`.
**Transformations:** The selection service chooses an active exercise in sequential or random mode. The event service creates or updates one listening-session row and records completion and end time.
**Shape at each step:** Selection sends a mode, direction, and exercise identifiers. Listening events send session, exercise, audio, event, position, and mode fields. The session stores playback progress and a chapter-number snapshot.
**Source:** `backend/app/api/listening.py:29-43,96-140`; `backend/app/services/listening.py:16-125`; `backend/app/models/__init__.py:148-170`; `frontend/src/api/listening.ts:12-73`.

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

## Chapter management and listening runs

**Source:** Approved chapter design and the schema/contracts slice.
**Sink:** No chapter-management or listening-run endpoint is registered in this slice.
**Transformations:** The approved design calls for chapter selection, sampling up to 10 exercises, saving a randomized order, and supporting resume and cancellation. These behaviors remain unimplemented.
**Shape at each step:** The schema defines chapter records, run statuses, selected chapter numbers, and run items. The frontend defines typed chapter and run contracts.
**Source:** `docs/superpowers/specs/2026-10-19-exercise-chapters-design.md:11-55`; `backend/app/models/__init__.py:130-250`; `frontend/src/api/chapters.ts`; `frontend/src/api/listeningRuns.ts`.
