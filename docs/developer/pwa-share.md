# PWA share prototype deployment

This document preserves the deployment and failure report for the superseded PWA sharing prototype.

Prerequisites:
- Read `docs/PRODUCT_BRIEF.md`, `docs/PHASES.md`, and `docs/DECISIONS.md`.
- Read `../web-projects/web-folders/documentation/onboarding.md`.
- Obtain approval before changing shared infrastructure or deploying.
- Obtain an Android device with Chrome, WhatsApp, and Telegram.

## Current state

The owner replaces product PWA audio sharing with the Telegram bot on 2026-09-29.
The Telegram path receives real audio, and the owner confirms successful playback.
PWA acceptance remains failed; the procedures below preserve the investigation rather than request further product acceptance.
See `docs/developer/telegram-bot.md` for the selected path.
This documentation change does not remove the deployed prototype, browser data, or certificate.

The owner approves the deployment plan on 2026-09-29.
The local prototype is implemented and verified.
The owner confirms publication and deployment permissions on 2026-09-29.
The owner supplies `https://solfeo.miveralta.ru` as the target hostname.
Shared configuration now includes the prototype site, service, and nginx templates.
DNS resolves to the existing VPS, and SSH access works.
The initial HTTPS check fails because the existing certificate does not cover the hostname.
The targeted deployment adds a valid certificate and passes public HTTPS checks.
The prototype runs at `https://solfeo.miveralta.ru/prototype-share/`.
The deployed diagnostic build comes from commit `d171be5`.
Android messenger sharing fails owner acceptance on 2026-09-29.
The page reports "No audio file was received" after a share from Telegram or WhatsApp.
The cause remains unconfirmed.

## Prototype scope

Use a static React, TypeScript, and Vite prototype under `prototypes/pwa/`.
Use react-i18next with Russian, English, and Spanish strings.
The receipt page shows the shared filename, type, size, and a clear-storage action.
It does not create exercises or upload audio.

The service worker handles the manifest's multipart POST share target.
It stores the file in IndexedDB before redirecting to the receipt page.
The manifest accepts `audio/*`, `.opus`, `.ogg`, and `application/octet-stream`.
It also maps text, title, and URL fields to diagnose shares without files.
The page must distinguish a completed receipt from empty input or a storage failure.

Keep file data and metadata on the device.
Do not add analytics, a backend, a database, Redis, product login, or exercise management.
Do not copy local exercise samples into the public image.
The originally planned browser login-return flow is superseded by Telegram audio import in PHASE 4.

### Routes

| Route | Purpose |
|---|---|
| `/prototype-share/` | Installable start page. |
| `/prototype-share/manifest.webmanifest` | Manifest and share-target configuration. |
| `/prototype-share/sw.js` | Service worker with scope `/prototype-share/`. |
| `/prototype-share/receive` | Multipart POST target handled by the service worker. |
| `/prototype-share/share` | Local file receipt page. |
| `/prototype-share/health` | Static deployment health check. |

Use the same prefix for the Vite base, manifest scope, start URL, and service-worker registration.
Limit the service worker to the prototype prefix, not the entire future product origin.
Do not cache API responses, protected files, or shared audio in Cache Storage.
The static server must reject an unhandled POST instead of claiming successful receipt.
The page must show when the service worker is ready before requesting an installation or share test.

## Local setup

Prerequisites:
- Use Node `22.12` or later within major version `22`, or the pinned Docker image below.
- Use Docker Compose for the static-server checks.

The local machine has Node 18, so verification uses Node 22 in Docker.
Do not share `node_modules` between host and container installations.
Native development dependencies depend on the operating system.

1. Open the prototype directory.

   ```sh
   cd prototypes/pwa
   ```

2. Create local configuration if necessary.

   ```sh
   cp -n .env.example .env
   ```

3. Install the locked dependencies with Node 22.

   ```sh
   npm ci --no-audit --no-fund
   ```

4. Run the checks.

   ```sh
   npm test
   npm run lint
   npm run format:check
   npm run build
   ```

For a machine without Node 22, use the following command instead of steps 3 and 4:

```sh
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
  --mount "type=bind,source=$PWD,target=/app" -w /app \
  node:22-bookworm-slim@sha256:43ac6c60b8f89723f746e8a92ce91abd5017e627ce1ddfe4238355d3a30b772c \
  sh -c 'npm ci --no-audit --no-fund && npm test && npm run lint && npm run format:check && npm run build'
```

5. Start the local static server.

   ```sh
   docker-compose up --build -d --wait
   ```

