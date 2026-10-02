# Decisions

This document records project decisions and their reasons.

Prerequisites:
- Read `docs/PRODUCT_BRIEF.md` and `docs/PHASES.md`.

Format: date, decision, reason. Do not reverse a decision without asking the owner.

- 2026-10-02: The owner requests mobile installation, browser language defaults, focused management changes, and automatic speech tempo.
  Original icons and localized manifests support online installation without a service worker or protected-file caching.
  Safari installation uses manual Share guidance; Chrome uses its native prompt when available.
  This decision restores optional installation, not the rejected Android share target.
  Browser preferences select the anonymous interface language; saved account settings retain priority after login.
  Recognition review shows only the score; exercise previews and student fallbacks retain the original image.
  Conservative AAC timings choose a safe tempo before playback; decoded timings confirm the choice before scheduling.
  Browser storage remembers tempo per account, exercise, score version, language, and naming choice.
  The slider can extend below its preferred minimum without exceeding the speech-rate or complete-duration limits.
  The existing 66 clips remain unchanged; no paid generation occurs.
- 2026-10-02: The owner requests focused mobile responsiveness without an architectural rewrite.
  Labeled cards below 600 px reuse all user and journal fields, actions, and pagination; larger screens retain Community DataGrid.
  Theme overrides reduce repeated mobile padding and improve navigation and touch targets.
  Score width changes trigger rendering and cursor restoration without restarting audio or speech.
  OSMD uses 75 % zoom on phones so notes remain distinct rather than squeezing a desktop score.
  Browser fixtures do not replace Safari, real-device, or real-media acceptance.
- 2026-10-01: The owner reduces the default password minimum to 8 characters.
  Creation, reset, change, and emergency credentials use the same configured minimum.
  The maximum password length remains 256 characters; hashing, rate limits, and session protections remain unchanged.
  Existing environment overrides retain precedence.
- 2026-10-01: The owner authorizes all remaining Material Design steps without intermediate confirmations.
  Each screen uses a separate commit after its build, linter, and targeted tests pass.
  Presentation adapters preserve native attributes and event signatures without changing business state or API calls.
  Community DataGrid retains external pagination and disables additional table operations and dynamic evaluation.
  Native dates remain because a Date Pickers adapter requires an unapproved dependency.
  Native audio and the tempo slider retain their original handlers.
  The local theme choice does not add a server setting or regenerate speech clips.
  Final Chrome checks use synthetic data; Safari automation remains blocked by its disabled browser setting.
- 2026-10-01: The owner starts the separate Material Design feature after accepted PHASE 7.
  Step 2 adds Material UI v9, Emotion, self-hosted Roboto, and Community DataGrid v9.
  The existing React 19 version satisfies the libraries' peer requirements.
  Charts remains absent because the application has no charts.
  Date Pickers remains absent because its required date library exceeds the approved dependencies.
  Keep native date controls unless the owner approves an exception.
  Installation does not change application code; the owner subsequently authorizes the remaining steps together.
- 2026-10-01: The owner confirms final PHASE 7 acceptance after the verified production deployment.
  This confirmation closes the full smoke acceptance gate and completes PHASE 7.
  PHASE 5 and PHASE 6 already have owner acceptance.
  The record does not invent automated browser results, device versions, or new host measurements.
  Material Design remains a separate planned feature; this closure does not modify frontend code.
- 2026-10-01: The owner confirms completion of PHASE 5 and PHASE 6 after successful production deployment.
  Pull request #2 merges as `165a1397`; publication and deployment run `36921037861` succeeds.
  Public HTTPS health returns `{"status":"ok"}`.
  This acceptance closes the deferred OMR and spoken-notes gates without regenerating the existing 66 clips.
  At that confirmation, PHASE 7 still requires separate smoke acceptance.
- 2026-10-01: The owner explicitly removes the host-memory preflight from rollout.
  Rollout no longer reads `/proc/meminfo` or rejects deployment through `OMR_MEMORY_INSUFFICIENT` or `OMR_MEMORY_UNKNOWN`.
  The obsolete host-reserve setting is removed from the example configuration and production Compose.
  Docker memory limits, disk checks, worker healthchecks, and compatible rollback remain unchanged.
  Memory pressure remains an operational risk; healthy startup does not establish successful recognition.
