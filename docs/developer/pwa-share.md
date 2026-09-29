# PWA share prototype deployment

This document proposes the HTTPS deployment and acceptance checks for the PHASE 0.5 PWA share prototype.

Prerequisites:
- Read `docs/PRODUCT_BRIEF.md`, `docs/PHASES.md`, and `docs/DECISIONS.md`.
- Read `../web-projects/web-folders/documentation/onboarding.md`.
- Obtain approval before changing shared infrastructure or deploying.
- Obtain an Android device with Chrome, WhatsApp, and Telegram.

## Current state

The deployment plan is ready for owner review.
No PWA code, shared-infrastructure change, or deployment exists yet.
The owner supplies `https://solfeo.miveralta.ru` as the target hostname.
The local `web-folders/sites.yaml` contains no Solfège entry on 2026-09-29.
DNS, TLS, registry permissions, and VPS access remain unverified.

## Proposed scope

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

- [ ] Build and test the local PWA before adding infrastructure references.
- [ ] Create the required manifest, favicon, installation icons, and Apple touch icon.
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
- [ ] Confirm that unhandled POST requests return an error without retaining file bodies.

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

## Cleanup and phase gate

Use a prototype-specific IndexedDB database and service-worker scope.
Before product deployment, remove the prototype installation and its stored file data from test devices.
Unregister only the prototype service worker.
Remove only the prototype container and site configuration through an approved change.
Do not remove a certificate or resource that another application uses.

PHASE 0.5 remains incomplete until the HTTPS prototype runs, Android checks pass, and the owner confirms the remaining decisions.
