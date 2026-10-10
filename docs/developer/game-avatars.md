# Game avatars

This document describes game artwork, clefs, note playback, avatar progression, protected generation, and extraction.

Prerequisites:
- Read `api.md` and `env-variables.md`.
- Keep the owner's original artwork in `avatars/`.
- Use the locked Python environment for extraction.

## Staff clefs

`Staff.tsx` uses filled, unaltered Bravura 1.482 glyph outlines instead of the previous hand-drawn placeholders.
`clefPaths.ts` contains only `gClef` (`U+E050`) and `fClef` (`U+E062`).
The pinned upstream revision is `steinbergmedia/bravura@37b194378b710cc40e406ab6c4b07608bb9548ae`.
The original font uses 1000 units per em and 250 units per staff space.

The 12-unit staff spacing gives a glyph scale of `0.048`.
The negative vertical scale converts the font's upward axis to SVG's downward axis.
The treble origin sits on G4 at `y=76`; the bass origin sits on F3 at `y=52`.
Bass dots surround the F3 line at `y=46` and `y=58`.
No runtime font download, system-font fallback, or image-loading delay affects the round.
Interface font settings cannot distort the outlines.

Existing staff lines, note heads, stems, ledger lines, and paper retain their native coordinates.
The SVG uses a fixed `0 0 234 140` viewport for all 1–4 note groups in either clef.
Both question ranges fit without changing clef anchors.
Shorter groups remain centered in the 4-note area.
Accessible labels describe the clef and note count in all 3 interface languages.
Tests lock the original outline fingerprints and verify both reference lines and unchanged note geometry.

The outline data retains the SIL Open Font License 1.1.
The release includes its copyright notice and full text at `/licenses/bravura-OFL.txt`.
The derived data uses the name **Game Clef Glyphs**, not the reserved font name.

To reproduce the contours without adding a project dependency:

```sh
uv run --locked --with fonttools==4.60.1 python - <<'PY'
from io import BytesIO
from urllib.request import urlopen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

url = (
    "https://raw.githubusercontent.com/steinbergmedia/bravura/"
    "37b194378b710cc40e406ab6c4b07608bb9548ae/redist/otf/Bravura.otf"
)
with urlopen(url, timeout=30) as response:
    font = TTFont(BytesIO(response.read()))
glyphs = font.getGlyphSet()
for label, codepoint in (("treble", 0xE050), ("bass", 0xE062)):
    pen = SVGPathPen(glyphs)
    glyphs[font.getBestCmap()[codepoint]].draw(pen)
    print(label, pen.getCommands())
PY
```

FontTools serves only this extraction procedure.
The application adds no font package or runtime dependency.

## Note playback

Treble questions use 13 natural pitches C4–A5; bass questions use 13 natural pitches E2–C4.
The 7 answer buttons select names C through B without octave grading.
Button audio uses the current question note's written octave, including repeated names and wrong choices.
`notes.ts` supplies shared pitch labels, setup options, and difficulty timings.
Labels use account note naming and interface language without octave suffixes.

Setup offers independent sound-hint and correct-answer switches.
The hint defaults to enabled; the correct answer defaults to hidden.
Choices remain between rounds within the current game-area session, not across reloads.
The single-line difficulty explanation reports only the selected 13, 10, or 7 s limit.
Difficulty does not change the pitch pool or scoring.
Each disabled switch adds 1 point once per completed round; enabled switches add 0 points.
The backend stores the switches and adds this bonus without changing XP, victory, or existing completed results.
The final round total is `max(0, sum(task_score) + assistance_bonus)`.
Migration `0011_game_rewards_review` floors historical negative totals; raw incorrect attempts remain -1.
Player locks serialize XP awards across concurrent round completions.
Stored JSON submission replies preserve the original response for repeated requests.
Question fields `issued_at`, `deadline_at`, `server_time`, and `time_limit_ms` govern the timer.
The frontend retains the initial server clock difference through later replies and submission retries.
The next question starts after `GAME_FEEDBACK_MS`, default `900`, rather than before the feedback finishes.
Practice hints contain a structured expected/entered pair or null.
The frontend translates both the message and note names using the account settings.
Version 1 rounds retain their previous octave grading and receive no assistance bonus.
Enabled feedback shows the server's `correct_answers` beside the centered playback control, including incorrect answers and timeouts.
The reserved feedback row prevents horizontal movement and keeps the staff at its fixed size.