- 2026-10-01: The owner merges pull request #1 and retains the existing 66 speech clips without regeneration.
  The owner authorizes complete PHASE 7 automation without intermediate confirmations.
  Manual acceptance follows the complete implementation.
  Main-branch deployment still stops at the OMR memory guard; merge does not establish production activation.
- 2026-10-01: Deployment reserves storage before image pulls and checks the reserve again before service changes.
  The default image budget is 6144 MiB; the free reserve is 2048 MiB on both measured filesystems.
  The rollout requires a local Docker daemon and never performs automatic image or volume cleanup.
  Existing compatible rollback images remain available.
- 2026-10-01: Unknown application pages use translated React content while retaining HTTP 404.
  API errors and direct internal-file denial do not use that fallback.
  CSP permits inline styles for score rendering, but not inline scripts or external resource loading.
  HSTS applies only to trusted HTTPS responses and the current hostname.
- 2026-10-01: Backend and worker diagnostics use fixed JSON fields without request bodies or credential-bearing values.
  Exception diagnostics retain types and frame locations, not values.
  CI audits all locked Python and JavaScript dependencies and checks documentation completeness.
  The Python auditor is a development dependency, not a runtime dependency.

- 2026-09-30: The owner accepts PHASE 4 and authorizes complete PHASE 5 automation.
  The owner reports unlinking Telegram and clearing VPS disk space.
  PHASE 5 does not restore the Telegram association.
- 2026-09-30: OMR jobs refer to an immutable image version and require explicit manager approval.
  Replacing an image or rerunning recognition withdraws the previous score from students.
  Existing images support manual recognition; deployment does not enqueue the existing catalog automatically.
  The original image remains available when recognition fails or the score is not approved.
- 2026-09-30: Backend and OMR share an immutable image, but run in separate containers.
  This retains the verified 2-image release bundle and avoids an independent engine release lifecycle.
  OMR uses a private database network and explicit CPU, memory, process, and temporary-storage limits.
  A deployment guard requires available RAM before image pulls or service changes.

- 2026-09-29: The owner confirms PHASE 3 and authorizes all PHASE 4 work without intermediate confirmations.
  The requested application 404 page belongs to PHASE 7.
- 2026-09-29: Managers link Telegram through a short-lived, single-use code created in their authenticated web account.
  PostgreSQL stores only the code hash; numeric sender IDs, not Telegram usernames, identify linked accounts.
  Received audio enters the owning manager's import list.
  The manager chooses creation or audio replacement, title, and description on the website.
  Repeated updates and repeated application requests do not create duplicate imports or exercises.
  The product worker replaces the existing bot poller; prototype files remain untouched.

- 2026-09-29: The owner confirms all PHASE 2 checks and authorizes the entire PHASE 3 without intermediate confirmations.
  Manual acceptance follows the complete implementation and automated deployment.
- 2026-09-29: A listening session starts on playback, survives pauses, and ends on navigation, exit, or natural completion.
  Replay after completion uses a new UUID.
  The event endpoint accepts the session-bound CSRF token in its JSON body because `sendBeacon` cannot set custom headers.
  The authenticated cookie and exact allowed origin remain mandatory.
  Other mutation endpoints keep their header-based CSRF checks.
  Repeated and out-of-order events preserve one row, maximum position, terminal time, and completion.
- 2026-09-29: Sequential selection persists per student and wraps at either end.
  Completion advances the saved pointer once; the displayed exercise does not change automatically.
  Random selection does not change the sequential pointer and excludes the current exercise when alternatives exist.
  Random Previous uses the current page's selection history; reload starts in sequential mode.
  Image-only exercises remain visible and create no listening session.
  Journal rows preserve the exercise title, audio reference, and duration from their first accepted event.

- 2026-09-29: The owner confirms all PHASE 1 manual checks and authorizes the complete PHASE 2 implementation.
  PHASE 2 needs no intermediate confirmations; manual acceptance follows implementation and deployment.
- 2026-09-29: PHASE 2 saves exercise forms and their files as one operation.
  Category is optional free text; metadata-only edits preserve current files.
  PostgreSQL serializes create, delete, and reorder operations with an advisory transaction lock.
  Reordering requires the exact active exercise set and rejects stale lists.
  Original images and replaced files remain in private storage; soft deletion preserves exercise records and files.
  Only authenticated members can read current files from active exercises.
  Product listening, journaling, OMR, and Telegram integration remain in their planned later phases.

