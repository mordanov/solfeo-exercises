# PWA share prototype deployment

This document describes the local PWA prototype, its approved deployment plan, and the remaining Android acceptance checks.

Prerequisites:
- Read `docs/PRODUCT_BRIEF.md`, `docs/PHASES.md`, and `docs/DECISIONS.md`.
- Read `../web-projects/web-folders/documentation/onboarding.md`.
- Obtain approval before changing shared infrastructure or deploying.
- Obtain an Android device with Chrome, WhatsApp, and Telegram.

## Current state

The owner approves the deployment plan on 2026-09-29.
The local prototype is implemented and verified.
No shared-infrastructure change, image publication, or HTTPS deployment exists yet.
The owner supplies `https://solfeo.miveralta.ru` as the target hostname.
The local `web-folders/sites.yaml` contains no Solfège entry on 2026-09-29.
DNS, TLS, registry permissions, and VPS access remain unverified.

## Prototype scope

Use a static React, TypeScript, and Vite prototype under `prototypes/pwa/`.
Use react-i18next with Russian, English, and Spanish strings.
The receipt page shows the shared filename, type, size, and a clear-storage action.
It does not create exercises or upload audio.

The service worker handles the manifest's multipart POST share target.
It stores the file in IndexedDB before redirecting to the receipt page.
The manifest accepts `audio/*`, `.opus`, `.ogg`, and `application/octet-stream`.
The page must distinguish a completed receipt from empty input or a storage failure.

Keep file data and metadata on the device.
Do not add analytics, a backend, a database, Redis, product login, or exercise management.
Do not copy local exercise samples into the public image.
Product authentication and the login-return flow remain PHASE 4 work.

### Proposed routes

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
The HTTPS deployment and owner device checks remain open.

## Proposed onboarding facts

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
| Registry image | `ghcr.io/<approved-owner>/solfeo-pwa-prototype:<commit>` |
| Site priority | `190`, subject to a fresh conflict check |
| Public landing-page link | Disabled for the prototype |

The inspected site priorities currently end at `180`.
Confirm the registry owner and push permissions before creating a publishing workflow.
Define all deployment variables in `.env.example`.
Never copy the files prototype's Basic credentials into this deployment.

## Deployment checklist

Follow the supplied onboarding guide after scope approval.
Treat database, Redis, and backend-only steps as explicitly inapplicable to this static prototype.

- [x] Build and test the local PWA before adding infrastructure references.
- [x] Create the required manifest, favicon, installation icons, and Apple touch icon.
- [ ] Add the site entry to `web-folders/sites.yaml`.
- [ ] Add the HTTP, HTTP-redirect, and HTTPS nginx templates.
- [ ] Add the static container service and nginx dependency to the shared Compose file.
- [ ] Add the domain variables to nginx and the shared `.env.example`.
- [ ] Document the disabled landing-page link.
- [ ] Prepare the prototype-only image publishing workflow and its onboarding template.
- [ ] Add CI placeholders for any genuinely required deployment variables.
- [ ] Verify DNS and the existing certificate state.
- [ ] Configure actual VPS variables through the approved deployment process.
- [ ] Publish the image under an immutable commit tag.
- [ ] Deploy only the prototype service and necessary nginx configuration.
- [ ] Issue or reuse the hostname certificate through the shared certbot setup.
- [ ] Verify the HTTPS health response, manifest, icons, and service-worker headers.
- [x] Confirm locally that unhandled POST requests return an error without retaining file bodies.

The publishing workflow supports only this prototype.
It does not replace the PHASE 0 product CI/CD work.
Do not restart unrelated applications.
Do not change the shared PostgreSQL configuration.
The static prototype must not retain uploaded request bodies or log their contents.

## Validation plan

Write failing tests before implementing share handling.
Cover valid files, empty shares, rejected input, IndexedDB errors, and redirect-after-storage ordering.
Cover receipt-page errors, storage clearing, and identical nonempty locale keys.
Run Vitest, Testing Library, TypeScript, ESLint, Prettier, and the production build.
Check manifest paths and service-worker scope against the deployed prefix.

Automated tests do not prove Android installation or messenger interoperability.
The following owner checks remain mandatory.

### Android acceptance checklist

1. Record the Android device and application versions.
2. Open the HTTPS prototype in Chrome.
3. Confirm that the page reports a ready service worker.
4. Install the PWA through Chrome.
5. Share an audio file from WhatsApp to the installed PWA.
6. Confirm that the receipt page shows the expected filename, type, and size.
7. Reload the receipt page.
8. Confirm that the stored file remains available.
9. Clear the stored file.
10. Confirm that the page shows no retained file.
11. Repeat the sharing steps from Telegram.
12. Repeat a share after closing the installed PWA.
13. Record failures without replacing them with successful synthetic requests.

Send 1 file at a time within the configured size limit.
The prototype keeps only the latest successful share.

## Cleanup and phase gate

Use a prototype-specific IndexedDB database and service-worker scope.
Before product deployment, remove the prototype installation and its stored file data from test devices.
Unregister only the prototype service worker.
Remove only the prototype container and site configuration through an approved change.
Do not remove a certificate or resource that another application uses.

PHASE 0.5 remains incomplete until the HTTPS prototype runs, Android checks pass, and the owner confirms the remaining decisions.
