# Project status

This document records progress and remaining checks for the current phase.

Prerequisites:
- Read `docs/PHASES.md` and `docs/DECISIONS.md`.

Last updated: 2026-09-29 by Copilot, session `1a328640-c756-4c7b-a686-ac6540a9a888`.

## Current phase
PHASE 0.5: Risk prototypes; ingestion decision accepted, remaining bot checks open.

## Plan for the current phase
- [x] Prepare the OMR sample set and owner-approved evaluation criteria.
- [x] Run Audiveris in Docker and report recognition results.
- [x] Demonstrate protected `.m4a` delivery with X-Accel-Redirect and Range.
- [x] Prepare the prototype deployment plan for owner review.
- [x] Evaluate Android PWA sharing and record its failure.
- [x] Demonstrate the Telegram replacement with owner-confirmed receipt and playback.
- [x] Record the owner-approved replacement of PWA audio sharing with the bot.
- [ ] Complete the remaining Telegram checklist before closing the phase.

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
- The owner confirms completion of the OMR manual checks on 2026-09-28.
- `prototypes/files/` contains the local protected-audio stand and its conversion helper.
- FastAPI authorizes the request; nginx serves the `.m4a` through an internal location.
- All 17 files unit tests and 13 live curl cases pass, with Ruff and strict mypy.
- `docs/developer/protected-audio.md` contains measured Range results and the Safari checklist.
- The files prototype containers and networks stop after verification; local media and evidence remain available.
- The owner confirms completion of the protected-audio manual step on 2026-09-29.
- `docs/developer/pwa-share.md` proposes the static HTTPS prototype and the shared-infrastructure changes.
- The owner approves the static PWA scope and deployment plan on 2026-09-29.
- `prototypes/pwa/` contains the local React/i18n shell, share receiver, IndexedDB storage, manifest, icons, and static Docker image.
- All 28 PWA tests, TypeScript, ESLint, Prettier, and the production build pass.
- Desktop Chrome verifies real multipart navigation, receipt, persistent storage, clear, and explicit errors against the built image.
- nginx rejects unhandled POSTs; browser-handled shares remain on the device.
- The local PWA container and isolated test browser stop after verification.
- The owner confirms the GHCR destination and authorizes shared configuration, publication, and targeted VPS deployment.
- DNS and SSH access identify the existing x86-64 VPS.
- Shared configuration adds the prototype without a database, Redis, or landing-page link.
- A prototype-only workflow validates and publishes the x86-64 image without automatic VPS deployment.
- The publishing workflow succeeds for application commit `8efc058`.
- The VPS runs the published image by digest at `https://solfeo.miveralta.ru/prototype-share/`.
- Shared infrastructure commits `900f62e` and `4578b73` persist on `main` and the VPS.
- A one-time `[skip ci]` synchronization prevents the general shared deployment from restarting unrelated applications.
- The hostname certificate is valid; the existing certificate watcher activates HTTPS.
- All 17 public HTTP checks pass, including certificate validation, manifest icons, worker headers, and early POST rejection.
- Desktop Chrome verifies the public share flow, persistence, clearing, and manifest installability without errors.
- All 12 deployed static files match the locally validated build.
- All 41 unrelated containers retain their original IDs and start times.
- `docs/user/pwa-prototype.md` provides the Android acceptance procedure.
- The owner approves the diagnostic follow-up after failed Android acceptance.
- The prototype maps text, title, and URL fields and distinguishes text-only, empty, and unexpected file-field input.
- On-device diagnostics retain field categories, file counts, types, and sizes without message contents, links, or filenames.
- Diagnostics and the last successful file have separate storage and clear actions.
- All 41 prototype tests, ESLint, Prettier, TypeScript, and the production build pass locally and in GitHub Actions.
- Diagnostic source commit `d171be5` is published and deployed by digest.
- Public HTTPS verifies the new manifest mappings and privacy-safe diagnostics through real browser form submissions.
- Failed attempts preserve the last successful file; diagnostic clearing persists independently.
- All 42 other containers, including nginx, retain their IDs and start times during this update.
- The owner confirms successful playback of `199163078.m4a` on 2026-09-29.
- The owner replaces product PWA audio sharing with the Telegram bot.
- The product brief and PHASE 4 plan now specify manager-only Telegram audio import.
- The existing web application scope, authentication, and student restrictions remain unchanged.
- The PWA report remains historical evidence of a failed approach, not an open product acceptance requirement.
- A targeted VPS restart preserves the saved audio hash, bot identity, and update checkpoint.
- The bot returns to healthy status; all 43 unrelated containers remain unchanged.

