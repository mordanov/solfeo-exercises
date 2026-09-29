# Project status

This document records progress and remaining checks for the current phase.

Prerequisites:
- Read `docs/PHASES.md` and `docs/DECISIONS.md`.

Last updated: 2026-09-29 by Copilot, session `1a328640-c756-4c7b-a686-ac6540a9a888`.

## Current phase
PHASE 1: Users, authentication, and settings; implementation and automatic verification are in progress.
The owner authorizes the entire phase without intermediate confirmations on 2026-09-29.
Manual checks follow the complete implementation.
PHASE 0 is complete with owner-confirmed deployed browser acceptance.
The owner confirms the requested local health-page and PostgreSQL restart scenarios on 2026-09-29.
The owner confirms the remaining bot checks and continuation on 2026-09-29.
PHASE 0.5 is complete; the failed PWA result remains unchanged.

## Plan for the current phase
- [x] Add typed users, sessions, login budgets, and migration `0002_auth`.
- [x] Add scrypt authentication, secure cookies, sliding expiry, CSRF, and login limits.
- [x] Add startup emergency synchronization and all required lifecycle cases.
- [x] Add manager-only user administration, password resets, and session revocation.
- [x] Add persisted language/naming settings and obligatory password changes.
- [x] Add translated login, role guards, user administration, and settings forms.
- [ ] Complete automatic browser scenarios and the deployed release verification.
- [ ] Complete documentation and the final manual checklist.
- [ ] Obtain owner acceptance after the complete implementation.

## Completed PHASE 0 plan
- [x] Add the product layout and locked Python and TypeScript tooling.
- [x] Add the public FastAPI health endpoint and translated React health page.
- [x] Add isolated local Docker images, nginx, Compose, and initial CI.
- [x] Select synchronous SQLAlchemy 2.0 with psycopg 3.
- [x] Add PostgreSQL, an empty Alembic migration, and database settings.
- [x] Add real PostgreSQL tests and migration checks to CI.
- [x] Add shared pre-commit checks locally and in CI.
- [x] Add production Compose configuration and isolated integration checks.
- [x] Add CI-gated image publication and verified release bundles.
- [x] Add targeted VPS deployment, migration, health verification, and rollback.
- [x] Complete the deployed health-page manual check.

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
- PHASE 1 backend tests first fail because the user/session models do not exist.
- UI tests first fail because the account component does not exist.
- Account service tests use real PostgreSQL; no database mocks replace permission or lifecycle checks.
- The migration adds `users`, `login_sessions`, and `login_limits` above the previous empty baseline.
- Login, logout, current-password checks, reset, expiry, and active/role changes enforce session boundaries.
- Startup synchronizes the emergency manager and explicitly fails when recovery cannot reach the database.
- All 3 languages include account forms, permission errors, manager controls, and settings.
- Settings save to PostgreSQL and apply immediately after successful updates.
- Container checks cover real nginx authentication, student API denial, session/settings persistence, and nginx throttling.
- Local Chrome completes the full manager/student scenario, including reset, revocation, activation, persisted settings, and logout.
- The local migration and backend now share one image, preventing a stale migration image during targeted builds.
- Native Safari automation is unavailable because Allow Remote Automation is disabled; no system setting is changed.
- A malformed non-ASCII CSRF header returns the stable rejection code instead of causing a server error.
- The owner confirms Chrome/Safari, RU/EN/ES, status refresh, and failure/recovery checks on the deployed page.
- PHASE 0 closes with successful CI, targeted CD, updated documentation, and owner acceptance.
- Product source `13a081745a8cf0a5804f75f9a5831c0e9e7f4137` is active at `https://solfeo.miveralta.ru/`.
- CI run `36585295551` and publication/CD run `36585683212` succeed.
- The runner passes all 30 release and production checks before deployment.
- Actions verifies the owner's SSH configuration with pinned host keys and deploys through the separate product project.
- The VPS stores 3 independent database passwords in private `.env.production`; no password enters Git or output.
- Independent checks confirm the exact image digests, schema heads, container health, loopback-only frontend port, and proxy network membership.
- The deployment removes its temporary registry credentials.
- Chrome 154.0.8037.58 passes public HTTPS, all 3 languages, browser metadata, blocked-API failure, and recovery.
- The browser-only failure scenario does not stop the VPS backend.
- Shared commit `ac76b1c` persists nginx routing and its dedicated proxy network attachment.
- Nginx validates and reloads without container recreation; its rebuilt image preserves the templates for later recreation.
- All 44 pre-existing VPS containers retain their IDs and start times.
- The Telegram worker remains healthy; `/prototype-share/` keeps its route and method restrictions.
- The owner confirms Actions secret setup and requests continuation.
- Rollout tests first fail because the implementation module does not exist.
- The rollout validates archive provenance and hashes before activation.
- Real-container scenarios pass for first deployment, migration failure, health failure, and compatible previous-image recovery.
- The proxy network test confirms that only the product frontend joins the external network.
- The owner confirms final browser acceptance; automated Chrome evidence remains separate from that confirmation.
- The first CI attempt finds a missing temporary parent directory on a fresh runner.
- The rollout fixture now creates that directory explicitly before its disposable container scenario.
- The first product publication succeeds for source `03260e554b13c23b640ef6432775c50b331a7a39`.
- Publication run `36572516719` pulls and checks the published x86-64 images before creating the release bundle.
- The downloaded bundle matches the source files, manifest hashes, and CI run `36572315149`.
- The first publication's prerequisite report finds all 4 SSH secrets unavailable; the owner resolves this before the successful CD run.
- `publish-product.yml` publishes backend and frontend images only for a main-branch commit with matching successful CI.
- It pulls the registry images by digest, checks their source labels, and runs the production container scenarios.
- `deploy/release.py` packages only deployment files and a provenance manifest with immutable image references and file hashes.
- All 13 release-bundle unit tests pass; the runtime dependencies remain unchanged.
- A separate Actions job reports SSH-secret presence without exposing values or accessing the VPS.
- That first publication task does not change shared infrastructure, the active bot, or public routing.
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
- Complete PHASE 1 automatic browser checks and targeted deployment.
- Present only the final manual checklist; do not request intermediate approvals.
- Keep PHASE 2 out of this task.
- Keep the active bot and superseded PWA deployment unchanged until an explicit deployment or cleanup task.

