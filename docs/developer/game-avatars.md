# Game avatars

This document describes the avatar artwork, progression, protected generation, and extraction procedure.

Prerequisites:
- Read `api.md` and `env-variables.md`.
- Keep the owner's original artwork in `avatars/`.
- Use the locked Python environment for extraction.

## First entry

The account menu links to `/game` for both roles after any required password change.
The player list distinguishes loading, request failures, and genuinely empty results.
Only managers can open **Create player** and assign a profile to an active account.
The account selector uses the existing 50-account pagination.
The default avatar is Unicorn; the existing chooser changes it after creation.
Creation also adds the active season required to start a round.
Students without profiles receive guidance to contact a manager.
Logout, session expiry, and account changes cancel and remove cached game data.

## Built-in characters

The catalog contains unicorn, dragon, phoenix, griffin, sphinx cat, fox, pegasus, mermaid, lion, panda, and rhino.
The stored identifiers use `sphinx_cat` and `kitsune_fox`.
No database migration changes this catalog.

Each character has 30 transparent PNG files: 10 avatar levels and 3 emotions.
Names use `<animal>_<level>_<state>.png`, with levels `01` through `10`.
States use `neutral`, `happy`, and `sad`.
The application serves public copies from `/assets/avatars/<animal>/`.
The full character fits inside a 384 × 384 px canvas without circular clipping.
The extractor preserves the original transparency instead of removing black pixels.

Selection images reside in `avatars/selection/` and `frontend/public/assets/avatars/selection/`.
The original selection sheet contains 10 animals and the question mark.
The unicorn choice uses its first neutral appearance because the sheet contains no unicorn portrait.
The question mark opens custom creation; it does not select a random character.

## Progress and emotions

The backend derives `avatar_level` from total XP.
Thresholds are 0, 30, 80, 150, 250, 400, 600, 850, 1150, and 1500.
Player cards, setup, profiles, manager cards, and results use this authoritative value.
A completed round invalidates both player caches before the next view retrieves progress.
Changing an avatar preserves XP and the avatar level.

| Correct answers | Result emotion |
|---|---|
| 5–7 | Happy |
| 3–4 | Neutral |
| 0–2 | Sad |

The existing winning threshold remains 5 correct answers.
The existing XP bonus remains unchanged.
A custom avatar uses its generated emotion images and the same numbered XP level.
Custom generation does not create 10 separate levels of artwork.

## Source correspondence

The owner permits repeated images when source counts differ.
`avatars/crops.json` records the original files, figure indices, crop bounds, and level correspondence.
Rows follow the original irregular arrangement rather than an assumed uniform grid.
Transparent contour cuts separate neighboring figures; connected-component cleanup removes detached fragments.
Some source figures overlap, so extraction cannot recover artwork hidden behind another figure.
The extractor does not invent missing artwork.

| Source group | Mapping to levels 1–10 |
|---|---|
| Dragon, unicorn, griffin, phoenix, sphinx cat | 1, 2, 3, 4, 5, 6, 7, 8, 9, 9 |
| Lion, panda, mermaid | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 |
| Pegasus, rhino, fox | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11 |

The last mapping retains the final forms when a sheet contains 11 groups.
The mermaid follows the owner's left-to-right sequence: neutral, happy, sad, repeated across rows.
Its inconsistent source expressions do not change that correspondence.

To reproduce the 330 appearances and 12 choices:
1. Preserve exactly 1 `download*.png` source in each original character folder.
2. Run `uv run --locked python -m worker.extract_avatar_art`.
3. Inspect all levels and selection images.
4. Commit the original artwork, generated copies, and updated correspondence together.

Extraction uses the existing Pillow dependency without network requests.
Docker includes only the public copies, not the original sheets.

## Custom creation

The chooser starts generation only after an explicit button click.
It shows quota, pending status, a ready preview, acceptance, discard, and explicit errors.
Reopening the chooser retrieves recent jobs without starting another generation.
Accepting a ready job persists its identifier on the player.
Selecting a built-in character clears that identifier.

`avatars` runs the existing `worker.generate_avatar` process in development and production Compose.
It uses the shared backend image, private database, and media volume.
Only its dedicated production network permits external generation requests.
The deployment script stops, starts, and restores this worker with the application.

**Caution:** Custom creation uses an external paid image service.
Set `OPENAI_API_KEY` privately on the deployment host only when this feature is needed.
The backend rejects unconfigured generation with `AVATAR_GENERATION_UNAVAILABLE`; the worker remains idle.
Tests use synthetic jobs and mock external requests instead of generating billable images.

Generated files remain under `MEDIA_ROOT/avatars/custom/<job_id>/`.
Authenticated file endpoints check ownership, job readiness, path containment, and file existence.
They return `X-Accel-Redirect`; nginx serves the private PNG without public media URLs.
Never include these files in a public avatar directory or browser cache.

Direct game page requests use the frontend document route, including setup reloads.
The previous missing nginx routes returned status `404` even when the fallback loaded the application.
Avatar setup and result controls retain touch targets of at least 44 px.
Narrow note-count buttons and result actions stay inside the viewport.