6. Open `http://127.0.0.1:18086/prototype-share/` in Chrome.

   The page reports readiness after the scoped service worker controls it.
   Chrome treats loopback addresses as secure contexts for local testing.
   An Android device still needs the planned HTTPS deployment.

7. Stop the local static server after testing.

   ```sh
   docker-compose down
   ```

Use `docker compose` when the plugin is available.
The measured environment uses standalone `docker-compose`.
The Dockerfile pins its Node and nginx base images.
`npm ci` uses `package-lock.json`; no installation script downloads the owner's sample files.

### Configuration and storage

| Variable | Default | Purpose |
|---|---|---|
| `VITE_DEFAULT_LANGUAGE` | `en` | Initial UI and manifest language: `en`, `ru`, or `es`. |
| `VITE_MAX_SHARE_BYTES` | `26214400` | Maximum size of a stored share: 25 MiB. |
| `VITE_SW_READY_TIMEOUT_MS` | `15000` | Maximum wait for service-worker control after registration. |
| `PWA_PORT` | `18086` | Localhost-only published port. |

Vite reads the UI settings from `.env` at build time.
Compose passes the same settings as build arguments.
Rebuild the image after changing them.
The Vite base and service-worker scope remain fixed at `/prototype-share/`.
The deployed manifest uses the build language; the page language selector changes the current page only.

The prototype stores exactly 1 file: the latest successful share.
It rejects multiple files rather than discarding extra files silently.
An invalid share or storage failure does not replace the previous successful share.
The receipt labels that file explicitly as the most recent successful share.
The clear action deletes it from IndexedDB.

The database name is `solfeo-pwa-prototype`.
Schema version 2 preserves version 1 files and adds a separate `attempts` store.
The prototype retains only the latest diagnostic attempt.
Successful receipt stores the file and its diagnostics in one transaction.
Failed receipt updates diagnostics without replacing the last successful file.
The separate clear actions remove the file or diagnostics independently.
The prototype validates the reported MIME type, extension, count, and file size.
It does not inspect magic bytes or claim that a file is valid audio.
This check is not the product upload-validation pipeline.
The 25 MiB limit applies after parsing the incoming browser form.
It is not a network upload limit.

The page uses no analytics, remote fonts, or server-side file storage.
The service worker intercepts only same-origin POST requests to `/prototype-share/receive`.
All other requests use normal browser networking.
No Cache Storage cache exists; offline shell support is outside this prototype.

### Local verification: 2026-09-29

All 28 tests pass.
TypeScript, ESLint, Prettier, and the production build pass.
The tests cover share errors, commit-before-redirect ordering, persistence, clearing, translated UI, manifest scope, and worker readiness.

An isolated desktop Chrome `154.0.8037.58` session verifies the built nginx image.
The test submits a synthetic file through an actual multipart form navigation.
It does not invoke the share handler directly.

| Check | Result |
|---|---|
| Worker control | `/prototype-share/sw.js`, scoped to `/prototype-share/`. |
| Manifest parsing | No Chrome manifest errors. |
| Successful share | Receipt shows `browser.opus`, `application/octet-stream`, and 23 bytes. |
| Page reload | Stored file remains available. |
| Empty share | Explicit error; previous successful file remains. |
| Clear and reload | No stored file remains. |
| `/api/audio` | `404`; the worker does not intercept it. |
| Cache Storage | No caches. |
| Direct POST without worker handling | nginx returns `405`. |
| Manifest icons | Served PNG dimensions match 192 and 512 pixel declarations. |
| Worker response header | `Cache-Control: no-store`. |
| Server access log | Browser share POSTs do not reach nginx. |

The local image ID is `sha256:3ab62986444bbb83ac6d02139629e8b59f6f24acfb170d1cc999c053943c613f`.
Evidence remains in ignored `prototypes/pwa/output/`:

- `browser-smoke.json`: actual browser observations.
- `static-checks.json`: served routes and cache headers.
- `nginx-access.log`: request evidence without file bodies.
- `post.headers`: rejection of the direct POST.
- `compose-up.log`: build and startup output.

These results do not prove Android installation or WhatsApp/Telegram interoperability.
The owner device checks remain open.

## Onboarding facts

These values describe the prototype, not the future production service layout.

| Fact | Proposal |
|---|---|
| Site ID | `solfeo-pwa-prototype` |
| Environment prefix | `SOLFEO_PWA_PROTOTYPE` |
| Domain and server name | `solfeo.miveralta.ru` |
| Service | `solfeo-pwa-prototype` |
| Container port | `80`, internal to the shared stack |
| Backend, database, worker, Redis | None |
| Health path | `/prototype-share/health` |
| Registry image | `ghcr.io/mordanov/solfeo-pwa-prototype:sha-<full-commit>` |
| Site priority | `190` |
| Public landing-page link | Disabled for the prototype |