The white 56 × 56 px button below the staff appears only when the sound hint is enabled.
Hints and answer buttons use the same `playNotes` path and velocity 64.
`soundfont-player` `0.12.0` loads `/assets/piano/salamander-c2-b5.json` once per audio context.
The release retains `salamander-c4-b5.json` unchanged for previously cached application code; the new application requests only the new asset.
An explicit local URL and identity key mapping prevent external soundfont downloads and preserve octave-specific velocity keys.
The application adds this requested dependency because oscillator tones cannot provide the requested recorded piano sound.
The package is archived; its locked runtime dependencies currently have no reported npm audit vulnerabilities.

The piano asset contains 112 AAC samples: 28 pitches and recorded velocity layers 4, 8, 12, and 16.
Natural C2–B5 pitches cover every possible answer button in each question octave.
Velocity boundaries select layers at 43, 64, and 96.
These layers contain different recordings, not copies with changed amplitude.
The browser uses the already tuned samples at playback rate 1.
No full SF2, speech clips, or external runtime piano resource is required.
The JSON asset contains 2464963 bytes, within the tested 2500000-byte limit.
Independent AAC decoding verifies all 112 samples within 11.45 cents of their intended frequencies.

The start gesture creates or resumes the audio context, including Safari's interrupted state.
All samples load and decode before the round request starts its timer.
Pending loading disables setup changes; failure shows an error and permits retry without creating a scored round.
Later gestures resume the context when required.
Notes start 0.75 s apart and play for 0.5 s with a 0.1 s release.
The ADSR settings are `[0.005, 0.1, 0.9, 0.1]`; gain is `0.8`.

The hint changes to **Stop listening** during playback.
Answer selection cancels the hint and plays the selected pitch.
Ordinary submission permits the final answer tone to finish.
Timeout, question transition, unmount, and `pagehide` cancel current and scheduled samples.
The player library disconnects source, envelope, and gain nodes after completion or cancellation.
Listening neither submits answers nor pauses the timer or changes scoring.

Mute, invalid pitches, missing samples, and unavailable audio produce an explicit translated error.
There is no oscillator fallback or success-shaped loading failure.
Retry clears the error; cancelled operations cannot change a newer playback's state.
Tests verify exact pitch keys, settings-based labels, preload ordering, velocity layers, cancellation, errors, and licensing.

### Piano source and export

The asset derives from Alexander Holm's Salamander Grand Piano V3 under CC BY 3.0.
The source revision is `sfzinstruments/SalamanderGrandPiano@3382bf9496bba2486f5ab0de55a264d1dfc38404`.
Export retains 4 original velocity layers and applies the upstream `Data/tune_ret.txt` corrections.
Nearest minor-third recordings supply pitches through offline resampling.
The offline C6 root supplies B5; the browser asset contains only C2–B5 natural pitches.
Each sample contains 2.5 s of mono 32 kHz AAC at 48 kbit/s, with a final 0.2 s fade.

`provenance.json` records the source, license, changes, tuning, 68 source hashes, final size, and asset hash.
`LICENSE.txt` includes attribution and the complete CC BY 3.0 license.
Setup links to this notice; `/licenses/soundfont-player-MIT.txt` retains the player license.

Prerequisites for export:
- Use the locked Python environment, ffmpeg, and the existing frontend formatter.
- Use an external temporary source directory, not the repository.

```sh
uv run --locked python worker/build_game_piano.py \
  --source-dir /tmp/solfeo-piano-sources \
  --public-dir frontend/public/assets/piano
npm exec --workspace frontend -- prettier --write public/assets/piano/provenance.json
uv run --locked pytest backend/tests/test_game_piano_asset.py -q
```

The builder downloads only 68 required FLAC recordings, not the complete library.
It caches the source recordings for retries and records their SHA-256 values.
Formatting provenance does not change the hashed piano asset.
Use a fresh source directory if the pinned revision changes.

## First entry

