# Project status

This document records progress and remaining checks for the current phase.

Prerequisites:
- Read `docs/PHASES.md` and `docs/DECISIONS.md`.

Last updated: 2026-10-01 by Copilot, session `296626a2-8b63-40eb-9331-72dd123a0523`.

## Current phase
PHASE 7: hardening and documentation review.
Implementation is complete locally; production deployment and final manual acceptance remain open.
The owner authorizes the entire phase without intermediate confirmations on 2026-10-01.
Work uses `feat/phase7-hardening`, based on merged PHASE 6 source `f3ba47f`.
The owner retains all 66 speech clips and declines regeneration.
The task does not call the paid speech generator.

### PHASE 7 implementation
- Add a configurable 6144 MiB cold-image budget and 2048 MiB free reserve.
- Measure Docker and release storage before pulls and check the reserve again before changing services.
- Fail closed for unknown storage, invalid limits, insufficient space, and remote Docker daemons.
- Preserve active services, database volumes, release state, and existing rollback images after capacity refusal.
- Add a translated application 404 page with a language selector and home link.
- Preserve HTTP 404, HEAD behavior, API JSON errors, authenticated file checks, and direct internal-file denial.
- Add CSP, frame denial, MIME protection, no-referrer, restricted browser permissions, and HTTPS-only HSTS.
- Reject insecure HTTPS cookies and non-loopback HTTP authentication during settings validation.
- Add structured backend, worker, and nginx access records without request bodies, tokens, or query strings.
- Keep exception types and frame locations without logging exception values.
- Record backend lifespan failures before rethrowing them; preserve cleanup and safe exception diagnostics.
- Verify existing production log rotation and OMR/Telegram healthchecks.
- Add strict Python and JavaScript dependency audits to CI.
- Add documentation checks for required guides, environment coverage, relative links, and sentence lengths.
- Review developer and user documentation; correct stale phase, schema, deployment, and prototype statements.
- Add the missing language and troubleshooting guides and the complete final VPS smoke checklist.

### PHASE 7 validation and deployment boundary
Local backend and frontend suites, quality hooks, dependency audits, image builds, and real container checks pass.
Local checks pass 150 backend tests, 137 frontend tests, and 56 deployment/container tests.
Container checks cover 404 statuses, headers, API/file boundaries, Range playback, log rotation, migrations, and compatible rollback.
Disk tests cover the exact 8192 MiB pre-pull boundary and the 2048 MiB post-pull reserve.
Documentation checks cover all product environment variables and the complete user/developer guide set.
The existing tracker test passes in the pinned Node container; no unrelated flaky-test change is necessary.

The updated PHASE 7 stand responds at `http://127.0.0.1:18080/`.
PostgreSQL, backend, frontend, and OMR report healthy states; Telegram remains stopped.
Public health and unknown-page HEAD checks pass against this persistent stand.
The strengthened rollback check confirms that disk refusal preserves all running service identities and release state.

Main-branch CI run `36866682091` succeeds for merged PHASE 6 source `f3ba47f`.
Publication run `36867434244` verifies its images but deployment fails with `OMR_MEMORY_INSUFFICIENT`.
The recorded failure is current evidence from the configured deployment target, not a new-host capacity measurement.
PHASE 7 does not bypass this guard, rewrite private server configuration, or restart unrelated services.
Its branch requires successful remote CI and a verified production rollout before final owner acceptance.
Chrome command-line DOM verification times out in this environment.
HTTP and React component checks pass; they do not establish a successful real-browser acceptance pass.
Chrome and Safari checks remain in the final checklist, after implementation.

### Previous PHASE 6 acceptance
PHASE 6 spoken notes are complete with owner-confirmed audible Chrome acceptance.
The owner authorizes complete phase automation and postpones PHASE 5 deployment on 2026-09-30.
Work uses `feat/phase6-spoken-notes` so main-branch publication cannot deploy these changes.
The owner supplies the private OpenAI key and opens pull request #1 on 2026-10-01.
All 66 actual speech clips are generated, verified, and committed.
The owner confirms audible Chrome acceptance in the local container stand on 2026-10-01.
The owner requests and receives 3 follow-up fixes after the listening pass, detailed below.

