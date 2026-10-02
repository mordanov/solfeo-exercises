# CI and deployment scope

This document explains the checks and deployment boundaries for the current product skeleton.

Prerequisites:
- Read `docs/developer/setup.md`.
- Read `docs/STATUS.md` before deployment work.

## Current CI

`.github/workflows/ci.yml` runs on relevant pull requests, pushes to `main`, and manual dispatch.
It uses read-only repository permissions.
The `checks` job runs `.pre-commit-config.yaml` with `--all-files`.
It checks Ruff, formatting, strict mypy, ESLint, Prettier, and TypeScript with the same commands used before local commits.
Python tools come from `uv.lock`; frontend tools come from `package-lock.json`.
The JavaScript hooks use isolated Node.js 22.23.3 and npm 12.1.0.
Changes to the hook configuration trigger CI.
Documentation changes also trigger CI.
Backend documentation tests check guide completeness, links, sentence lengths, and the environment reference.
The dependency job audits all installed locked Python packages and the complete npm lock.
`pip-audit --strict` and `npm audit --audit-level=low` fail on known advisories.
Unavailable audit services fail explicitly rather than silently passing.
The Python auditor is a development dependency and never enters the runtime image.

The backend job checks tests and the hashed dependency export.
It starts pinned PostgreSQL 17 with a disposable `solfeo_test` database.
The test fixture refuses any other database name.
The job verifies migration upgrade, downgrade, repeated upgrade, the current revision, and model drift.
Its fixed test password belongs only to the disposable CI service, not a deployed database.
The frontend job checks tests and the production build, including its TypeScript compilation.

Vitest limits execution to 2 workers for consistent local and CI resource use.
The default 5 s test timeout remains unchanged.
Use `npm test` without a special local worker override.

Speech tests mock only the OpenAI transport and perform real AAC conversion.
A mandatory check verifies all 66 committed speech files, receipts, and the manifest.
Missing or damaged assets fail CI instead of skipping verification.
Synthetic conversion tests do not establish voice quality.

The container job generates a private password, builds both images, and runs the migration service.
It verifies the schema revision and health through nginx.
It also runs `deploy/tests` against a separate production Compose project using the freshly built images.
Those checks verify restricted database roles, private ports, migration metadata isolation, persistence, and failed-migration recovery.

The production permission test compares database metadata with the migration head in the built backend image.
It does not hard-code a previous feature's revision.
It stops its Compose project after the checks.

The HTTP health endpoint remains independent of database readiness.
Pre-commit selects product files only; prototype workflows remain independent.
All 6 hooks reject deliberate defects during local verification and pass after removal of those temporary files.

## Deployment boundary

