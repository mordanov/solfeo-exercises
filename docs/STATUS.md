# Project status

This document records progress and remaining checks for the current phase.

Prerequisites:
- Read `docs/PHASES.md` and `docs/DECISIONS.md`.

Last updated: 2026-09-28 by Copilot, session `1a328640-c756-4c7b-a686-ac6540a9a888`.

## Current phase
PHASE 0.5: Risk prototypes

## Plan for the current phase
- [x] Prepare the OMR sample set and owner-approved evaluation criteria.
- [ ] Run Audiveris in Docker and report recognition results.
- [ ] Demonstrate protected `.m4a` delivery with X-Accel-Redirect and Range.
- [ ] Plan the prototype deployment through the shared `web-folders` infrastructure.
- [ ] Demonstrate Android PWA sharing over HTTPS.
- [ ] Obtain owner approval of the report and record the final decisions.

## Done
- The owner approves the PHASE 0.5 plan.
- The owner approves 10 initial images, recognition criteria, and an owner-reviewed engine recommendation.
- Local sample preparation uses images 1 through 10; image 11 remains outside the initial evaluation.
- `docs/developer/omr-pipeline.md` defines sample handling, evaluation, and reporting.
- `docs/DECISIONS.md` records the approved evaluation decisions, not an engine acceptance decision.

## In progress
- No prototype code exists yet.
- Audiveris has not run; recognition quality remains unknown.
- The owner approves the Audiveris implementation plan and starting the existing Colima runtime.
- Runtime preparation stops because Docker remains unreachable after `colima start`.
- Colima reports an ARM64 VM with 2 CPUs and 10 GiB of memory.
- The official Audiveris release is `5.11.0`; its Linux installers target x86-64.
- A pinned ARM64 source build remains a candidate, not a verified runtime.

## Next step
- Restore Docker access or obtain explicit approval to restart Colima.
- Confirm that `docker version` reports both client and server versions.
- Select and verify a reproducible Audiveris build.
- Add failing prototype tests before implementing the runner and scoring logic.

## Open questions for the owner
- Authorize a Colima restart, or restore Docker without interrupting other workloads.
- Confirm the minimum prototype onboarding scope before changing the shared infrastructure.
- Identify the Android device and browser versions when manual testing starts.

## Manual checks the owner must do
- [ ] Confirm that images 1 through 10 represent the intended exercises.
- [ ] Review the criteria in `docs/developer/omr-pipeline.md`.
- [ ] Review actual recognition results and the engine recommendation after the OMR run.
- [ ] Test audio playback and seeking in macOS Safari and iOS/iPadOS Safari after the files prototype.
- [ ] Install the PWA from Android Chrome after HTTPS deployment.
- [ ] Share audio from WhatsApp and Telegram after the PWA prototype.

## Known issues
- Docker cannot connect to the configured Colima socket.
- `colima start` reports an existing running VM but does not restore Docker access.
- A diagnostic SSH command fails because the VM cannot access the project working directory.
- A follow-up diagnostic command receives a permission denial.
- No VM restart or container change occurs; restarting requires separate approval because it can interrupt other workloads.
- Samples and generated MusicXML remain local; a fresh clone does not contain them.
- HTTPS onboarding remains pending for `https://solfeo.miveralta.ru`.
- The onboarding guide is `../web-projects/web-folders/documentation/onboarding.md`.
- The prototypes have no execution results yet; PHASE 0.5 remains incomplete.