## In progress
- The files protocol checks and owner manual step are complete.
- Basic authentication is a localhost-only prototype assumption, not a product authentication decision.
- The HTTPS deployment works, but Android messenger sharing fails owner acceptance.
- On 2026-09-29, the owner reports "No audio file was received" after sharing from Telegram or WhatsApp.
- The owner repeats the Android test and reports a current attempt timestamp, `EMPTY_SHARE`, 0 file fields, and no form fields.
- The receiver observes an empty form; the point where data disappears remains unknown.
- Message-only sharing remains an unconfirmed hypothesis.
- The owner approves a separate Telegram prototype and deployment on the existing VPS.
- The bot implementation accepts allowlisted private attachments and saves validated AAC audio without creating exercises.
- All 27 bot tests, Ruff, and strict mypy pass locally and in CI, including actual Opus-to-AAC conversion.
- A non-root, read-only Docker check verifies simulated Telegram ingestion through real AAC conversion and durable checkpointing.
- Bot source `ac3442e` is published; shared configuration `3b94837` is synchronized to the VPS.
- The VPS `.env` pins the bot image digest.
- The published x86-64 image passes an offline runtime check on the VPS using simulated Telegram and actual AAC conversion.
- All 43 existing containers retain their original IDs and start times.
- The owner supplies the dedicated bot configuration privately.
- Telegram identity and webhook checks pass locally and from the VPS without exposing credentials.
- Shared commit `5e2f6c0` registers and activates only the Telegram worker.
- `https://t.me/solfeo_exercises_bot` is active, healthy, and polling Telegram.
- Both configuration files use mode `0600`; no token or allowed user ID enters Git or command output.
- All 43 pre-existing containers remain unchanged during activation.
- The owner confirms successful real audio receipt on 2026-09-29.
- The reported bot reply identifies `199163078.m4a`, with a size of 636644 bytes.
- Playback is confirmed; the specific attachment type and remaining checklist results are not recorded.
- Live checks for untested attachment types and an unauthorized sender remain open.
- No new-phase product code or deployment cleanup occurs in this task.

## Next step
- Complete the remaining bot checks without repeating the confirmed playback check.
- Close PHASE 0.5 after the remaining checks, then approve the first PHASE 0 implementation task.
- Keep the active bot and superseded PWA deployment unchanged until an explicit deployment or cleanup task.

## Proposed PHASE 0 sequence

The next phase is the walking skeleton, not product Telegram integration.
The following sequence is a plan, not implementation approval.

- [ ] Define the product layout, Python and TypeScript tooling, and the SQLAlchemy execution model.
- [ ] Add a tested FastAPI health endpoint and the translated React health page.
- [ ] Add PostgreSQL, an empty Alembic migration, validated settings, and complete environment examples.
- [ ] Add pre-commit checks, Docker images, Compose, and CI.
- [ ] Add targeted VPS deployment, health verification, and rollback without restarting unrelated applications.
- [ ] Update setup and deployment guides, then complete the manual health-page check.

Keep authentication in PHASE 1 and exercise/file operations in PHASE 2.
Integrate the bot with manager accounts and exercises in PHASE 4.
Do not copy disposable prototype authentication into the product.

## Open questions for the owner
- Identify the Android device and browser versions when manual testing starts.
- Record which Telegram attachment types passed; do not infer them from the saved filename.
- Select sync or async SQLAlchemy during PHASE 0 planning.

## Manual checks the owner must do
- [x] Confirm that images 1 through 10 represent the intended exercises.
- [x] Review the criteria in `docs/developer/omr-pipeline.md`.
- [x] Review the local MusicXML against the original images, especially images 7–9.
- [x] Review the image 6 failure and the manual event counts.
- [x] Confirm the recommendation to continue with Audiveris.
- [x] Complete the protected-audio manual step, as confirmed by the owner.
- [x] Confirm one successful real audio receipt through the Telegram bot.
- [x] Confirm successful playback of the saved audio.
- [x] Select Telegram instead of PWA sharing for product audio import.
- [x] Verify preserved audio and checkpoint state after a targeted VPS restart.
- [ ] Complete the real-message bot checklist in `docs/user/telegram-prototype.md`.

The superseded Android PWA checklist is no longer required.
Unreported bot checks remain unconfirmed; the replacement decision does not mark them as passed.

## Known issues
- Image 6 produces no MusicXML; image 7 receives 46 % recognition.
- Images 8 and 9 receive 95.35 % and 88 %, with important errors despite their `fully recognized` labels.
- Local artifacts are under `prototypes/omr/output/20260928T201957Z-84f49a71/`.
- Files evidence is under `prototypes/files/output/curl-20260928T204244Z-ec7ed479/`.
- The owner reports completion of the files manual step; device versions and the test setup are not recorded.
- Basic authentication uses disposable local credentials; product session authentication remains out of scope.
- The files prototype image remains local; operating-system package repositories remain unpinned.
- The PWA keeps only the latest successful share and rejects files above 25 MiB by default.
- Desktop browser checks do not establish Android sharing compatibility.
- The owner reports failed Android messenger sharing; successful desktop checks do not override this result.
- The PWA diagnostic receiver observes an empty form; the loss point remains unknown and is no longer under active investigation.
- PWA browser and static-server evidence remain in `prototypes/pwa/output/`.
- Samples and generated MusicXML remain local; a fresh clone does not contain them.
- The HTTPS PWA runs at `https://solfeo.miveralta.ru/prototype-share/`.
- The onboarding guide is `../web-projects/web-folders/documentation/onboarding.md`.
- PHASE 0.5 remains incomplete until the remaining prototypes and owner review finish.
