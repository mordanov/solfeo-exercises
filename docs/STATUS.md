# Project status

This document records progress and remaining checks for the current phase.

Prerequisites:
- Read `docs/PHASES.md` and `docs/DECISIONS.md`.

Last updated: 2026-09-29 by Copilot, session `1a328640-c756-4c7b-a686-ac6540a9a888`.

## Current phase
PHASE 0: Walking skeleton and CI/CD; CI-gated release publication is implemented, but VPS rollout remains pending.
The owner confirms the requested local health-page and PostgreSQL restart scenarios on 2026-09-29.
The owner confirms the remaining bot checks and continuation on 2026-09-29.
PHASE 0.5 is complete; the failed PWA result remains unchanged.

## Plan for the current phase
- [x] Add the product layout and locked Python and TypeScript tooling.
- [x] Add the public FastAPI health endpoint and translated React health page.
- [x] Add isolated local Docker images, nginx, Compose, and initial CI.
- [x] Select synchronous SQLAlchemy 2.0 with psycopg 3.
- [x] Add PostgreSQL, an empty Alembic migration, and database settings.
- [x] Add real PostgreSQL tests and migration checks to CI.
- [x] Add shared pre-commit checks locally and in CI.
- [x] Add production Compose configuration and isolated integration checks.
- [x] Add CI-gated image publication and verified release bundles.
- [ ] Add targeted VPS deployment, migration, health verification, and rollback.
- [ ] Complete the deployed health-page manual check.

## Completed PHASE 0.5 plan
- [x] Prepare the OMR sample set and owner-approved evaluation criteria.
- [x] Run Audiveris in Docker and report recognition results.
- [x] Demonstrate protected `.m4a` delivery with X-Accel-Redirect and Range.
- [x] Prepare the prototype deployment plan for owner review.
- [x] Evaluate Android PWA sharing and record its failure.
- [x] Demonstrate the Telegram replacement with owner-confirmed receipt and playback.
- [x] Record the owner-approved replacement of PWA audio sharing with the bot.
- [x] Complete the remaining Telegram checklist, as confirmed by the owner.

## Done
- The first product publication succeeds for source `03260e554b13c23b640ef6432775c50b331a7a39`.
- Publication run `36572516719` pulls and checks the published x86-64 images before creating the release bundle.
- The downloaded bundle matches the source files, manifest hashes, and CI run `36572315149`.
- The Actions prerequisite report finds `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, and `VPS_KNOWN_HOSTS` unavailable.
- `publish-product.yml` publishes backend and frontend images only for a main-branch commit with matching successful CI.
- It pulls the registry images by digest, checks their source labels, and runs the production container scenarios.
- `deploy/release.py` packages only deployment files and a provenance manifest with immutable image references and file hashes.
- All 13 release-bundle unit tests pass; the runtime dependencies remain unchanged.
- A separate Actions job reports SSH-secret presence without exposing values or accessing the VPS.
- This task does not change shared infrastructure, the active bot, or public routing.
- `deploy/compose.prod.yaml` uses supplied images without building application code on the server.
- It publishes only the frontend on loopback and keeps PostgreSQL on a private network.
- Production uses separate bootstrap administrator, migration owner, and runtime application roles.
- The runtime role can change table data but cannot create, alter, or drop tables.
- Alembic metadata uses a private production schema, inaccessible to the runtime role.
- The development version table remains in `public`; regression checks prevent an unwanted autogeneration diff.
- Production startup waits for migrations; the integration test proves a failed migration blocks a stopped backend from starting.
- Docker logs have configured size and file-count limits.
- The backend suite passes 33 tests; 3 separate production container scenarios pass.
- Production tests verify SQL permissions, hidden privileged credentials, unpublished ports, restart persistence, migration failure, and recovery.
- The tests remove their own temporary projects and volumes without changing the development database or VPS.
- `docs/developer/deploy.md` documents production configuration and the remaining TLS/CD integration.
- The owner confirms that the requested local health-page and database persistence scenarios pass.
- `.pre-commit-config.yaml` runs Ruff, Ruff format, strict mypy, ESLint, Prettier, and TypeScript.
- Python hooks use the locked project tooling; JavaScript hooks use isolated Node.js 22.23.3 and npm 12.1.0.
- The JavaScript hooks use existing workspace dependencies without replacing the system Node.js.
- All 6 hooks reject deliberate lint, formatting, or type errors and pass after those temporary probes are removed.
- Hook configuration changes trigger all checks; prototype-only changes trigger none of these product hooks.
- The repository Git hook is installed locally without overwriting existing hooks.
- CI runs the same configuration through its `checks` job; tests, migrations, and builds remain separate jobs.
- The pre-commit dependency belongs only to development tooling; the runtime dependency export is unchanged.
- The product backend and frontend remain separate from disposable prototypes.
- `/api/health` returns `{"status":"ok"}` without authentication or caching.
- This endpoint checks the process, not PostgreSQL or other services.
- The health page supports English, Russian, and Spanish, with pending, success, failure, and retry states.
- The page shows explicit network, timeout, unavailable-service, and invalid-response errors.
- Language changes update the page, document title, and document language.
- The root `.env.example` documents all settings for this slice.
- Root `uv.lock`, `requirements.txt`, and `package-lock.json` lock dependencies.
- The health-page task passes 12 backend tests, 34 frontend tests, and all configured code checks.
- The database task extends the backend suite to 30 passing tests against real PostgreSQL.
- Ruff, formatting, and strict mypy pass for the database implementation and migrations.
- PostgreSQL 17 uses a pinned image, a persistent development volume, and a loopback host port.
- A separate disposable PostgreSQL stand isolates tests from the development database.
- Alembic revision `0001_initial` records an empty baseline without product tables.
- The migration check covers a fresh schema, repeated upgrade, downgrade, upgrade, and model drift.
- FastAPI owns the connection pool and disposes it during shutdown.
- Request sessions close without automatic commit; explicit transactions commit or roll back.
- Configuration requires a private database password and hides SQL parameter values in errors.
- A private root `.env` uses mode `0600` and remains outside Git.
- Local Compose waits for PostgreSQL and successful migrations before starting the backend.
- A local PostgreSQL restart preserves revision `0001_initial`; native and container migration commands confirm the current schema.
- The production frontend build and isolated Compose healthchecks pass.
- Desktop Chrome verifies the built page, all 3 languages, a stopped backend, explicit failure, and recovery.
- The local stand remains available at `http://127.0.0.1:18080/` for owner checks.
- `.github/workflows/ci.yml` checks the product without publishing or deploying images.
- `docs/developer/setup.md` explains local execution and checks.
- Product authentication, domain models, and Telegram integration are not implemented.
- The working VPS, bot, and superseded PWA deployment remain unchanged in this task.
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