The owner confirms the registry and deployment permissions.
Define all deployment variables in `.env.example`.
Never copy the files prototype's Basic credentials into this deployment.

## Deployment checklist

Follow the supplied onboarding guide after scope approval.
Treat database, Redis, and backend-only steps as explicitly inapplicable to this static prototype.

- [x] Build and test the local PWA before adding infrastructure references.
- [x] Create the required manifest, favicon, installation icons, and Apple touch icon.
- [x] Add the site entry to `web-folders/sites.yaml`.
- [x] Add the HTTP, HTTP-redirect, and HTTPS nginx templates.
- [x] Add the static container service and nginx dependency to the shared Compose file.
- [x] Add the domain variables to nginx and the shared `.env.example`.
- [x] Document the disabled landing-page link.
- [x] Prepare the prototype-only image publishing workflow and its onboarding template.
- [x] Confirm that no new mandatory CI placeholders apply.
- [x] Verify DNS and the existing certificate state.
- [x] Configure actual VPS variables through the approved deployment process.
- [x] Publish the image under a full commit tag.
- [x] Deploy only the prototype service and necessary nginx configuration.
- [x] Issue the hostname certificate through the shared certbot setup.
- [x] Verify the HTTPS health response, manifest, icons, and service-worker headers.
- [x] Confirm locally that unhandled POST requests return an error without retaining file bodies.

The publishing workflow supports only this prototype.
It does not replace the PHASE 0 product CI/CD work.
Do not restart unrelated applications.
Do not change the shared PostgreSQL configuration.

### Publication and targeted deployment

`.github/workflows/publish-pwa-prototype.yml` runs on relevant `main` changes or manual dispatch.
It runs the prototype checks before publishing an x86-64 image.
Build settings come from `prototypes/pwa/.env.example`.
The workflow publishes a full commit tag and reports the registry digest.
It does not deploy automatically or require VPS secrets.

Set these values in the shared VPS `.env`:

```dotenv
SOLFEO_PWA_PROTOTYPE_PRIMARY_DOMAIN=solfeo.miveralta.ru
SOLFEO_PWA_PROTOTYPE_SERVER_NAMES=solfeo.miveralta.ru
SOLFEO_PWA_PROTOTYPE_IMAGE=ghcr.io/mordanov/solfeo-pwa-prototype@sha256:<published-digest>
```

The `unpublished` default prevents accidental use of an unpinned image.
Pin the registry digest for deployment; commit tags identify the corresponding source.
Do not pass a temporary image override that disappears during the next deployment.

Warning: pushing shared `main` starts the general deployment workflow.
That workflow can restart unrelated applications.
Use a separate infrastructure branch for this targeted onboarding.
Preserve all unrelated VPS files and running services.
After verification, synchronize the reviewed changes to shared `main` with a one-time `[skip ci]` documentation commit.
This prevents the general deployment during synchronization.
It does not disable later workflow runs.

1. Apply the reviewed infrastructure commit with a fast-forward merge.
2. Set the 3 prototype values in the VPS `.env`.
3. Pull the configured prototype image.
4. Start only the prototype service.

   ```sh
   docker compose pull solfeo-pwa-prototype
   docker compose up -d --no-deps --wait solfeo-pwa-prototype
   ```

5. Build the shared nginx image with the new templates.
6. Validate its configuration before replacing nginx.
7. Recreate only nginx with `docker compose up -d --no-deps nginx`.
8. Issue the hostname certificate through the shared certbot webroot.
9. Wait for the certificate watcher to activate HTTPS.
10. Verify the public routes and all previously running services.

Do not run `deploy-one-db.sh` or the all-sites certificate script for this prototype.
No application database or migration applies.

For an image rollback, restore the previous digest in `.env`.
Repeat the targeted pull and start commands.
For initial onboarding failure, stop the prototype and restore the previous nginx image, manifest, and domain configuration.
Do not reset the shared repository or restart unrelated services.
The static prototype must not retain uploaded request bodies or log their contents.

### Initial HTTPS verification: 2026-09-29