## PHASE 0 boundaries

The owner requests continuation after completing PHASE 0.5 checks.
The first implementation task establishes a local health page, not a complete production deployment.
The database task adds synchronous SQLAlchemy and an empty Alembic baseline.
It does not add users, exercises, journal records, or worker jobs.

Keep authentication in PHASE 1 and exercise/file operations in PHASE 2.
Integrate the bot with manager accounts and exercises in PHASE 4.
Do not copy disposable prototype authentication into the product.

## Acceptance details
- The owner confirms the requested local scenarios without browser versions or a detailed browser matrix.
- The owner confirms the requested final VPS scenarios on 2026-09-29.
- Owner-tested browser versions and a per-browser evidence matrix are not supplied.

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
- [x] Confirm Chrome and Safari behavior, all 3 languages, and failure/recovery during final VPS acceptance.
- [x] Configure the 4 deployment secrets, as confirmed by the owner.

The superseded Android PWA checklist is no longer required.
The new local health-page procedure appears in `docs/user/manager.md` and `docs/user/student.md`.
The owner confirms final PHASE 0 browser acceptance at the public HTTPS address.
The final PHASE 1 procedures are in `docs/user/manager.md` and `docs/user/student.md`.

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
- Product CD and public nginx integration are active; the owner confirms final VPS acceptance.
- The first deployment has no earlier production release; automatic rollback becomes available after a subsequent successful deployment.
- Schema-incompatible rollback stops the product services and requires operator recovery; no automatic database downgrade occurs.
- The current CLI credential cannot manage repository Actions secrets: the public-key API returns HTTP 403.
- The deployment job confirms valid SSH configuration and removes its temporary registry credentials.
- Development still uses the bootstrap database role; the separate production configuration does not.