### PHASE 6 follow-up fixes after owner acceptance
- Poor photo quality causes genuine OMR chords and backups in exercises 32 and 33, so the strict
  parser correctly refuses to speak them. `docs/PRODUCT_BRIEF.md`, `docs/PHASES.md`, and
  `docs/user/manager.md` now document the required photo quality before OMR upload.
- Spoken playback previously changed pitch per note duration because the rate limiter clamped
  long notes down to `minRate`. The rate now floors at 1 and pads spare time with silence, so
  every note keeps one natural voice pitch. `minRate` is removed from the spoken configuration.
- The generator adds a native-accent hint per language (`ACCENT_HINTS` in
  `worker/generate_spoken.py`). The fingerprint does not hash the instructions text, so the 66
  committed clips remain valid without regeneration; applying the new accent requires the owner
  to regenerate into a fresh `SPOKEN_OUTPUT` directory with their own key, listen, and replace the
  committed set. This is optional future work, not a PHASE 6 blocker.
- `Listening.tsx` now shows the spoken-notes controls with a dedicated message when an approved
  exercise has no recorded audio, instead of the generic "image only" message.
- All 3 fixes are committed, pushed, and merged through pull request #1; pre-commit and
  `backend/tests/test_spoken_generation.py` are green.

PHASE 6 acceptance uses the local container stand at `http://127.0.0.1:18080/` on 2026-10-01.
Removing duplicate database credentials from the private `.env` resolves the local migration authentication failure.
Migration exits successfully; PostgreSQL, backend, frontend, and OMR report healthy states.
The startup recovery serves speech assets, preserves database passwords and volumes, and does not start Telegram.
Local OMR repair on 2026-10-01 addresses the owner's exercises 32 and 33 without VPS changes.
Disabling indentation-based movement splitting keeps both systems of exercise 32 in one score.
A bounded threshold retry recovers an export for exercise 33 after faint staff detection fails.
The original images remain unchanged and uncommitted; both results require manager review.
Recognition errors remain: exercise 32 has clef and pitch errors; exercise 33 omits a measure and misreads notes.
See `docs/developer/omr-pipeline.md` for the repair evidence and remaining quality limits.
The repair passes 29 targeted backend tests, 22 frontend tests, all quality hooks, and the real container scale regression.
Local Chrome renders both repaired scores in manager review; neither score receives automatic approval.
The repair leaves the owner's Telegram container unchanged.
PHASE 5 OMR works locally, but its production acceptance remains open.
The owner reports a new VPS target; this task does not connect to or deploy on that host.
The previous VPS memory failure remains historical evidence, not a measurement of the new host.
The owner confirms PHASE 4 acceptance and authorizes complete PHASE 5 automation on 2026-09-30.
The owner reports unlinking Telegram; this phase does not restore that association.
The previous VPS check records approximately 18 GiB free disk space after owner cleanup.
That host has approximately 116 MiB available RAM, no swap, and no noninteractive sudo access at the recorded check.
The owner confirms all PHASE 3 checks and authorizes complete PHASE 4 automation on 2026-09-29.
The application 404 page is scheduled in PHASE 7.
The owner confirms all PHASE 2 checks and authorizes the complete PHASE 3 without intermediate confirmations on 2026-09-29.
The owner confirms all PHASE 1 manual checks on 2026-09-29.
The owner authorizes the entire PHASE 2 without intermediate confirmations on 2026-09-29.
Manual checks follow the complete implementation.
PHASE 0 is complete with owner-confirmed deployed browser acceptance.
The owner confirms the requested local health-page and PostgreSQL restart scenarios on 2026-09-29.
The owner confirms the remaining bot checks and continuation on 2026-09-29.
PHASE 0.5 is complete; the failed PWA result remains unchanged.

## Plan for the current phase
- [x] Add deployment storage preflight and reserve checks.
- [x] Add translated application 404 content without changing API or protected-file errors.
- [x] Verify cookie, CSRF, upload, and proxy boundaries; add security headers.
- [x] Add structured logs and verify bounded rotation and worker readiness.
- [x] Add Python and JavaScript dependency audits.
- [x] Review documentation and complete the environment reference and missing guides.
- [x] Prepare the complete final VPS smoke checklist.
- [x] Run local tests, builds, audits, and quality hooks.
- [ ] Obtain successful remote CI for the PHASE 7 branch.
- [ ] Deploy a verified release after resolving the VPS capacity constraint.
- [ ] Complete the final smoke checklist in Chrome and Safari.