- <date>: Job queue is in Postgres (SKIP LOCKED), no Redis. Reason: fewer services.
- <date>: Audio is stored as AAC in .m4a. Reason: Chrome and Safari both play it.
- <date>: Passwords use bcrypt or scrypt. Reason: the owner wants simple auth, plaintext is not allowed.
- <date>: The original image is always kept. Reason: needed for OMR review and as a fallback.
- 2026-09-29: The PHASE 0 database foundation uses synchronous SQLAlchemy 2.0 and psycopg 3.
  Reason: synchronous sessions simplify transactions and suit the expected workload.
  Database-dependent HTTP handlers use FastAPI's synchronous execution path.
  Future workers own separate engines and sessions; they do not share the backend pool.
  Do not run synchronous database calls directly inside an asynchronous handler.
- 2026-09-29: PHASE 1 uses session-bound CSRF tokens and an explicit origin allowlist.
  Login requires an allowed `Origin`; other mutations also require `X-CSRF-Token`.
  `/api/auth/me` returns the CSRF token after cookie authentication.
  Reason: JSON requests and same-origin token delivery protect state changes without exposing the httpOnly session cookie.
- 2026-09-28: PHASE 0.5 evaluates `ejercicio_1.jpeg` through `ejercicio_10.jpeg`; image 11 remains for a later check. Reason: use 10 samples without selecting by results.
- 2026-09-28: Original samples and generated MusicXML remain local and uncommitted. Reason: the owner approves local-only sample handling.
- 2026-09-28: Recognition uses `100 × max(0, 1 − errors / expected events)`. Reason: the owner approves event comparison against original images.
  Each substitution, omission, or extra event counts as 1 error.
  A note must match pitch, accidental, octave, and duration; a rest must match duration.
  Structural errors appear separately in the report.
- 2026-09-28: Fully recognized means at least 80 %; partly recognized means at least 50 % and below 80 %. Failed means below 50 % or no usable MusicXML.
  Reason: these boundaries remove overlap between the owner's recognition bands.
- 2026-09-28: The owner reviews the engine recommendation without an aggregate acceptance threshold. Reason: per-image results and structural errors inform the decision.
- 2026-09-28: The owner confirms the recommendation to continue with Audiveris.
  Reason: 8 of 10 images meet the agreed recognition threshold; 2 fail.
  Manager review and the original-image fallback remain mandatory.
  This decision does not authorize automatic score approval or confirm completion of the detailed manual checks.
- 2026-09-28: The owner confirms completion of the OMR manual checks.
  The decision to continue with Audiveris remains unchanged.
- 2026-09-29: The owner confirms completion of the protected-audio manual step.
  X-Accel-Redirect and nginx byte-range delivery remain the planned file-serving mechanism.
  Device versions and the manual test setup are not recorded.
- 2026-09-29: The owner approves the static PWA prototype and HTTPS onboarding plan.
  The prototype uses `/prototype-share/` on `solfeo.miveralta.ru` and stores shared files on the device.
  Reason: test Android sharing without building product authentication, uploads, or database services.
  Registry ownership and publishing permissions still require confirmation.
- 2026-09-29: The owner confirms `ghcr.io/mordanov/solfeo-pwa-prototype` and authorizes publication, shared infrastructure changes, and VPS deployment.
  Only the prototype and necessary nginx configuration belong to this deployment.
  Reason: enable Android acceptance checks without restarting unrelated applications.
- 2026-09-29: The owner approves a separate Telegram bot prototype and deployment on the existing VPS.
  Reason: evaluate direct attachment ingestion after Android PWA sharing delivers an empty form.
  The prototype stays in PHASE 0.5 and does not create exercises.
  The failed PWA acceptance result remains unchanged.
- 2026-09-29: The owner confirms successful real audio receipt through the Telegram prototype.
  The reported reply identifies `199163078.m4a`, with a size of 636644 bytes.
  This confirms the basic bot ingestion path, not the full manual checklist or replacement of the product PWA requirement.
- 2026-09-29: The owner confirms successful playback of the audio received through the Telegram prototype.
  The earlier receipt identifies `199163078.m4a`, with a size of 636644 bytes.
