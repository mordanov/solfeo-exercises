# Project status

This document records progress and remaining checks for the current phase.

Prerequisites:
- Read `docs/PHASES.md` and `docs/DECISIONS.md`.

Last updated: 2026-09-28 by Copilot, session `1a328640-c756-4c7b-a686-ac6540a9a888`.

## Current phase
PHASE 0.5: Risk prototypes

## Plan for the current phase
- [x] Prepare the OMR sample set and owner-approved evaluation criteria.
- [x] Run Audiveris in Docker and report recognition results.
- [ ] Demonstrate protected `.m4a` delivery with X-Accel-Redirect and Range.
- [ ] Plan the prototype deployment through the shared `web-folders` infrastructure.
- [ ] Demonstrate Android PWA sharing over HTTPS.
- [ ] Obtain owner approval of the report and record the final decisions.

## Done
- The owner approves the PHASE 0.5 plan.
- The owner approves 10 initial images, recognition criteria, and an owner-reviewed engine recommendation.
- Local sample preparation uses images 1 through 10; image 11 remains outside the initial evaluation.
- `docs/developer/omr-pipeline.md` defines sample handling, evaluation, and reporting.
- `docs/DECISIONS.md` records the approved evaluation criteria and the decision to continue with Audiveris.
- Docker access is restored before the OMR run.
- `prototypes/omr/` contains the pinned Audiveris build, offline runner, settings, dependency lock, and 26 passing tests.
- Ruff and strict mypy pass for the prototype.
- Audiveris `5.11.0` runs natively on ARM64 against all 10 selected images.
- The run exports MusicXML for 9 images; image 6 fails during staff detection.
- The reviewed classification is 8 fully recognized, 0 partly recognized, and 2 failed images.
- Images 8 and 9 meet the threshold but contain notation errors.
- `docs/developer/omr-pipeline.md` contains reproduction commands, per-image results, limitations, and the recommendation.
- The owner confirms the engine recommendation on 2026-09-28.
- Manager review and the original-image fallback remain mandatory.

## In progress
- Detailed owner verification of the event comparisons remains unconfirmed.
- No files or PWA prototype work starts in this task.

## Next step
- Plan the protected-audio prototype as the next implementation task.

## Open questions for the owner
- Confirm the minimum prototype onboarding scope before changing the shared infrastructure.
- Identify the Android device and browser versions when manual testing starts.

## Manual checks the owner must do
- [ ] Confirm that images 1 through 10 represent the intended exercises.
- [ ] Review the criteria in `docs/developer/omr-pipeline.md`.
- [ ] Review the local MusicXML against the original images, especially images 7–9.
- [ ] Review the image 6 failure and the manual event counts.
- [x] Confirm the recommendation to continue with Audiveris.
- [ ] Test audio playback and seeking in macOS Safari and iOS/iPadOS Safari after the files prototype.
- [ ] Install the PWA from Android Chrome after HTTPS deployment.
- [ ] Share audio from WhatsApp and Telegram after the PWA prototype.

## Known issues
- Image 6 produces no MusicXML; image 7 receives 46 % recognition.
- Images 8 and 9 receive 95.35 % and 88 %, with important errors despite their `fully recognized` labels.
- Local artifacts are under `prototypes/omr/output/20260928T201957Z-84f49a71/`.
- The original-image transcription requires owner verification.
- The tested Docker image is local, not published; operating-system package repositories remain unpinned.
- Samples and generated MusicXML remain local; a fresh clone does not contain them.
- HTTPS onboarding remains pending for `https://solfeo.miveralta.ru`.
- The onboarding guide is `../web-projects/web-folders/documentation/onboarding.md`.
- PHASE 0.5 remains incomplete until the remaining prototypes and owner review finish.