## Completed PHASE 6 plan
- [x] Add shared vocabulary and a strict MusicXML sequence parser.
- [x] Add offline OpenAI generation, AAC conversion, resumability, and manifest verification.
- [x] Generate, verify, and commit the real speech clips after private API-key configuration.
- [x] Add approved-only speech, tempo controls, cancellation, and score highlighting.
- [x] Preserve recorded-audio playback and journal boundaries.
- [x] Finish local checks and record their evidence.
- [x] Enable branch CI through the owner-created pull request #1.
- [x] Update user and developer documentation.
- [x] Obtain audible Chrome acceptance after clip generation; Safari acceptance remains open.

## PHASE 5 implementation and deferred acceptance
- [x] Add versioned OMR jobs, leases, retries, review, and protected MusicXML.
- [x] Package Audiveris and implement the bounded worker.
- [x] Add manager review, approved-score rendering, and localized note labels.
- [x] Measure actual recognition quality and verify local browser workflows.
- [ ] Deploy only when VPS memory capacity permits safe recognition.
- [x] Complete developer and user documentation.
- [ ] Obtain final manual acceptance after production activation.

## Completed PHASE 4 plan
- [x] Add manager linking, durable imports, role checks, and retry protection.
- [x] Add Telegram polling and reuse protected AAC storage.
- [x] Add the translated manager import interface.
- [x] Verify locally, publish, and replace only the existing bot poller on the VPS.
- [x] Complete documentation and the final manual checklist.

## Completed PHASE 3 plan
- [x] Add per-student pointers and listening sessions with migration `0004_listening`.
- [x] Add sequential/random selection and idempotent, beacon-safe event handling.
- [x] Add student playback, pause/resume, heartbeats, completion, and exit handling.
- [x] Add manager journal filters, pagination, deleted-exercise labels, and translations.
- [x] Complete local PostgreSQL, container, and actual Chrome tab-close scenarios.
- [x] Deploy and verify the exact release over public HTTPS.
- [x] Complete documentation and the final manual checklist.
- [x] Obtain owner acceptance after implementation.

## Completed PHASE 2 plan
- [x] Add exercise and media models, migration, CRUD, soft deletion, and atomic reordering.
- [x] Add bounded uploads, signature checks, original images, AAC conversion, and duration checks.
- [x] Add protected file endpoints and nginx byte-range delivery.
- [x] Add translated exercise forms, upload progress, previews, and drag-and-drop controls.
- [x] Complete browser scenarios, container verification, and deployment.
- [x] Complete documentation and the final manual checklist.
- [x] Obtain owner acceptance after the complete implementation.

