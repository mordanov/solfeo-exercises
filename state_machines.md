# State Machines — Solfège Trainer

> Entity lifecycles. What states exist, how transitions happen, and what guards them.

## Exercise

**States:** active, deleted
**Initial:** active
**Transitions:**
- — → active on creation, when the exercise has an image or audio file.
- active → active on update or reorder, while at least one media file remains.
- active → deleted on soft deletion; the record and its files remain.
**Source:** `backend/app/services/exercises.py:29-35,54-123`.

## Listening session

**States:** incomplete, completed; ended is an independent timestamp.
**Initial:** incomplete
**Transitions:**
- — → incomplete on a valid `start` event for an active exercise with audio.
- incomplete → incomplete on playback updates below 90% of the audio duration.
- incomplete → completed on an `ended` event or when playback reaches 90%.
- incomplete/completed → ended when an `end` or `ended` event sets `ended_at`.
**Guards:** The user, exercise, and audio must match the session.
**Source:** `backend/app/services/listening.py:91-125`.

## Listening run

**States:** active, completed, cancelled
**Initial:** Not defined in this schema slice.
**Transitions:** No mutation paths exist in this slice.
**Notes:** The database constrains the status values and allows one active run per user.
**Source:** `backend/migrations/versions/0013_exercise_chapters_and_listening_runs.py:1-170`.

## OMR job

**States:** pending, processing, needs_review, approved, rejected, failed
**Initial:** pending
**Transitions:**
- any current job → superseded when a new job replaces it.
- pending → processing when a worker claims an eligible job.
- processing → processing when a worker reclaims an expired lease.
- processing → needs_review when valid MusicXML completes.
- processing → pending after a retryable failure with attempts remaining.
- processing → failed after a terminal failure or exhausted attempts.
- needs_review/approved/rejected → approved or rejected after manager review.
**Guards:** Claims require a current job, a matching exercise image, an available retry time, and attempts remaining.
**Source:** `backend/app/services/omr.py:36-207`.

## Round and task attempt

**Round states:** active, completed, expired
**Initial:** active
**Transitions:**
- — → active when the service creates a round with valid settings.
- active → active when a valid next task is submitted.
- active → completed after the final configured task is submitted.
**Notes:** The model admits `expired`, but no observed mutation writes that status.
**Task attempt states:** unissued, issued, submitted. The service issues tasks in order and records each response once.
**Source:** `backend/app/game/services/rounds.py:94-263`; `backend/app/game/models.py:76-127`.

## Season

**States:** active, ended
**Initial:** active
**Transitions:**
- — → active when the service creates the first season.
- active → ended when a reset closes the current season.
- ended → active when the service creates the next season.
**Source:** `backend/app/game/services/players.py:75-93`; `backend/app/game/services/seasons.py:20-37`.

## Custom avatar

**Job states:** pending, ready, failed
**Review states:** pending, approved, rejected
**Transitions:**
- — → pending on a valid avatar-generation request.
- pending → ready when generation completes and awaits manager review.
- pending → failed when generation reaches a terminal failure.
- ready/pending-review → ready/approved or ready/rejected after manager review.
- ready/approved → ready/approved when a player selects the avatar.
- non-pending → deleted when a manager discards an unused avatar.
**Notes:** The worker also records generation phases. The database does not constrain their values.
**Source:** `backend/app/game/services/avatars.py:38-91,207-233,271-329`; `worker/generate_avatar.py:288-395`.

## Telegram import

**States:** message, pending, ready, failed, applied, discarded
**Transitions:**
- — → message when the service stores an incoming private-chat update.
- message → pending when an authorized import starts.
- message/pending → failed when validation or processing fails.
- pending → ready when processing succeeds.
- ready → applied when a manager applies the media to an exercise.
- ready → discarded when a manager discards the import.
- applied → applied when the same request is repeated idempotently.
**Notes:** The `ready` and `discarded` mutation paths need confirmation from their owning handlers.
<!-- needs-confirmation: Confirm the success and discard mutation paths in the Telegram handlers. -->
**Source:** `backend/app/services/telegram.py:120-200,218-270,325-365`.
