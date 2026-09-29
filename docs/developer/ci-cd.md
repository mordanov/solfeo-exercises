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

The backend job checks tests and the hashed dependency export.
It starts pinned PostgreSQL 17 with a disposable `solfeo_test` database.
The test fixture refuses any other database name.
The job verifies migration upgrade, downgrade, repeated upgrade, the current revision, and model drift.
Its fixed test password belongs only to the disposable CI service, not a deployed database.
The frontend job checks tests and the production build, including its TypeScript compilation.
The container job generates a private password, builds both images, and runs the migration service.
It verifies the schema revision and health through nginx.
It also runs `deploy/tests` against a separate production Compose project using the freshly built images.
Those checks verify restricted database roles, private ports, migration metadata isolation, persistence, and failed-migration recovery.
It stops its Compose project after the checks.

The HTTP health endpoint remains independent of database readiness.
Pre-commit selects product files only; prototype workflows remain independent.
All 6 hooks reject deliberate defects during local verification and pass after removal of those temporary files.

## Deployment boundary

The CI workflow neither publishes images nor connects to the VPS.
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

| Image | Active digest reference |
|---|---|
| Backend | `ghcr.io/mordanov/solfeo-backend@sha256:fc311fdb42c7b13a09eaca4667718a414cac48e2d349c414f5ca5bfc2d1dc16e` |
| Frontend | `ghcr.io/mordanov/solfeo-frontend@sha256:9bb783a2af4f422de9f419097344800367c1b9fcc68c4fb1ad00989c9307a4cd` |

Independent checks confirm these references, schema heads, public HTTPS, private network boundaries, and removal of temporary registry credentials.
All 44 existing VPS containers retain their IDs and start times.
Chrome 154.0.8037.58 passes the deployed page, 3 languages, browser-only API failure, and recovery.
The owner confirms Chrome/Safari, language switching, status refresh, and failure/recovery on 2026-09-29.
PHASE 0 is complete; owner-tested browser versions and per-browser evidence are not supplied.