The upper-left circular Unicorn badge links to `/game` without bypassing authentication or a required password change.
Its localized tooltip and accessible name use `game.playHint` in Russian, English, and Spanish.
The 44 × 44 px target supports pointer and keyboard interaction.
Only the header branding moves right.
Below 900 px, smaller branding text fits beside the badge.
An inaccessible sizing copy preserves the original header dimensions and the coordinates of all other controls.
The existing account navigation remains unchanged.

The supplied source stays unchanged in `guess-the-note-prompts/Rainbow Unicorn Music Badge.png`.
The public copy is a 128 × 128 px PNG with transparent outer corners.
It resides at `/assets/game-badge.png`, outside the leveled avatar catalog.
Reproduce it with the existing Pillow dependency:

```sh
uv run --locked python - <<'PY'
from PIL import Image, ImageDraw

image = Image.open("guess-the-note-prompts/Rainbow Unicorn Music Badge.png").convert("RGBA")
image = image.crop((72, 65, 1182, 1175))
mask = Image.new("L", image.size, 0)
ImageDraw.Draw(mask).ellipse((3, 3, 1106, 1106), fill=255)
image.putalpha(mask)
image.resize((128, 128), Image.Resampling.LANCZOS).save(
    "frontend/public/assets/game-badge.png", optimize=True
)
PY
```

The account menu links to `/game` for all 3 roles after any required password change.
The player list distinguishes loading, request failures, and genuinely empty results.
Only managers can open **Create player** and assign a profile to an eligible active account.
`GET /api/game/players/accounts` excludes occupied accounts and the emergency manager before pagination.
The selector uses 50-account pages and their filtered total.
An empty candidate list shows the localized all-assigned popup, not a creation form.
Creation locks the owner account row and rejects emergency owners or a second profile.
Existing profiles and progress remain unchanged.
The default avatar is Unicorn; the existing chooser changes it after creation.
Creation also adds the active season required to start a round.
Students and players without profiles receive guidance to contact a manager.
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
The pending-review image is the new wordless `under_moderation.png`.
The packaged image resides in `/assets/avatars/selection/`; the owner's original PNG remains untouched outside the frontend.
Rejected selections show `custom.png`, the question-mark choice.

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
New custom generation creates 10 levels with 3 emotions each.
Older custom avatars retain their 3 shared emotion images without paid regeneration.

## Lifetime prizes

The game awards 20 prizes from completed rounds across all seasons.
Each profile receives each code once, with no extra XP.
The existing trophies for 20, 100, 200, and 500 completed rounds remain separate.
Statistics resets retain all prize records.
`docs/PRODUCT_BRIEF.md` lists all codes and conditions.
`GAME_TIMEZONE`, default `UTC`, defines calendar days for prizes and generation quotas.

Individual-note prizes compare corresponding positions in the existing expected and entered arrays.
Correct positions count even when another position makes the whole answer incorrect.
Version 2 compares names; version 1 also compares octaves.
Timeouts and unfinished rounds do not contribute.
Consecutive-answer prizes count whole correct answers across completed rounds.
Treble and bass prizes also count whole correct answers, not individual notes.
The interface uses `game.prizes.codes.<code>` for localized names and `game.prizes.descriptions.<code>` for conditions.
The copy welcomes breaks without guilt, lost-prize warnings, or daily penalties.

### Prize images

The owner's original `trophies.png` contains the 20 prizes in a 5-column, 4-row layout.
`scripts/build_prize_assets.py` maps each position to its stable prize code.
The extractor follows connected visible pixels instead of assuming perfectly centered grid cells.
It removes detached background specks without cutting another badge into the result.
Each public PNG uses a transparent 256 × 256 px canvas with at least 8 px of padding.
The original image remains unchanged.
Reproduction tests compare decoded RGBA pixels, dimensions, and PNG format instead of compressed file bytes.
Different platform encoders can produce different PNG bytes for identical pixels.
The source checksum still verifies byte-for-byte preservation.

To reproduce the packaged images:

```sh
uv run --locked python scripts/build_prize_assets.py
uv run --locked pytest backend/tests/test_prize_art.py
```

