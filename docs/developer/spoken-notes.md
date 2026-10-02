# Spoken notes

This document explains speech generation, playback timing, and the remaining acceptance checks.

Prerequisites:
- Read `setup.md` and `omr-pipeline.md`.
- Install the existing Python and frontend dependencies.
- Make `ffmpeg` and `ffprobe` available.
- Keep a valid private root `.env` file.

## Current delivery

PHASE 6 includes 66 generated AAC clips, their receipts, and a verified manifest.
The owner supplies the private API key and opens pull request #1 on 2026-10-01.
Commit `39545ef` adds the complete vocabulary in English, Russian, and Spanish.
Both the source assets and the frontend build pass manifest verification.
Chrome decodes all 66 real clips and verifies scheduled speech and rests for all 6 language and naming combinations.
Natural quarter notes fit the default 72 BPM tempo in every combination.
The owner confirms audible Chrome acceptance on 2026-10-01.
The owner confirms complete PHASE 6 acceptance after production deployment on 2026-10-01.
This confirmation does not add automated Safari results or browser-specific measurements.
The owner merges pull request #1 later that day.
That recorded deployment stops at the former OMR memory guard; image publication does not establish production acceptance.
The owner removes the host-memory rollout check later that day; container memory limits remain active.

The generator now adds a native-accent hint per language to the speech instructions.
The fingerprint does not track that wording, so the 66 committed clips stay valid without regeneration.
The owner decides to retain the existing clips and decline regeneration on 2026-10-01.
Do not regenerate them as part of PHASE 7.
The procedure below remains available for a future separately approved change.

## Generate the vocabulary

The shared vocabulary is `frontend/src/features/spoken/vocabulary.json`.
It supplies note labels and localized spoken names for letters and solfège.
The generator sends only these public names to OpenAI.
It never sends exercises, original images, MusicXML, user data, or credentials in the speech input.
The browser identifies the voice as AI-generated.

**Caution:** Generation calls a paid external API.
Keep the API key private and outside every `VITE_*` setting.

1. Set `OPENAI_API_KEY` in the root `.env` file.
2. Select `SPOKEN_MODEL` and `SPOKEN_VOICE`.
   To compare accents, set a separate `SPOKEN_OUTPUT` directory and try a different `SPOKEN_VOICE` value.
   Current OpenAI voice names include `alloy`, `ash`, `ballad`, `coral`, `echo`, `nova`, `onyx`, `sage`, `shimmer`, `verse`.
   Repeat with another directory and voice, then keep the committed set that sounds best.
3. Run the generator from the repository root.

```sh
PYTHONPATH=backend uv run python -m worker.generate_spoken
```

4. Verify the complete result without another API call.

```sh
PYTHONPATH=backend uv run python -m worker.generate_spoken --check
```

5. Listen to all names and suffixes in all 3 languages.
6. Confirm natural speech without singing, extra words, clipped beginnings, or clipped endings.
7. Format the generated JSON files.

```sh
npm run format --workspace frontend
```

8. Commit `frontend/public/solfege/` with its manifest and receipts.
9. Build the frontend only after the complete set passes inspection.

The output contains 66 AAC files under `<language>/<naming>/`.
Each directory contains 7 names and 4 accidental suffixes.
Equal text within one language reuses a generated clip.
Each receipt records the content hash and generation settings.
The final manifest appears only after every expected file passes verification.
Verification checks the manifest version, exact path set, settings, hashes, AAC codec, MP4 container, duration, and byte limit.

An interrupted run reuses files with matching receipts.
A crash between audio replacement and receipt replacement can require one repeated request.
Changed settings or damaged recorded files cause an explicit error.
Use a separate `SPOKEN_OUTPUT` directory for intentional regeneration with another model or voice.
Keep the old complete directory until the new set passes inspection.
The default output path is the only path that Vite packages automatically.
Do not publish a partial directory or remove another directory automatically.

OpenAI failures report stable codes without provider response bodies or API keys.
The generator bounds response bytes and network waits.
The existing media helper bounds conversion time and removes application secrets from subprocess environments.
No runtime container receives the OpenAI key.
The shared `Settings` class requires database configuration, but generation does not connect to PostgreSQL.