## PHASE 0.5 deployment record
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
- The owner subsequently confirms that the remaining manual checks pass on 2026-09-29.
- This confirms the voice, forwarded-audio, document, and unauthorized-sender cases requested in the previous handoff.
- The owner does not supply device versions or a per-message evidence record.

## Next step
- Review the publication artifact and the deployment prerequisite report.
- Configure any missing SSH secrets through repository settings.
- Implement targeted VPS rollout, shared nginx integration, migration verification, and rollback.
- Keep the active bot and superseded PWA deployment unchanged until an explicit deployment or cleanup task.

## PHASE 0 boundaries

The owner requests continuation after completing PHASE 0.5 checks.
The first implementation task establishes a local health page, not a complete production deployment.
The database task adds synchronous SQLAlchemy and an empty Alembic baseline.
It does not add users, exercises, journal records, or worker jobs.

Keep authentication in PHASE 1 and exercise/file operations in PHASE 2.
Integrate the bot with manager accounts and exercises in PHASE 4.
Do not copy disposable prototype authentication into the product.

## Remaining acceptance details
- The owner confirms the requested local scenarios without browser versions or a detailed browser matrix.
- Complete the browser matrix during final VPS acceptance.

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
- [x] Complete the real-message bot checklist, as confirmed by the owner.
- [x] Confirm that the local health page opens.
- [x] Confirm that the local schema revision survives a PostgreSQL restart.
- [ ] Confirm Chrome and Safari behavior, all 3 languages, and failure/recovery during final VPS acceptance.
- [ ] Configure the 4 missing deployment secrets in the application repository's Actions settings.

The superseded Android PWA checklist is no longer required.
The new local health-page procedure appears in `docs/user/manager.md` and `docs/user/student.md`.
The production configuration task adds no new browser manual checks before the actual VPS deployment.

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
- npm 10 fails during fresh workspace dependency resolution; npm 12.1.0 resolves the declared dependencies.
- The health-page language selector is temporary and does not save user preferences.
- Product CD, public nginx integration, and VPS acceptance remain for later PHASE 0 tasks.
- No product release is active on the VPS; publication artifacts provide the tested image digests for the next task.
- The current CLI credential cannot manage repository Actions secrets: the public-key API returns HTTP 403.
- VPS rollout cannot proceed through the planned Actions configuration until the owner provides the missing SSH secrets.
- Development still uses the bootstrap database role; the separate production configuration does not.
