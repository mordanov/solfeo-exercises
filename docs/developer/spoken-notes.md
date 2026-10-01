# Spoken notes

This document explains speech generation, playback timing, and the remaining acceptance checks.

Prerequisites:
- Read `setup.md` and `omr-pipeline.md`.
- Install the existing Python and frontend dependencies.
- Make `ffmpeg` and `ffprobe` available.
- Keep a valid private root `.env` file.

## Current delivery limit

PHASE 6 has no generated production clips yet.
The local environment has no `OPENAI_API_KEY`.
The generator reports `OPENAI_KEY_REQUIRED`; it does not create substitute audio.
Automated conversion checks use synthetic test signals in temporary directories, not production speech.
Do not claim audible acceptance until the actual clips pass the checks below.
The owner postpones deployment; this branch does not change either VPS.
The CLI credential cannot create a pull request or dispatch CI; GitHub returns HTTP 403.
An authorized operator must open a draft pull request for branch CI.
Do not merge that request while deployment remains postponed.

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
Playback rate remains within the configured range; silence fills the remaining duration.
A name that cannot fit at the maximum rate produces `SPOKEN_TEMPO_TOO_FAST`.
The player does not truncate speech or overlap the next note.
The user must lower the tempo.
The default tempo is 72 BPM; the default slider range is 40–160 BPM.
Tempo changes stop speech and apply to the next explicit start.

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
The Docker build explicitly includes only `frontend/public/solfege/` from the public directory.
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
It does not establish voice quality or audible speaker output.
The owner must confirm those checks with generated speech.
