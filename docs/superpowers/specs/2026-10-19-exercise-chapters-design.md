# Exercise chapters — design spec

Purpose: Define the design for numbered chapters and randomized listening runs.

Prerequisites:
- Read `docs/PRODUCT_BRIEF.md`.
- Read `docs/developer/data-model.md` and `docs/developer/listening.md`.

Date: 2026-10-19  
Status: approved for specification review; not implemented

## 1. Goal

Group exercises into numbered chapters and let students select chapters for a randomized listening run. Every exercise belongs to exactly one chapter.

The application uses `Chapter` in English, `Глава` in Russian, and `Unidad` in Spanish. It generates the translated label from the stable chapter number.

## 2. Roles and chapter management

Managers create numbered chapters and assign exercises to them. The app assigns the next unused number and never renumbers or reuses a number.

Managers select a chapter when they create or edit an exercise. The existing optional exercise category remains separate from the chapter.

Managers can delete a chapter only when no exercise remains assigned to it. This includes soft-deleted exercises. A run and a listening record keep chapter-number snapshots, so chapter deletion does not rewrite their history.

The schema migration creates Chapter 1. It assigns every existing exercise to Chapter 1, including soft-deleted exercises. It assigns every existing listening record to Chapter 1.

## 3. Student listening run

A student selects one or more chapters that contain active exercises. The student starts one active run for the account.

The app combines the active exercises from the selected chapters. If the pool contains more than 10 exercises, the backend samples 10 without replacement. Otherwise, it includes every exercise. The backend then saves a randomized order.

The app includes image-only exercises. These exercises keep the existing behavior: they show available content but do not create a listening journal row without audio playback.

The run contains each selected exercise once. It ends after the last exercise. The student can move backward or forward without automatic playback.

The backend saves the selected chapters, exercise order, current position, and run state. The same student can resume the same run after a reload or from another device.

Each student can have at most one active run. The student must cancel that run before starting another. A completed or cancelled run is no longer active.

The Cancel control stops playback, ends the current listening session under the existing event rules, and returns the student to chapter selection. A later run receives a fresh sample and shuffle.

## 4. Data and API

Add a numbered `chapters` table and a required chapter reference on each exercise. Keep the existing per-student sequential pointer columns, but stop using them for student exercise selection.

Add normalized listening-run records and ordered run-item records. Store the selected chapter numbers as run snapshots. Store the current position and active, completed, or cancelled state on the run.

Enforce one active run per student in PostgreSQL. Serialize run creation, navigation, and cancellation so simultaneous requests cannot corrupt the saved position.

Add manager endpoints to list, create, and delete chapters. Add a chapter field to exercise create and update requests.

Add student endpoints to list non-empty chapters, create or resume the active run, navigate its saved order, and cancel it. Keep the current student and CSRF permission checks.

The backend creates the sample and queue in one transaction. It rejects an empty chapter selection and stale or unavailable chapter IDs with stable error codes. A repeated start request returns the existing active run.

If a queued exercise becomes soft-deleted, the backend skips it. Protected exercise endpoints continue to reject deleted exercises.

## 5. Journal

Keep the journal at one row per listening session. Add a Chapter filter for managers.

Each new listening record stores the chapter number that applied when playback started. Existing records receive Chapter 1 during migration. Later exercise moves do not change earlier journal results.

The filter includes current chapters and chapter numbers found in historical journal snapshots. The manager can still filter records for a deleted chapter number.

## 6. User interface and localization

The manager interface provides chapter creation and chapter assignment in exercise forms. It prevents deletion while any active or soft-deleted exercise remains assigned.

The student interface replaces the sequential/random mode selector with a chapter selector. It shows the saved active run when one exists, with options to resume or cancel it.

All new interface strings use react-i18next. Add matching keys to English, Russian, and Spanish locale files.

## 7. Acceptance criteria

1. Upgrade an empty database and the previous release without data loss.
2. Assign every existing exercise and journal record to Chapter 1.
3. Create a numbered chapter and assign a new or existing exercise to it.
4. Reject exercise creation without a chapter and reject deletion of a non-empty chapter.
5. Let a student select multiple chapters and start a run with no more than 10 distinct exercises.
6. Confirm that every eligible exercise appears once when the combined pool contains 10 or fewer exercises.
7. Confirm that a pool above 10 produces a random sample with no duplicates and a saved randomized order.
8. Resume the same queue and position after reload and on another device.
9. Verify Previous, Next, completion, cancellation, and fresh-run behavior without automatic playback.
10. Confirm that cancel ends playback and preserves any journal row under the existing completion rule.
11. Confirm that image-only exercises remain eligible and create no playback journal rows.
12. Filter journal records by the chapter snapshot, including records created before the migration.
13. Reject access from player accounts and enforce the existing CSRF protections.
14. Verify matching localization keys in English, Russian, and Spanish.

## 8. Documentation and scope

Update the product brief, phase plan, manager guide, student guide, developer data-model guide, API guide, listening guide, glossary, and `STATUS.md` in the implementation phase.

Do not add dependencies. Do not change the exercise journal granularity, file protection, OMR behavior, or spoken-note behavior.