The script requires exactly 20 separate badges before it writes any files.
It uses the existing Pillow dependency.
Images live at `/assets/prizes/<code>.png`.
`PrizeImage` supplies the shared renderer for the result shelf, profile shelf, and new-prize announcements.
Round preparation does not render the shelf or request its achievement catalog.
The result shows the full collection below replay controls, even without new awards.
Earned prizes use full color; locked prizes use grayscale and reduced opacity.
Names, accessible image labels, and conditions retain the selected interface language.
No image contains translated text, and no runtime image generation occurs.

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
It shows availability, quota, phase, saved-image count, approximate remaining time, previews, acceptance, discard, and explicit errors.
Reopening the chooser retrieves recent jobs without starting another generation.
Selecting an approved ready job persists its identifier on the player.
Selecting a built-in character clears that identifier.
The saved gallery includes approved ready jobs from every player profile.
It also includes the requested profile's own ready jobs, including pending review results.
Pending and rejected jobs from other profiles remain private.
Any player can preview and select an approved avatar without another provider request.
The chooser hides the discard action for avatars owned by another account.
The preview supports levels 1–10 and all 3 emotions.
Discard removes the database record and the creator's selection.
The system rejects discard while another profile selects that avatar.
Discard does not remove files or perform another generation.

`avatars` runs the existing `worker.generate_avatar` process in development and production Compose.
It uses the shared backend image, private database, and media volume.
Only its dedicated production network permits external generation requests.
The deployment script stops, starts, and restores this worker with the application.

**Caution:** Custom creation uses an external paid image service.
Set `OPENAI_API_KEY` privately on the deployment host only when this feature is needed.
The backend rejects unconfigured creation with status `503` and `AVATAR_GENERATION_UNAVAILABLE`.
The quota endpoint reports this condition before the interface permits a request.
The worker leaves new jobs queued without a key but can complete extraction from a saved sheet.
Tests use synthetic jobs and mock external requests instead of generating billable images.

Generated files remain under `MEDIA_ROOT/avatars/custom/<job_id>/`.
The shared `media_data` volume preserves them across container restarts and releases.
Each new job saves `sheet.png`, 30 transparent PNG frames, and `manifest.json` with source and frame hashes.
Frames use `levels/avatar_<level>_<state>.png` with levels `01` through `10`.
Atomic replacement and explicit synchronization publish files before the worker marks the job ready.
Both selection endpoints reject incomplete version 2 sets.
Authenticated file endpoints check ownership or approval, generation readiness, path containment, and file existence.
Managers can inspect ready unapproved files; students and players cannot.
They return `X-Accel-Redirect`; nginx serves the private PNG without public media URLs.
Any authenticated member can retrieve frames only for ready approved avatars.
Pending and rejected images remain private to the creator and managers.
Never include these files in a public avatar directory or browser cache.

### One-sheet generation

The default model is `gpt-image-1-mini` with low quality.
One image request creates a transparent `1024x1536` sheet, not 30 separate images.
An automatic moderation request checks the description first.
Automatic image moderation checks the generated sheet before local extraction and manager review.
The prompt requires 5 columns, 6 rows, consistent identity, and empty gutters.
It requests 4 vertical and 5 horizontal cyan divider lines between the cells.
The worker detects these bands and excludes them from each frame crop.
New sheets fail validation when either set of separators is missing or malformed.
A `sheet-layout.txt` marker keeps strict segmentation active after a worker restart.
Saved sheets without this marker retain equal-cell fallback for recovery.
The prompt keeps equal cell dimensions, camera distance, and full-body framing.
Body proportions grow through 10 distinct stages, from a baby near 2 heads tall to a titan near 6–7 heads tall.
Each stage adds age-specific clothing, features, and accessories while preserving the same individual and species.
Rows 1, 2, and 3 contain neutral, happy, and sad levels 1–5.
Rows 4, 5, and 6 contain the same emotions for levels 6–10.
Each level repeats its body proportions and outfit across its 3 emotion variants.
Neutral is calm and friendly, or serious and focused for strong forms.
Happy adds a joyful smile, sparkling eyes, and small sparkles; strong forms use a confident grin.
Sad adds gentle disappointment, drooping eyes, and at most 1 small tear.
The prompt changes only the face and slight posture between a level's mood variants.
The worker rejects cells with visible pixels under 2% of their area.
It accepts figures that touch cell edges and crops them to visible bounds.
Pixels with alpha below 32 are ignored as antialiasing residue.
An invalid sheet is regenerated once automatically; this second request happens in the same job and does not consume extra quota.
If the second sheet is also invalid, the job fails with `AVATAR_SHEET_INVALID` and keeps `sheet.png`.
The failure log carries `error_code` and the failing `cell` (`level=N state=...`).