The CI workflow neither publishes images nor connects to the VPS.
The owner merges [pull request #1](https://github.com/mordanov/solfeo-exercises/pull/1) on 2026-10-01.
Source `f3ba47f` passes main-branch CI run `36866682091`.
Publication run `36867434244` verifies the images, but deployment stops with `OMR_MEMORY_INSUFFICIENT`.
The owner explicitly removes the host-memory deployment gate on 2026-10-01.
New rollouts retain disk checks, health verification, and compatible rollback.
Pull request #2 merges as `165a1397` on 2026-10-01.
Publication run `36921037861` completes publishing and the production deployment successfully.
The public HTTPS health endpoint returns `{"status":"ok"}`.
The owner accepts PHASE 5 and PHASE 6, then confirms final PHASE 7 acceptance on 2026-10-01.
The existing prototype publishing workflows remain separate.
`deploy/compose.prod.yaml` provides a separate, image-based production configuration.
See `docs/developer/deploy.md` for its role boundaries and operational requirements.
`cd.yml` performs targeted VPS rollout after successful publication.
The owner confirms the separate final browser acceptance gate on 2026-09-29.

Do not run the shared infrastructure's general deployment for a scoped product change.
Plan the named services, nginx routes, migration order, and rollback before the first product deployment.
Preserve the active Telegram prototype, its data, and unrelated services.

## Product release publication

`.github/workflows/publish-product.yml` runs after successful main-branch CI or through manual dispatch.
It accepts only this repository's `main` branch and an exact commit with successful push or manual CI.
Pull-request CI does not authorize publication.
Manual publication also requires a successful CI run for the exact selected commit.
Run Product CI manually first if a documentation-only commit has no matching CI run.

The workflow builds x86-64 images for the VPS:
- `ghcr.io/mordanov/solfeo-backend`
- `ghcr.io/mordanov/solfeo-frontend`

Only the publishing job has `packages: write`.
It uses `GITHUB_TOKEN`; no personal registry credential is required for publication.
The images have source-revision labels and `sha-<commit>` tags.
Deployment references use registry digests, not those mutable tags.

After publishing, the workflow pulls both images by digest and checks their source labels.
It runs the production Compose scenarios against those pulled images.
It emits a release bundle only after all those checks pass.
A failed check can leave registry images, but it does not produce a verified release bundle.

The artifact name is `solfeo-release-<source-sha>` and its retention is 30 days.
It contains `solfeo-release.tar.gz` with exactly these files:
- `release.json`
- `deploy/compose.prod.yaml`
- `deploy/compose.proxy.yaml`
- `deploy/postgres-init.sh`
- `.env.example`

`release.json` records format version, repository, source commit, CI run ID, image digests, and deployment-file SHA-256 hashes.
The bundle excludes `.env`, prototype files, media, and unrelated repository content.
The builder rejects mutable image references, unsafe symlinks, and non-executable bootstrap scripts.
It normalizes file ownership and does not overwrite an existing artifact.

Download the artifact from a successful publication run, not from an arbitrary branch or run.
The rollout verifies provenance and hashes before SSH and again on the server.
The publication workflow calls the separate deployment job only after verified artifact creation.
Image publication alone does not establish successful VPS deployment.

## Targeted CD

`publish-product.yml` calls reusable `.github/workflows/cd.yml` with the exact source SHA and CI run ID.
The deployment job downloads the artifact from that same workflow run.
It rejects stale source commits, configures pinned SSH, and verifies server prerequisites.
It never prints the SSH identity or host-key contents.
It uploads the deployment scripts and verified bundle to `~/solfeo-production/incoming`.
It uses temporary GHCR credentials instead of changing the account's existing Docker login.
The final cleanup removes those credentials.

The VPS must already contain private `.env.production` and the shared proxy network.
Rollout and rollback operate only on the separate product project.
The script verifies the schema, frontend HTML, and HTTPS health before promoting the release.
A failed update returns a failed job even when recovery succeeds.
See `deploy.md` for compatibility limits, private diagnostics, and operator recovery.

## Deployment prerequisite report

A separate job reports only whether the required SSH secrets are present.
It does not print their values, test connectivity, or contact the VPS.
Missing secrets appear as `DEPLOYMENT_SETUP_REQUIRED`, not as a successful deployment.

| Secret | Required value |
|---|---|
| `VPS_HOST` | The intended SSH host |
| `VPS_USER` | The deployment account |
| `VPS_SSH_KEY` | A deployment private key authorized for that account |
| `VPS_KNOWN_HOSTS` | Host-key entries from an already trusted source |

The deployment accepts optional `VPS_PORT`, with port 22 as its default.
Use the repository's Settings > Secrets and variables > Actions page to configure these values.
Do not send private keys in chat or commit them.
Do not replace pinned host verification with an unverified `ssh-keyscan`.
The current CLI credential receives HTTP 403 for repository secret management, so it cannot provision missing secrets.

## First verified product release

Publication run [`36572516719`](https://github.com/mordanov/solfeo-exercises/actions/runs/36572516719) succeeds on 2026-09-29.
Its source commit is `03260e554b13c23b640ef6432775c50b331a7a39`.
The matching CI run is `36572315149`.

| Image | Verified digest reference |
|---|---|
| Backend | `ghcr.io/mordanov/solfeo-backend@sha256:8ace159a2b2fd0d3ca77a1b61bdd414611ca8eabe3d26bf3596c3d99d1f275e0` |
| Frontend | `ghcr.io/mordanov/solfeo-frontend@sha256:d3109a2492538e60ef075d34f7053f33e6ec180c52ce8148430062c449b23929` |

The runner pulls these images and passes all 16 release and production-configuration checks.
The downloaded artifact matches all 3 deployment-file hashes and preserves the bootstrap executable mode.
The prerequisite report finds all 4 required SSH secrets unavailable in the repository workflow context.
That first publication does not connect to SSH or deploy the application.
The owner subsequently confirms secret setup; the new deployment job verifies actual connectivity.

## First deployed product release

CI [`36585295551`](https://github.com/mordanov/solfeo-exercises/actions/runs/36585295551) succeeds for source `13a081745a8cf0a5804f75f9a5831c0e9e7f4137`.
Publication and CD [`36585683212`](https://github.com/mordanov/solfeo-exercises/actions/runs/36585683212) succeed on 2026-09-29.
All 30 release and production checks pass before the SSH deployment.
The deployment validates real SSH credentials and the pinned host key.

| Image | Initial PHASE 0 digest reference |
|---|---|
| Backend | `ghcr.io/mordanov/solfeo-backend@sha256:fc311fdb42c7b13a09eaca4667718a414cac48e2d349c414f5ca5bfc2d1dc16e` |
| Frontend | `ghcr.io/mordanov/solfeo-frontend@sha256:9bb783a2af4f422de9f419097344800367c1b9fcc68c4fb1ad00989c9307a4cd` |

Independent checks confirm these references, schema heads, public HTTPS, private network boundaries, and removal of temporary registry credentials.
All 44 existing VPS containers retain their IDs and start times.
Chrome 154.0.8037.58 passes the deployed page, 3 languages, browser-only API failure, and recovery.
The owner confirms Chrome/Safari, language switching, status refresh, and failure/recovery on 2026-09-29.
PHASE 0 is complete; owner-tested browser versions and per-browser evidence are not supplied.

## Deployed PHASE 1 release

Source `481c72b0cb137aa512798172f377e89e2aca42d8` completes PHASE 1 implementation on 2026-09-29.
CI [`36593904877`](https://github.com/mordanov/solfeo-exercises/actions/runs/36593904877) succeeds.
Publication and CD [`36594338338`](https://github.com/mordanov/solfeo-exercises/actions/runs/36594338338) succeed.
The suites pass 62 backend, 46 frontend, and 33 deployment/release checks.

| Image | PHASE 1 digest reference |
|---|---|
| Backend | `ghcr.io/mordanov/solfeo-backend@sha256:b43d285569d9de5d74c9f0e7f8ba82ac44eb70f3e5b325e964aa75b148c35265` |
| Frontend | `ghcr.io/mordanov/solfeo-frontend@sha256:499fea60aa30323fa6b55b387594e4a1223b0bb26331cb9da1a936d2b6d2bf47` |

The migration advances the retained PostgreSQL volume to `0002_auth`.
All 45 other containers retain their IDs and start times.
Only the product backend and frontend change.
The bot and historical PWA remain healthy.

Chrome completes the account scenarios locally and through public HTTPS.
Those scenarios create users, change temporary passwords, persist preferences, enforce roles, reset passwords, revoke sessions, and verify activation and logout.
The automation deactivates its 4 synthetic VPS accounts and does not publish their passwords.
The operator retrieves emergency credentials only from private server configuration.
The owner confirms final PHASE 1 manual acceptance on 2026-09-29.
Local Safari automation remains unavailable; owner acceptance does not claim automated Safari coverage.

## Deployed PHASE 2 release

Source `61ed497df1c2bc295363df1f59248f76f251c14c` completes PHASE 2 implementation on 2026-09-29.
CI [`36609358064`](https://github.com/mordanov/solfeo-exercises/actions/runs/36609358064) succeeds.
Publication and CD [`36609836972`](https://github.com/mordanov/solfeo-exercises/actions/runs/36609836972) succeed.
The suites pass 77 backend tests, 57 frontend tests, and 34 container/release checks.
Publication repeats the container checks against the pulled immutable images.

| Image | Active digest reference |
|---|---|
| Backend | `ghcr.io/mordanov/solfeo-backend@sha256:211f886a15b94f988b473fa27c226bd3734976fcfa17ce5e1718c6658792e572` |
| Frontend | `ghcr.io/mordanov/solfeo-frontend@sha256:b08a515620c3a6d025977922772432ffa4a723d720065d08a5872a61f3205b79` |

The retained database advances to `0003_exercises`.
The backend and frontend share `solfeo-production_media_data`; frontend access is read-only.
Shared infrastructure commit `fb55be7` updates only the product route's upload forwarding and timeout.
The shared nginx image includes this change; a validated graceful reload updates the running container.
All 45 other containers retain their IDs and start times.
Both prototypes remain healthy.

Chrome completes the exercise workflow locally and through public HTTPS.
The scenario uploads a synthetic image above 1 MiB and a real encoded Opus fixture.
It verifies preview, AAC playback, seeking, metadata updates, reordering, persistence, soft deletion, and logout.
Independent requests verify 206 byte ranges, anonymous denial, and internal-location protection.
The automation leaves 2 soft-deleted production exercises and preserves their files.
It restores the emergency manager's settings and does not publish credentials.
The owner confirms all PHASE 2 checks on 2026-09-29.

## Deployed PHASE 3 release

Local suites pass 87 backend tests, 72 frontend tests, and 35 container/release checks.
Real Chrome verifies student selection, heartbeats, pause/resume, completion, actual tab closure, journal filters, and retained deleted exercises.
The container scenario verifies normal student session persistence and saved progress after a backend restart.
The publication workflow supplies `VITE_LISTENING_HEARTBEAT_MS=5000` to the frontend build.
Source `e141b75c803ad56733731965056ef969f0e22c8a` completes PHASE 3 implementation on 2026-09-29.
CI [`36621440972`](https://github.com/mordanov/solfeo-exercises/actions/runs/36621440972) succeeds.
Publication and CD [`36621939822`](https://github.com/mordanov/solfeo-exercises/actions/runs/36621939822) succeed.
Publication repeats all 35 container/release checks against the pulled immutable images.

| Image | Active digest reference |
|---|---|
| Backend | `ghcr.io/mordanov/solfeo-backend@sha256:824396d04493d6435b7eb2c1dc8a660f7747355e88575bffdbea2cdfdd4dda79` |
| Frontend | `ghcr.io/mordanov/solfeo-frontend@sha256:f49fc74d605ba8f9b7c127f8bd50fb352efbfb05c27cf40398ea7714fce19c4e` |

The retained database advances to `0004_listening`.
Independent VPS verification checks source labels, digest references, migration compatibility, private media mounts, journal retention, and registry cleanup.
All 45 other containers retain their IDs and start times.
No shared infrastructure change is necessary.

Public HTTPS Chrome repeats the complete listening and journal scenario.
The actual tab-close beacon arrives, and the journal retains one completed row and one incomplete row.
The scenario leaves 2 soft-deleted synthetic exercises, 2 retained journal rows, and 2 inactive synthetic accounts.
It does not change real accounts or exercises.
Cleanup removes the isolated browser profile and disposable test database.
The local development stand and public health endpoints remain healthy.

The owner confirms final PHASE 3 acceptance on 2026-09-29.
Safari automation remains unavailable because Allow Remote Automation is disabled.
The manual procedures appear in `docs/user/student.md` and `docs/user/manager.md`.

## Deployed PHASE 4 release

Local suites pass 98 backend tests, 76 frontend tests, and 36 container/release checks.
The worker uses the backend image; CI also checks `worker/` and its runtime HTTPX dependency.
Simulated Telegram responses exercise real PostgreSQL persistence, AAC conversion, retries, and durable offsets.
Local Chrome verifies the manager interface and protected preview without modifying real accounts or exercises.
Headless playback uses `--disable-audio-output` because the host audio renderer is unavailable.
This preserves real decoding and playback timing, not audible speaker verification.
Source `3e898fc08771dfecfec43533b9ee8a329d4a4f5e` passes
CI [`36633406979`](https://github.com/mordanov/solfeo-exercises/actions/runs/36633406979).
Run [`36633989417`](https://github.com/mordanov/solfeo-exercises/actions/runs/36633989417) publishes and verifies the immutable images.
Its deployment job fails because the VPS disk fills.
The historical workflow conclusion remains failure; do not describe that job as successful.

The disk failure temporarily prevents product PostgreSQL startup.
Recovery removes only 8 explicitly identified, unused historical Solfeo images.
No production volume, exercise, journal, or prototype audio is deleted.
The database retains `0004_listening` before the successful retry.
GitHub refuses the CLI's job-rerun request with a permission error.

The same standard rollout script retries the same verified bundle through trusted SSH.
It pulls the pinned references, applies `0005_telegram`, starts the product services, verifies health, and promotes the release.
The script reports `DEPLOYED:3e898fc08771dfecfec43533b9ee8a329d4a4f5e`.

| Service | Active digest reference |
|---|---|
| Backend and Telegram worker | `ghcr.io/mordanov/solfeo-backend@sha256:57ae1a00671c320dca1e44ee878d1eb1c069d2207cc1a9843cdf919b86da4032` |
| Frontend | `ghcr.io/mordanov/solfeo-frontend@sha256:3bb4b5795378e4fb9341832ad1a904cab230329ca0a337dfbf2127d7b263e8ce` |

Public HTTPS Chrome completes the manager import workflow.
Independent checks verify exact provenance, live bot identity, readiness, private storage, and registry credential cleanup.
A targeted worker restart preserves its offset and import references.
All 43 unrelated containers retain their IDs and start times.
Product PostgreSQL retains its container ID and data but restarts during disk recovery.

Shared commit `87fd752` removes only the prototype poller's automatic registration.
The prototype remains stopped; its retained audio hashes do not change.
The product worker alone uses the bot token.
The browser scenarios retain 3 soft-deleted exercises, 4 synthetic imports, and 2 inactive synthetic managers.
An initial browser timing failure leaves 2 of those imports unused.

Approximately 1.1 GiB remains available, with filesystem usage near 98 %.
Provide more capacity before another release.
The owner confirms final PHASE 4 acceptance, including real messages and Safari playback, on 2026-09-30.
Cleanup removes the isolated browser profile and disposable local test database.
The development stand remains healthy.