The image publication workflow succeeds:
[`36528824725`](https://github.com/mordanov/solfeo-exercises/actions/runs/36528824725).
The VPS runs the x86-64 image by registry digest, not by a mutable tag.

| Item | Verified value |
|---|---|
| Application source | `8efc058e69e6a5ff28a6f7d13b5adc4185354473` |
| Published tag | `ghcr.io/mordanov/solfeo-pwa-prototype:sha-8efc058e69e6a5ff28a6f7d13b5adc4185354473` |
| Deployed digest | `sha256:b780e044a9cc0a4093957d40dee1476f5b1c5a31f33ca5d639179e16c3871c99` |
| Infrastructure commits | `900f62e` and `4578b73`, on shared `main` and the VPS |
| TLS certificate expiry at issuance | `2026-12-28` |
| Static files | All 12 match the locally validated build |
| Unrelated containers | All 41 retain their IDs and start times |

The existing certbot service handles renewals.
The nginx watcher activates HTTPS after its 300 s polling interval.
The previous nginx image remains available as `web-folders-nginx:before-solfeo-pwa` for an initial rollback.
No unrelated VPS files change.

All 17 public HTTP checks pass with normal certificate validation.
They cover redirects, health, manifest scope, declared PNG dimensions, worker cache headers, HEAD requests, unknown paths, and POST rejection.
The proxy rejects POST before accepting a body through `100 Continue`.
The static container receives no POST requests.

Desktop Chrome `154.0.8037.58` reports no manifest or installability errors.
Actual multipart navigation stores a synthetic 23-byte file and opens the receipt.
Reload preserves it; a failed share preserves the prior success; clearing persists after reload.
The worker scope remains `/prototype-share/`, and Cache Storage remains empty.
The proxy receives no browser share POSTs.

The first browser assertion races asynchronous receipt loading.
The test waits for that loading to finish before checking the preserved file.
No application change is necessary.

Local evidence remains in ignored `prototypes/pwa/output/https-static-checks.json` and `https-browser-smoke.json`.
The isolated browser and temporary local containers stop after verification.
These results do not prove Android installation or messenger compatibility.

## Validation plan

Write failing tests before implementing share handling.
Cover valid files, empty shares, rejected input, IndexedDB errors, and redirect-after-storage ordering.
Cover receipt-page errors, storage clearing, and identical nonempty locale keys.
Run Vitest, Testing Library, TypeScript, ESLint, Prettier, and the production build.
Check manifest paths and service-worker scope against the deployed prefix.

Automated tests do not prove Android installation or messenger interoperability.
The following owner checks remain mandatory.
The device procedure also appears in `docs/user/pwa-prototype.md`.

### Failed Android acceptance: 2026-09-29

The owner does not confirm acceptance.
Telegram or WhatsApp opens the prototype, but the receipt reports "No audio file was received".
The owner suggests that the messenger shares a message containing audio rather than an audio file.
This explanation remains a hypothesis.

`handleShare()` returns `EMPTY_SHARE` when `form.getAll("audio")` contains no entries.
This condition does not establish whether another field contains a file or whether the messenger supplies only text.
The current manifest requests files but does not map text, title, or URL fields.
The desktop test supplies an `audio` field explicitly and cannot reproduce the unknown Android payload.

The owner approves the diagnostic task by requesting continuation.
The implementation includes:

- Regression tests for text-only, blank, empty, mixed text/file, and unexpected file-field input.
- Manifest mappings for text, title, and URL parameters.
- A `diagnostics v1` section, separate from the last successful file.
- Field categories, file counts, MIME types, byte sizes, and empty/nonempty text indicators.
- Distinct `TEXT_ONLY_SHARE`, `EMPTY_SHARE`, and `UNEXPECTED_FILE_FIELD` outcomes.
- Preservation of the previous file when a new attempt fails.
- Independent clearing of diagnostics, with explicit storage errors.
- Database upgrade coverage and identical translation keys in all 3 languages.

Diagnostics retain no message contents, URL values, filenames, or unrecognized field names.
Unknown field names become the category `other`.
The recorded timestamp identifies the latest stored attempt, not necessarily the current navigation.
An unsuccessful diagnostic write reports `STORAGE_FAILED` rather than claiming that the diagnostic record is current.
The error redirect contains only an error code.

All 41 prototype tests, ESLint, Prettier, TypeScript, and the production build pass locally and in GitHub Actions.
The diagnostic publication and targeted deployment are complete.
Android acceptance remains failed; the later replacement decision removes the requirement to repeat these checks.

### Diagnostic deployment: 2026-09-29

The successful publication run is
[`36531363171`](https://github.com/mordanov/solfeo-exercises/actions/runs/36531363171).
The source commit is `d171be57752d47b414279b323d04314fcbbde131`.
The VPS pins `ghcr.io/mordanov/solfeo-pwa-prototype@sha256:da3d90317c2b7910910dd017158dddd9f52c15725382f2bd0a8e1961e6d185d0` in `.env`.
Only the prototype container changes.
All 42 other containers, including nginx, retain their IDs and start times.

All 12 deployed static files match the validated local build.
All 17 public HTTP checks pass, and the manifest includes the new text, title, and URL mappings.
Desktop Chrome exercises text-only and unexpected file-field submissions through real multipart navigation.
Diagnostics exclude synthetic private text, URL values, filenames, and unknown field names.
Failed attempts preserve the prior file.
Both clear actions persist after reload.
The proxy receives no browser share POSTs.

Evidence remains in ignored `prototypes/pwa/output/`:
- `diagnostics-local-browser.json`
- `diagnostics-https-browser.json`
- `diagnostics-https-static.json`

The isolated test browser and local container stop after verification.
The historical diagnostic procedure requires reinstalling the Android PWA before repeating messenger tests.
Those retests are no longer required for the selected Telegram path.
These diagnostic results do not establish the cause of the original Android failure.

Warning: the old prototype image expects database version 1.
An image rollback does not downgrade browser storage.
Preserve any needed test audio before clearing site data during an old-image rollback.

Do not fetch shared links or attempt to extract audio from message text.
Do not upload diagnostic metadata or file contents.
Do not broaden accepted file types without evidence.
A successful file-manager control test does not establish messenger compatibility.

### Android acceptance checklist

The owner reports another failure after the diagnostic release.
The attempt timestamp is current, the outcome is `EMPTY_SHARE`, and the form contains 0 fields.
This confirms an empty form at the receiver, not the original contents of the Android sharing request.
The failure does not establish that either messenger supplies only text.

1. Record the Android device and application versions.
2. Remove the previous PWA installation after the diagnostic deployment.
3. Open the HTTPS prototype in Chrome.
4. Confirm that the page shows `diagnostics v1`.
5. Confirm that the page reports a ready service worker.
6. Reinstall the PWA to refresh its share target.
7. Share an audio file from WhatsApp to the installed PWA.
8. Confirm that the receipt page shows the expected filename, type, and size.
9. Reload the receipt page.
10. Confirm that the stored file remains available.
11. Clear the stored file.
12. Confirm that the page shows no retained file.
13. Repeat the sharing steps from Telegram.
14. Repeat a share after closing the installed PWA.
15. Record failures and diagnostic metadata without replacing them with successful synthetic requests.
16. Clear the recorded diagnostics.

Send 1 file at a time within the configured size limit.
The prototype keeps only the latest successful share.

## Telegram alternative

The owner proposes a Telegram bot after the repeated Android failure.
The owner subsequently approves the separate prototype and deployment on the existing VPS.
The owner later confirms playback and explicitly replaces the product PWA requirement with the bot.
Implementation and activation instructions are in `docs/developer/telegram-bot.md`.

A bot can receive `audio`, `voice`, or `document` attachments in its private chat.
It can use the attachment's `file_id` with Telegram `getFile` to retrieve the file.
This route does not depend on the browser share target.
A message containing only text or a link still does not supply an audio attachment.

The proposed PHASE 0.5 prototype:
- Uses a separate directory under `prototypes/`.
- Receives updates through long polling without a new public endpoint.
- Accepts messages only from configured Telegram user IDs in private chats.
- Reads the token, allowed user IDs, size limit, and storage configuration from `.env`.
- Downloads permitted attachments and checks their size and actual file type.
- Reports success only after saving the file; reports failures explicitly.
- Keeps credentials and received media out of Git and logs.
- Tests direct attachments, forwarded attachments, voice messages, unsupported input, and unauthorized senders.
- Does not create product exercises or add a database, Redis, or product authentication.

The standard hosted Bot API currently limits `getFile` downloads to 20 MB.
See the [official Telegram FAQ](https://core.telegram.org/bots/faq#how-do-i-download-files).
This limit differs from the PWA prototype's default 25 MiB limit.

WhatsApp has no direct connection to this Telegram bot.
The owner must send the actual audio into Telegram or save it before attaching it to the bot.
Acceptance must use the owner's real sharing workflow.
A successful bot test does not count as successful PWA acceptance.

## Cleanup and phase gate

Use a prototype-specific IndexedDB database and service-worker scope.
Before product deployment, remove the prototype installation and its stored file data from test devices.
Unregister only the prototype service worker.
Remove only the prototype container and site configuration through an approved change.
Do not remove a certificate or resource that another application uses.

The owner accepts Telegram as the replacement path after real audio receipt and successful playback.
The failed Android PWA checklist no longer gates phase completion.
Remaining Telegram checks and the phase status appear in `docs/STATUS.md`.
