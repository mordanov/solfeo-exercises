# Production smoke check

This document defines the final PHASE 7 end-to-end acceptance procedure after a clean verified deployment.

Prerequisites:
- Deploy the exact release through the standard CI, publication, and rollout workflow.
- Read `deploy.md`, `troubleshooting.md`, and both user guides.
- Prepare ordinary manager and student accounts through private channels.
- Prepare test audio, a clear original image, and a verified monophonic score.
- Use Chrome and Safari with Developer Tools or Web Inspector.

**Warning:** Use dedicated test accounts and exercises.
Preserve real accounts, original images, audio, imports, and journal rows.
Do not expose cookies, passwords, linking codes, or tokens in acceptance evidence.

## Release and isolation

1. Record the source SHA, successful CI run, release digests, deployment result, and browser versions.
2. Confirm healthy PostgreSQL, backend, frontend, OMR, and configured Telegram containers.
3. Confirm Alembic reports `0006_omr` through the migration service.
4. Confirm HTTPS health returns exactly `{"status":"ok"}`.
5. Confirm only the frontend publishes a loopback port.
6. Confirm unrelated containers retain their IDs and start times.
7. Confirm the current and compatible previous release remain available.
8. Confirm both storage filesystems retain the configured reserve.
9. Confirm JSON records and bounded Docker log rotation.
10. Confirm the OpenAI key is absent from runtime containers and browser assets.

Local automated scenarios cover cold installation, compatible rollback, and schema-incompatible refusal.
Do not deliberately exhaust production storage or break production migrations to repeat those checks.

## Unknown pages and browser protection

1. Open `/phase7-missing-page` without signing in.
2. Confirm the document returns HTTP 404.
3. Confirm the page offers a home link and all 3 language choices.
4. Check Russian, English, and Spanish messages and document language.
5. Click the home link and confirm a valid home page.
6. Reload `/login`, `/settings`, `/manager/exercises`, and `/student` directly.
7. Confirm valid routes still load their normal guarded application.
8. Request `/api/phase7-missing` and confirm JSON `NOT_FOUND` with HTTP 404.
9. Request an internal protected-media or protected-score path and confirm denial without exercise data.
10. Confirm CSP, frame denial, MIME protection, no-referrer, and restricted browser permissions.
11. Confirm HSTS on HTTPS responses.
12. Confirm the browser reports no CSP violations during score rendering, speech, and recorded playback.

## Accounts and upload limits

1. Sign in as an ordinary manager and create a test student.
2. Complete that student's obligatory password change.
3. Save each interface language and both note-naming choices.
4. Reload and sign in again to confirm persistence.
5. Open manager routes as the student and confirm denial.
6. Reset the student's password and confirm the old session stops working.
7. Confirm Secure, httpOnly, SameSite=Lax, and host-only session cookies.
8. Confirm requests with a missing or incorrect CSRF token fail.
9. Upload an image and real Opus audio as the manager.
10. Confirm the original image remains unchanged and converted audio uses AAC `.m4a`.
11. Submit unsupported and oversized files and confirm explicit errors without exercise creation.
12. Reorder exercises and reload to confirm persistence.

## OMR, speech, listening, and journal

1. Confirm the student sees the original image while recognition awaits approval.
2. Compare the recognized score with every note, rest, accidental, and measure.
3. Approve only a correct score.
4. Check labels and speech in all 6 language and naming combinations.
5. Check rests, ties, durations, slow tempo, and fast-tempo errors.
6. Confirm natural voice pitch and silence after short words in long notes.
7. Alternate speech and recorded audio and confirm only one plays.
8. Hide the tab, stop, navigate, and sign out without delayed speech.
9. Play and seek forward and backward in Chrome and Safari.
10. Confirm authenticated audio Range requests return HTTP 206.
11. Complete the first recording and close another tab before 90 %.
12. Confirm one completed and one incomplete journal row.
13. Confirm speech alone does not create or complete recorded-audio journal rows.
14. Check sequential persistence, random non-repetition, Previous, and no automatic playback.
15. Replace the image and confirm the old approval no longer authorizes labels or speech.
16. Delete a test exercise and confirm its original journal row remains.

## Telegram and recovery

1. Link a normal manager account through its website code.
2. Import real voice, forwarded audio, and an audio document.
3. Create an exercise from one import and replace audio from another.
4. Confirm original-image and earlier journal retention.
5. Confirm repeated delivery and repeated Save do not duplicate imports or exercises.
6. Confirm students and unlinked senders cannot import audio.
7. Restart only the product worker through its exact current-release configuration.
8. Confirm its offset, association, and saved imports remain.
9. Sign out in both browsers and confirm protected information disappears.
10. Record each result and any failed step before requesting final acceptance.

Safari audible speech acceptance remains mandatory.
Headless decoding and HTTP checks do not replace hearing the existing clips.
PHASE 7 remains open until this checklist passes on the VPS.