## Timing and supported scores

The parser accepts one part and one staff with explicit positive durations and divisions.
It applies division changes in document order.
Written duration values include dots and tuplets.
Rests reserve silence; matching consecutive ties merge into one spoken event.
The parser preserves each written index for the score cursor.
Pitch alterations select sharp, flat, double-sharp, or double-flat suffixes.
Natural pitches need no suffix.
Octaves remain in the parsed pitch, but speech does not announce octave numbers.

Unsupported chords, grace notes, multiple voices, repeats, navigation, ornaments, or malformed ties produce an explicit error.
Empty measures also fail instead of silently removing time.
The parser does not repair recognition errors; manager approval remains necessary.

The scheduler uses the Web Audio clock, not chained timers.
Each note occupies `beats * 60 / BPM` seconds.
The name and optional suffix share that slot.
Playback rate never drops below 1; the word keeps its natural pitch and voice.
Silence fills the remaining duration after the word, instead of a slower, lower-pitched voice.
The scheduler speeds up the word only when it does not fit at the natural rate, up to the configured maximum.
Conservative AAC frame timings select a safe integer tempo before the first playback.
Decoded buffer lengths confirm the tempo before scheduling.
The low-level planner retains `SPOKEN_TEMPO_TOO_FAST` for callers that bypass automatic fitting.
The player does not truncate speech or overlap the next note.
The preferred tempo is 72 BPM; the preferred slider range is 40–160 BPM.
Short notes can extend the minimum below 40 BPM, while each score imposes a safe maximum.
The complete-duration limit remains active; impossible scores report an explicit unsupported-score or duration error.
Tempo changes stop speech and apply to the next explicit start.

Browser storage remembers tempo per account, exercise, immutable score version, language, and naming choice.
Storage failures show a localized error; clearing storage removes these preferences.
Installed Safari applications can have separate browser storage.

Export conservative timing metadata without regeneration:

```sh
PYTHONPATH=backend uv run --locked python -m worker.generate_spoken --write-timings
```

The command verifies existing assets and writes `timings.json`; it makes no OpenAI request and changes no voice files.
Normal generation also exports timings.
Full AAC frame counts include decoder padding; container duration alone can underestimate decoded speech length.

The cursor marks the first written note of a tied event for its combined duration.
The animation clock updates the cursor; the audio clock controls sound.
Changing note labels preserves the speech schedule and restores the current cursor.

## Authorization and lifecycle

Only an approved score exposes speech controls.
Each start checks current approval and the exact job version before fetching protected MusicXML again.
A stale manager preview cannot authorize speech.
Starting speech resumes `AudioContext` directly within the click handler for Safari.
There is no automatic playback after navigation or tempo changes.

Speech pauses the exercise recording; starting that recording stops speech.
Stopping, navigation, hidden tabs, page exit, logout, and score or setting changes cancel pending and scheduled sound.
Speech does not create or complete recorded-audio journal sessions.
Image-only speech also creates no journal row.

Generated vocabulary clips are public application assets, not uploaded exercise files.
The Docker build explicitly includes public voice assets and application installation assets.
Private originals, exercise recordings, and MusicXML retain authenticated delivery.
Missing clips, invalid media, unsupported notation, and audio failures show localized errors.

## Acceptance after generation

1. Complete the student guide's PHASE 6 checklist in Chrome and Safari.
2. Compare the spoken sequence with an approved original image.
3. Check letters and solfège in Russian, English, and Spanish.
4. Check rests, dotted notes, ties, and every accidental suffix.
5. Compare slow and fast tempos without cut words or overlapping notes.
6. Confirm silence after a short word in a long note.
7. Revoke approval before another start and confirm rejection.
8. Confirm that speech does not change recorded-audio completion.

Headless Chrome verifies decoded timing, silence, and cursor behavior with synthetic signals.
It also verifies actual AAC decoding, scheduled signal output, and silent rests for every language and naming combination.
It does not establish voice quality or audible speaker output.
The owner must confirm those checks with generated speech.
