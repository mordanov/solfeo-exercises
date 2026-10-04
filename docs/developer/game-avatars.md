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
The SVG viewport expands vertically when C4–B5 notes or stems require additional space.
This keeps the highest bass notes and ledger lines visible without changing clef anchors.
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

Both clefs use the same 14 natural pitches from C4 through B5.
The 14 answer buttons pass the selected name and octave to the round API.
They no longer substitute the question's octave or use a fixed clef reference octave.
`notes.ts` supplies shared pitch labels, setup options, and difficulty timings.
Labels use account note naming and interface language, including scientific octave numbers 4 and 5.

Setup offers independent sound-hint and correct-answer switches.
The hint defaults to enabled; the correct answer defaults to hidden.
Choices remain between rounds within the current game-area session, not across reloads.
The difficulty explanation reports the existing 13, 10, or 7 s limit.
Difficulty does not change the pitch pool or scoring.
Enabled answer feedback shows the server's `correct_answers` to the staff's right, including incorrect answers and timeouts.

The white 56 × 56 px button below the staff appears only when the sound hint is enabled.
Hints and answer buttons use the same `playNotes` path and velocity 64.
`soundfont-player` `0.12.0` loads `/assets/piano/salamander-c4-b5.json` once per audio context.
An explicit local URL and identity key mapping prevent external soundfont downloads and preserve octave-specific velocity keys.
The application adds this requested dependency because oscillator tones cannot provide the requested recorded piano sound.
The package is archived; its locked runtime dependencies currently have no reported npm audit vulnerabilities.

The piano asset contains 56 AAC samples: 14 pitches and recorded velocity layers 4, 8, 12, and 16.
Velocity boundaries select layers at 43, 64, and 96.
These layers contain different recordings, not copies with changed amplitude.
The browser uses the already tuned samples at playback rate 1.
No full SF2, speech clips, or external runtime piano resource is required.
The JSON asset contains 1233535 bytes, within the tested 1500000-byte limit.

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
The offline C6 root supplies B5; the browser asset contains only C4–B5 natural pitches.
Each sample contains 2.5 s of mono 32 kHz AAC at 48 kbit/s, with a final 0.2 s fade.

`provenance.json` records the source, license, changes, tuning, 36 source hashes, final size, and asset hash.
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

The builder downloads only 36 required FLAC recordings, not the complete library.
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

The account menu links to `/game` for both roles after any required password change.
The player list distinguishes loading, request failures, and genuinely empty results.
Only managers can open **Create player** and assign a profile to an eligible active account.
`GET /api/game/players/accounts` excludes occupied accounts and the emergency manager before pagination.
The selector uses 50-account pages and their filtered total.
An empty candidate list shows the localized all-assigned popup, not a creation form.
Creation locks the owner account row and rejects emergency owners or a second profile.
Existing profiles and progress remain unchanged.
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