## Completed PHASE 1 plan
- [x] Add typed users, sessions, login budgets, and migration `0002_auth`.
- [x] Add scrypt authentication, secure cookies, sliding expiry, CSRF, and login limits.
- [x] Add startup emergency synchronization and all required lifecycle cases.
- [x] Add manager-only user administration, password resets, and session revocation.
- [x] Add persisted language/naming settings and obligatory password changes.
- [x] Add translated login, role guards, user administration, and settings forms.
- [x] Complete automatic browser scenarios and the deployed release verification.
- [x] Complete documentation and the final manual checklist.
- [x] Obtain owner acceptance after the complete implementation.

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
- PHASE 6 adds shared localized vocabulary, duration parsing, rests, ties, accidentals, and explicit unsupported-score errors.
- Speech uses the Web Audio clock with bounded playback rates, silent tails, tempo controls, and score highlighting.
- Current approval and job version are checked before every start.
- Speech and recorded audio stop each other without changing recorded-audio completion.
- Exit, hidden tabs, logout, score changes, and settings changes cancel pending and scheduled speech.
- The offline generator produces bounded AAC assets with resumable receipts and an atomic verified manifest.
- Conversion tests replace only the OpenAI transport and use real ffmpeg.
- Local checks pass 125 backend tests, 128 frontend tests, and 38 deployment/container tests.
- The 9 generation tests pass with real committed assets; missing assets now fail instead of skipping verification.
- The frontend production build and all 6 pre-commit checks pass.
- Headless Chrome verifies 8 seconds, 4 spoken attacks, silent rests and tails, and 7 written cursor positions.
- That browser check uses synthetic signals; it does not verify actual pronunciation or speaker output.
- Source commits `2a7d008`, `a86e4fa`, and `8285252` belong only to `feat/phase6-spoken-notes`.
- The last fix coordinates speech with manager audio previews as well as student recordings.
- The owner resolves the initial key and PR blockers on 2026-10-01.
- Commit `39545ef` adds 66 real OpenAI speech clips, 66 receipts, and the verified manifest.
- AAC data totals 600676 bytes; the frontend build includes the complete verified set.
- Chrome decodes all 66 clips and verifies 24-second schedules in all 6 language and naming combinations.
- Each schedule contains 15 clips, all accidental suffixes, and a silent final rest.
- Natural quarter notes fit 72 BPM in every combination; actual pronunciation still requires owner acceptance.
- Pull request #1 starts CI; run `36816378757` passes for the earlier source `2782422`.
- Read [the PR checks](https://github.com/mordanov/solfeo-exercises/pull/1/checks) for the current branch result.
- No merge to main, image publication, or deployment occurs.
- Cleanup removes the stopped phase-six browser profile; temporary browser and frontend processes remain stopped.
- `docs/developer/spoken-notes.md` and the student guide contain regeneration and final audible acceptance steps.
- PHASE 5 source `be0000d1e8208489b65fc939b77e1bbb013422e7` passes CI run `36674676116`.
- Run `36675174373` publishes both immutable images and verifies the pulled x86-64 images.
- Its deployment job stops with `OMR_MEMORY_INSUFFICIENT` before image pulls, service changes, or migration.
- Before/after snapshots match all VPS container IDs, start times, image references, and release state.
- Public health remains available; production schema remains `0005_telegram`.
- The job removes temporary registry and SSH credentials after the blocked deployment.
- The verified bundle remains available for an operator-approved retry after provisioning RAM.
- PHASE 5 passes 117 backend tests, 92 frontend tests, and 38 deployment/container tests locally.
- All 6 pre-commit checks pass; the production frontend build also passes.
- PHASE 5 adds migration `0006_omr`, image-bound jobs, expiring claim tokens, retries, and explicit manager review.
- Upload transactions enqueue recognition; replacement and rerun invalidate previous scores.
- Student MusicXML access requires current approval; original images remain available.
- OpenSheetMusicDisplay renders scores, with optional localized lyrics and explicit rendering-error fallback.
- The worker uses pinned Audiveris, a 512 MiB Java heap, a 1024 MiB container limit, and one CPU.
- A native-library failure reveals that JavaCPP needs executable mappings in its bounded temporary filesystem.
- The final container check uses `exec` on that mount and succeeds without network access.
- The local browser verifies actual recognition, side-by-side review, approval, rejection, original fallback, and localized note labels.
- Synthetic scale recognition is 100 %; rhythm recognition is 57.14 %; the accidentals fixture produces no export.
- Private images 1 and 7 reproduce the earlier event sequences; image 6 still fails.
- The measured worker peak is 325550080 bytes; this is not a safe maximum for larger inputs.
- The deployment guard requires 1536 MiB available host memory with default limits.
- The latest VPS check finds approximately 116 MiB available, so activation must wait.
- Only identified obsolete local Solfeo images and cache records are removed during build-space recovery.
- The task does not stop unrelated services or change VPS swap, Telegram associations, or production exercises.
- Cleanup removes the isolated Chrome profile and disposable test database.
- All 5 services in the persistent local development stand remain healthy.
- PHASE 4 is active at `https://solfeo.miveralta.ru/manager/telegram` with `@solfeo_exercises_bot`.
- Source `3e898fc08771dfecfec43533b9ee8a329d4a4f5e` passes CI run `36633406979`.
- Run `36633989417` publishes and verifies both images; its initial deployment fails because the VPS disk fills.
- PostgreSQL temporarily cannot start; its schema remains `0004_listening` before recovery.
- Targeted removal of 8 unused historical Solfeo images restores space without deleting production volumes or files.
- The standard rollout script successfully deploys the same verified bundle through SSH and advances to `0005_telegram`.
- GitHub denies the CLI's request to rerun the failed job; its historical failure remains visible.
- Public HTTPS Chrome verifies linking-code UI, private previews, byte ranges, exercise creation, confirmed replacement, image retention, reload, and logout.
- Independent verification confirms immutable images, bot identity, live polling, readiness, private media mounts, and registry credential cleanup.
- A targeted product-worker restart preserves the durable offset and synthetic import references.
- Shared commit `87fd752` removes only the prototype poller's automatic registration.
- The prototype stays stopped; all its saved audio remains byte-identical.
- All 43 unrelated VPS containers retain exact IDs and start times.
- Product PostgreSQL retains its container ID and data; its start time changes during disk recovery.
- The browser scenarios retain 3 soft-deleted synthetic exercises and 4 synthetic imports, including 2 unused fixtures from a timing retry.
- Both synthetic manager accounts are inactive.
- Cleanup removes the isolated browser profile and disposable local test database.
- The persistent development stand and all 4 product services remain healthy.
- PHASE 4 passes 98 backend tests, 76 frontend tests, and 36 container/release checks locally.
- Local Chrome verifies code generation, AAC preview and seeking, new exercises, confirmed audio replacement, image retention, reload, and logout.
- Simulated Telegram transport tests verify intake, actual conversion, durable offsets, duplicate updates, retry recovery, and notifications.
- Bot startup identity and webhook checks pass against the real Telegram service.
- The private product configuration contains the existing token; only the product worker polls the bot.
- Headless Chrome reports a host audio-renderer error; `--disable-audio-output` permits real decoding and timeline verification.
- The common AAC format remains unchanged; the unsuccessful sample-rate experiment is removed.
- PHASE 3 adds student listening and the manager journal.
- Source `e141b75c803ad56733731965056ef969f0e22c8a` passes CI run `36621440972` and publication/CD run `36621939822`.
- The pulled immutable images pass all 35 container/release checks before deployment.
- Public HTTPS Chrome verifies selection, pause/resume, completion, actual tab closure, journal filters, and retained deleted exercises.
- The tab-close terminal beacon arrives; the journal shows one completed session and one incomplete session.
- Independent VPS checks confirm exact image provenance, migration compatibility, private media, retained journal rows, and registry credential cleanup.
- All 45 other VPS containers retain their exact IDs and start times.
- The 2 synthetic production exercises remain soft-deleted; their 2 journal rows and media remain intact.
- Both synthetic accounts are inactive; real accounts and exercises remain unchanged.
- Cleanup removes isolated Chrome, its temporary profile, and the disposable test database.
- The local development stand and both public health endpoints remain healthy.
- PHASE 3 passes 87 backend tests, 72 frontend tests, and 35 container/release checks locally.
- Real Chrome verifies random history, sequential persistence, pause/resume, heartbeats, completion, and actual tab closure.
- The local journal retains the interrupted session after deletion and supports student/exercise filters.
- Explicit quality checks pass Ruff, mypy strict, ESLint, Prettier, TypeScript, and frontend builds.
- PHASE 2 adds exercise management at `https://solfeo.miveralta.ru/manager/exercises`.
- Publication/CD run `36609836972` succeeds for source `61ed497df1c2bc295363df1f59248f76f251c14c`.
- The published immutable images pass all 34 container/release checks before deployment.
- Public HTTPS Chrome repeats creation, a 3 MiB image upload, Opus conversion, playback, seeking, editing, reordering, reload, and deletion.
- Independent HTTPS checks confirm authenticated byte ranges, anonymous denial, and rejection of direct internal-file URLs.
- The 2 synthetic production exercises remain soft-deleted with their original images and converted audio.
- Independent VPS verification confirms release provenance, `0003_exercises`, private volume ownership, read-only nginx access, and registry credential cleanup.
- All 45 other VPS containers retain their exact IDs and start times, including PostgreSQL, shared nginx, and both prototypes.
- Cleanup stops isolated Chrome, removes its temporary profile, and removes the disposable test database.
- The local development stand remains healthy with its persistent database and media volumes.
- PHASE 2 implementation uses migration `0003_exercises`, protected persistent media, and translated manager forms.
- Source `61ed497df1c2bc295363df1f59248f76f251c14c` passes CI run `36609358064`.
- The suites pass 77 backend tests, 57 frontend tests, and 34 container/release checks.
- Real Chrome 154.0.8037.58 completes local uploads above 1 MiB, Opus conversion, playback, seeking, editing, reordering, and soft deletion.
- Container tests verify original bytes, protected GET/HEAD, normal/suffix/invalid ranges, restart persistence, and denial after deletion.
- Backend tests cover Opus, Ogg, MP3, WAV, AAC, M4A, PNG, JPEG, and WebP.
- Additional checks cover malformed media, byte/pixel/duration limits, chunked requests, permission boundaries, and atomic replacement.
- A replacement regression identifies a foreign-key ordering error; media inserts now complete before exercise updates.
- The shared proxy change `fb55be7` delegates upload limits to the product proxy and permits conversion time.
- Shared nginx validates and reloads without container recreation; its rebuilt image preserves the updated templates.
- The preceding PHASE 1 release uses source `481c72b0cb137aa512798172f377e89e2aca42d8`.
- CI run `36593904877` and publication/CD run `36594338338` succeed.
- The PHASE 1 suites pass 62 backend tests, 46 frontend tests, and 33 deployment/release checks.
- Real Chrome 154.0.8037.58 completes the manager/student workflow locally and over public HTTPS.
- The scenarios cover user creation, obligatory password change, all 3 languages, saved naming, role denial, reset, revocation, activation, and logout.
- The public browser check waits for user-list loading before editing; its first attempt identifies a test-harness timing issue.
- All 4 synthetic VPS accounts remain inactive; their generated passwords do not enter logs or Git.
- The 2 synthetic local accounts remain inactive.
- Cleanup removes the disposable test database and isolated Chrome profile; the development stand remains running.
- The private VPS configuration contains the generated `recovery-manager` credentials and HTTPS-only authentication settings.
- The emergency password remains only in `~/solfeo-production/.env.production`; the operator retrieves it through trusted SSH.
- Independent verification confirms exact image digests, `0002_auth`, secure settings, private network boundaries, and removal of temporary registry credentials.
- All 45 other containers retain their IDs and start times, including PostgreSQL, shared nginx, the PWA, and the Telegram worker.
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
- The owner confirms Chrome/Safari, RU/EN/ES, status refresh, and failure/recovery checks on the deployed PHASE 0 health page.
- PHASE 0 closes with successful CI, targeted CD, updated documentation, and owner acceptance.
- The initial PHASE 0 release uses source `13a081745a8cf0a5804f75f9a5831c0e9e7f4137`.
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
- Review and merge `feat/phase7-hardening` only after successful remote CI.
- Provision enough available RAM for `OMR_MEMORY_MB + OMR_HOST_RESERVE_MB` before production activation.
- Preserve the configured disk reserve and deploy only the verified immutable release.
- Complete `docs/developer/smoke-check.md` in Chrome and Safari after deployment.
- Confirm audible Safari acceptance with the existing speech clips; do not regenerate them.
- Preserve prototype files and the historical PWA deployment.

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

## Final PHASE 1 manual acceptance
- [x] Sign in as a manager in Safari and Chrome.
- [x] Create a student and complete the obligatory password change.
- [x] Confirm language and naming persistence after reload and a new sign-in.
- [x] Confirm student denial at `/manager/users`.
- [x] Confirm password reset, deactivation/reactivation, and logout behavior.

The owner confirms all PHASE 1 checks on 2026-09-29.
Chrome automation covers these scenarios separately.
Safari 26.6.2 refuses WebDriver sessions until Allow Remote Automation is enabled.
The task does not change that system permission or claim automated Safari success.

## Final PHASE 2 manual acceptance
- [x] Create an exercise with a real Opus file and image in Chrome and Safari.
- [x] Play and seek forward and backward after conversion.
- [x] Edit metadata and replace attachments.
- [x] Reorder exercises by dragging or buttons; confirm the order after reload.
- [x] Confirm soft deletion and explicit errors for invalid or missing files.
- [x] Confirm student denial at `/manager/exercises`.

The owner confirms all PHASE 2 checks on 2026-09-29.

## Final PHASE 3 manual acceptance
- [x] Complete the first audio exercise and interrupt the second by closing the tab.
- [x] Confirm completed and incomplete sessions in the manager journal.
- [x] Confirm pause/resume uses one row and replay after natural completion uses another.
- [x] Check sequential persistence, random selection, Previous, and no automatic playback.
- [x] Check journal filters and retention after exercise deletion.
- [x] Confirm student denial at `/manager/journal` in Chrome and Safari.

The owner confirms all PHASE 3 checks on 2026-09-29.

## Final PHASE 4 manual acceptance
- [x] Link a normal manager account to the bot.
- [x] Import real voice, forwarded audio, and audio documents.
- [x] Create an exercise and replace another exercise's audio.
- [x] Play and seek in Chrome and Safari; confirm original-image and journal retention.
- [x] Check unsupported input, size errors, and retry behavior.
- [x] Confirm unlinking and student denial.

The owner confirms all PHASE 4 checks, Telegram unlinking, and VPS disk cleanup on 2026-09-30.

## Final PHASE 5 manual acceptance
- [ ] Review and approve a real image in Chrome and Safari.
- [ ] Confirm original-image fallback before approval and after rejection or replacement.
- [ ] Check note labels for letters and solfège in all 3 languages.
- [ ] Toggle labels during audio playback without interrupting the listening session.
- [ ] Check failed recognition, retry, and student permission boundaries.

Production deployment and owner acceptance remain pending.

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
The final PHASE 5 procedure is in `docs/user/manager.md`.

## Known issues
- PHASE 6 audible Safari acceptance remains open; Chrome acceptance is confirmed on 2026-10-01.
- PHASE 7 production activation and the final VPS smoke check remain open.
- Merged PHASE 6 publication run `36867434244` fails deployment at the OMR RAM guard.
- Native Chrome DOM automation times out; local HTTP and React tests do not replace final browser acceptance.
- The owner-created PR resolves the initial CI blocker without changing CLI permissions.
- The previous VPS check finds approximately 18 GiB free disk space but insufficient RAM for PHASE 5 activation.
- The owner postpones deployment and reports a new host; this task does not verify or change that host.
- The initial PHASE 4 CD attempt fails from disk exhaustion; the verified SSH recovery succeeds.
- The current CLI cannot rerun Actions jobs with its token; GitHub returns a permission error.
- The owner confirms real Telegram acceptance and subsequently unlinks the association.
- Image 6 produces no MusicXML; image 7 receives 46 % recognition.
- Images 8 and 9 receive 95.35 % and 88 %, with important errors despite their `fully recognized` labels.
- Local artifacts are under `prototypes/omr/output/20260928T201957Z-84f49a71/`.
- Files evidence is under `prototypes/files/output/curl-20260928T204244Z-ec7ed479/`.
- The owner reports completion of the files manual step; device versions and the test setup are not recorded.
- Basic authentication remains a disposable prototype mechanism; PHASE 1 uses independent product session cookies.
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
- Anonymous language selection remains temporary; authenticated language and note naming now persist per user.
- Product CD and public nginx integration are active; the owner confirms final VPS acceptance.
- The PHASE 0 image cannot recognize `0002_auth`; rollback across that schema boundary requires a compatible forward fix.
- PHASE 1 images cannot recognize `0003_exercises`; PHASE 2 recovery requires a compatible image.
- PHASE 2 images cannot recognize `0004_listening`; PHASE 3 recovery requires a compatible image.
- PHASE 3 images cannot recognize `0005_telegram`; PHASE 4 recovery requires a compatible image.
- PHASE 4 images cannot recognize `0006_omr`; recovery after that migration requires a compatible image.
- Schema-incompatible rollback stops the product services and requires operator recovery; no automatic database downgrade occurs.
- The current CLI credential cannot manage repository Actions secrets: the public-key API returns HTTP 403.
- The deployment job confirms valid SSH configuration and removes its temporary registry credentials.
- Development still uses the bootstrap database role; the separate production configuration does not.
