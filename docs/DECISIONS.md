# Decisions

This document records owner-approved project decisions and their reasons.

Prerequisites:
- Read `docs/PRODUCT_BRIEF.md` and `docs/PHASES.md`.

Format: date, decision, reason. Do not reverse a decision without asking the owner.

- <date>: Job queue is in Postgres (SKIP LOCKED), no Redis. Reason: fewer services.
- <date>: Audio is stored as AAC in .m4a. Reason: Chrome and Safari both play it.
- <date>: Passwords use bcrypt or scrypt. Reason: the owner wants simple auth, plaintext is not allowed.
- <date>: The original image is always kept. Reason: needed for OMR review and as a fallback.
- <date>: Sync or async SQLAlchemy: <decide in PHASE 0>.
- <date>: CSRF method: <decide in PHASE 1>.
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