## Face icon (portrait)

After the 30 frames are saved, the worker makes one more, separate image request for a close-up face of the same described creature.
The result goes through the same image moderation as the sheet, is cropped to a circle, resized to 256×256 and stored as `avatars/custom/{id}/portrait.png`.
`GET /api/game/avatars/{id}/files/portrait` serves it with the same approval rule as the frames.
Portrait generation is best effort.
Provider errors, moderation flags, and invalid images log `AVATAR_PORTRAIT_FAILED` or `AVATAR_PORTRAIT_FLAGGED`.
The job still becomes `ready` with all 30 frames.
A restart reuses a saved `portrait.png` without another paid request.
The saved-avatar gallery in the chooser shows the circle and falls back to the neutral level-1 frame when it is missing.
This second request is paid but does not consume extra daily quota, and a separate request cannot guarantee an identical face to the sheet.
It fits each complete figure inside a transparent 384 × 384 px canvas.
Geometry checks cannot prove correct character identity, expression, or artistic progression.
Inspect all 30 images before approving visual quality.

### Manager approval

Successful generation remains separate from permission to show the result to a student or player.
The worker leaves ready results with review status `pending`.
The player sees a wordless hourglass instead of an unapproved generated image.
The backend omits unapproved image paths from status responses.
Direct student and player frame requests also fail until approval.

1. Open **Player management** as a manager.
2. Open the avatar approval queue.
   The queue shows ready pending results in pages of 12, oldest first.
3. Inspect the description and all 30 level/emotion frames.
4. Approve an acceptable result or reject an unsuitable result.
   Approval activates the waiting player selection; rejection returns it to the question-mark artwork.

Approval activates only when `players.avatar_review_job_id` still identifies that job.
The decision does not replace a later explicit built-in choice.
`GET /api/game/avatars/review?offset=0` returns the queue and its total.
`POST /api/game/avatars/{id}/review` accepts `decision` with `approved` or `rejected`.
The manager-only `review-sheet` route serves the generated original through protected storage.
Review records include the manager and decision time.
Repeating the same decision is safe; changing an existing decision returns a conflict.
Review uses no image-generation request and consumes no extra quota.
All controls, statuses, accessible labels, and errors follow the selected language.
Migration `0011_game_rewards_review` marks existing ready avatars approved without another provider request.
This includes legacy avatars, preserving earlier approved-looking selections and progress.

During provider generation, the saved-image count stays at 0.
The interface explains that all variants arrive together.
Local extraction advances the count only after each file reaches storage.
The estimate uses up to 5 recent, uninterrupted successful jobs or the configured initial duration.
An overdue estimate becomes unknown instead of reporting false completion.
The player can close the window and return to the same job.

Account and player locks serialize quota checks and creation.
Identical pending requests reuse one job and one quota record.
Different descriptions for a busy player return `AVATAR_JOB_BUSY`.
The worker claims jobs with `FOR UPDATE SKIP LOCKED` and a durable lease token.
An active claim prevents another worker from repeating the request.
An expired claim reuses a saved sheet without another image request.
An interrupted generation without a saved sheet fails explicitly; no automatic paid retry occurs.
Lease checks prevent a late provider reply from replacing another worker's saved sheet.
Moderation refunds only the linked quota record.
Manager rejection does not repeat a paid request.

Migration `0009_avatar_sheets` preserves older ready avatars as version 1.
It closes legacy pending jobs as interrupted because their original worker records no durable request phase.
This prevents an untracked paid retry during deployment.
The migration does not regenerate existing avatars.

Direct game page requests use the frontend document route, including setup reloads.
The previous missing nginx routes returned status `404` even when the fallback loaded the application.
Avatar setup and result controls retain touch targets of at least 44 px.
Narrow note-count buttons and result actions stay inside the viewport.