- 2026-09-29: The owner replaces product PWA audio sharing with the Telegram bot.
  Reason: real Telegram receipt and playback succeed, while Android PWA sharing delivers an empty form.
  PHASE 4 now implements manager-only Telegram audio import instead of an Android share target.
  The web application and its role boundaries remain unchanged.
  The old PWA result remains failed; no further PWA acceptance is required for the selected ingestion path.
  This decision does not claim completion of unreported bot checklist cases or authorize deletion of deployed prototypes.
- 2026-09-29: The owner confirms the remaining manual checks and requests continuation.
  PHASE 0.5 closes with Audiveris, protected AAC delivery, and Telegram ingestion as the selected paths.
  The previous handoff requests voice, forwarded-audio, document, and unauthorized-sender checks.
  The confirmation covers those checks; device versions and per-message evidence remain unrecorded.
  PHASE 0 starts with the local health-page skeleton.
  Product Telegram integration remains in PHASE 4; deployed prototypes remain unchanged.
- 2026-09-29: The owner confirms the requested local health-page and PostgreSQL restart scenarios.
  The local schema revision remains `0001_initial` after restart.
  Browser versions and a detailed browser matrix are not supplied.
  This confirmation does not close the later VPS acceptance gate.
- 2026-09-29: Production uses separate application and migration roles within a dedicated PostgreSQL instance.
  Reason: runtime data access must not grant schema ownership or permission to alter migration metadata.
  Alembic metadata uses a private production schema; the development schema remains unchanged.
  Production Compose uses supplied images, a private database network, and a loopback frontend port.
  Registry publication, TLS integration, and actual VPS deployment remain separate tasks.
- 2026-09-29: Product CD uses a separate proxy network, dedicated runtime directory, and immutable release bundles.
  Reason: preserve unrelated VPS services and keep the backend and database off shared application networks.
  Shared nginx and the product frontend join `solfeo-proxy`; existing TLS and prototype routes remain.
  Rollback restores previous images only when their Alembic heads match the current database.
  An incompatible schema requires operator recovery; automated downgrade and volume deletion are prohibited.
- 2026-09-29: The owner confirms the final deployed health-page checklist and closes PHASE 0.
  The confirmation covers Chrome and Safari, RU/EN/ES, status refresh, and failure/recovery.
  Owner-tested browser versions and a per-browser evidence matrix are not supplied.
  PHASE 1 remains unstarted and requires a separate approved plan.
- 2026-09-29: The owner authorizes the complete PHASE 1 implementation without intermediate confirmations.
  Manual acceptance follows the complete implementation and automated checks.
- 2026-09-29: Passwords use standard-library scrypt with `N=32768`, `r=8`, `p=3`, and independent 16-byte salts.
  Login cookies contain random 256-bit tokens; PostgreSQL stores only their SHA-256 hashes.
  Sessions use a 90-day sliding lifetime by default, with httpOnly, Secure, and SameSite=Lax cookies in production.
  Password changes, manager resets, deactivation, and role changes revoke affected sessions.
- 2026-09-29: PostgreSQL stores separate login budgets for normalized usernames and client IP addresses.
  Transaction-level advisory locks serialize concurrent attempts; nginx adds a burst limit before password hashing.
  Shared nginx overwrites client identity headers; the private frontend forwards that trusted identity to the private backend.
  Do not expose the backend or attach untrusted services to these networks.
- 2026-09-29: Emergency synchronization completes before backend startup succeeds.
  Incomplete credentials fail configuration validation; absent credentials deactivate the flagged account and revoke its sessions.
  Changing the emergency username retires the previous account without deleting it.
  The manager interface cannot modify emergency accounts or change the current manager's own role or active status.
- 2026-09-30: The owner authorizes complete PHASE 6 automation while explicitly postponing PHASE 5 deployment.
  Work stays on `feat/phase6-spoken-notes`; no merge, publication, or VPS change belongs to this request.
  PHASE 5 production acceptance remains open.
  Speech uses approved scores and public pre-generated vocabulary, as required by the brief.
  Speech does not report progress against a different uploaded recording.
  Missing OpenAI credentials block actual clip generation; synthetic test signals do not replace production speech.
- 2026-10-01: The owner supplies the private OpenAI key and opens pull request #1.
  Actual vocabulary generation and branch CI can proceed without merging or deploying.
  Audible owner acceptance remains separate from automated media checks.
