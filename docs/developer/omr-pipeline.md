# OMR risk prototype

This document defines the sample set and evaluation criteria for the PHASE 0.5 OMR prototype.

Prerequisites:
- Read `docs/PRODUCT_BRIEF.md`, `docs/PHASES.md`, and `docs/DECISIONS.md`.
- Obtain the owner's local `examples/` directory.
- Read the terms in `docs/developer/glossary.md`.
- Install Python 3.12, uv, and Docker.
- Start a Docker daemon with enough space for a Java build.

## Scope and current state

The owner approves these criteria on 2026-09-28.
The sample preparation task and the Audiveris prototype run are complete.
The report below contains actual results from all 10 original images.
The owner confirms the recommendation to continue with Audiveris on 2026-09-28.
Detailed owner verification of the event comparisons remains unconfirmed.
The prototype does not implement product code or select a replacement engine.

## Sample set

The initial evaluation uses 10 original images.
The selection follows file numbers, not recognition results.
It does not establish accuracy across other exercise types.

| Local original image | Prototype copy |
|---|---|
| `examples/ejercicio_1.jpeg` | `prototypes/omr/samples/ejercicio_1.jpeg` |
| `examples/ejercicio_2.jpeg` | `prototypes/omr/samples/ejercicio_2.jpeg` |
| `examples/ejercicio_3.jpeg` | `prototypes/omr/samples/ejercicio_3.jpeg` |
| `examples/ejercicio_4.jpeg` | `prototypes/omr/samples/ejercicio_4.jpeg` |
| `examples/ejercicio_5.jpeg` | `prototypes/omr/samples/ejercicio_5.jpeg` |
| `examples/ejercicio_6.jpeg` | `prototypes/omr/samples/ejercicio_6.jpeg` |
| `examples/ejercicio_7.jpeg` | `prototypes/omr/samples/ejercicio_7.jpeg` |
| `examples/ejercicio_8.jpeg` | `prototypes/omr/samples/ejercicio_8.jpeg` |
| `examples/ejercicio_9.jpeg` | `prototypes/omr/samples/ejercicio_9.jpeg` |
| `examples/ejercicio_10.jpeg` | `prototypes/omr/samples/ejercicio_10.jpeg` |

`examples/ejercicio_11.jpeg` remains outside the initial evaluation for a later check.
The corresponding audio files use the `.opus` extension.
OMR evaluation does not use audio as the reference.

**Caution:** Keep original images, audio, and generated MusicXML local.
Do not commit these files or include them in public reports.

`prototypes/omr/.gitignore` excludes `samples/` and `output/`.
The local `examples/` directory must also remain outside Git.
A fresh clone does not contain the sample files.

To prepare another local checkout:

1. Obtain the same original images from the owner.
2. Exclude `/examples/` through the local `.git/info/exclude` file if no existing rule excludes it.
3. Create `prototypes/omr/samples/`.
4. Copy images 1 through 10 into that directory without changing their contents.
5. Compare each copy with its original image.
6. Confirm that Git ignores the samples and output paths.

## Evaluation procedure

1. Record the Audiveris version, Docker image digest, command, configuration, and runtime environment.
2. Run Audiveris in Docker against each selected original image.
3. Retain generated MusicXML and diagnostic output under `prototypes/omr/output/`.
4. Count the expected events in each original image.
5. Compare those events with the exported MusicXML in notation order.
6. Record each substitution, omission, and extra event.
7. Calculate the recognition percentage.
8. Record structural errors separately.
9. Classify each image with the thresholds below.
10. Report all results, including failures.

### Event comparison

A note matches only when its pitch, accidental, octave, and duration match the original image.
A rest matches only when its duration matches.
A substituted event counts as 1 error, even when several attributes differ.
An omitted event counts as 1 error.
An extra event counts as 1 error.

An omission or extra event must not make all later events count as substitutions.
The comparison follows matching events to identify the actual errors.
The original image provides the reference, not Audiveris output or the audio recording.

Let `N` equal the expected event count.
Let `E` equal the sum of substitutions, omissions, and extra events.

`recognition percentage = 100 × max(0, 1 − E / N)`

For example, 20 errors across 100 expected events give 80 %.
50 errors across 100 expected events give 50 %.
More errors than expected events give 0 %.

An image with no expected events cannot use this formula.
Such an image requires owner review before evaluation.

### Classification

| Classification | Rule |
|---|---|
| Fully recognized | Recognition percentage is at least 80 %. |
| Partly recognized | Recognition percentage is at least 50 % and below 80 %. |
| Failed | Recognition percentage is below 50 %, or no usable MusicXML exists. |

These labels describe the agreed thresholds, not perfect notation.
The classification uses the unrounded percentage.
An unusable export receives `failed`, with the recognition percentage marked `not evaluated`.
A pending run receives `not run`, not `failed`.

Clef, key signature, time signature, and measure structure require separate review.
Structural errors do not add separate event errors.
Their effects on note pitches or durations still count through event comparison.
The report must show structural errors even when the classification is `fully recognized`.

## Required report

The report contains 1 row per image with these fields:

- Image filename and reference to local output.
- Run outcome and failure details.
- Expected event count.
- Substitution, omission, and extra event counts.
- Recognition percentage and classification.
- Structural errors and concrete notation errors.
- Reference to the local MusicXML and diagnostics, when available.

The report also records reproducible commands and the runtime environment.
No aggregate acceptance threshold applies.
The recommendation considers all per-image results, structural errors, and limitations.
The owner reviews the recommendation before confirming an engine decision in `docs/DECISIONS.md`.

## Run the prototype

**Caution:** The build downloads public dependencies.
Recognition runs without network access and does not upload the samples.
The Docker build context excludes samples, output, and local configuration.

1. Prepare the sample copies with the procedure above.
2. Open `prototypes/omr/` from the repository root.

   ```sh
   cd prototypes/omr
   ```

3. Create `.env` from `.env.example` if no local configuration exists.

   ```sh
   cp -n .env.example .env
   ```

4. Install the locked Python dependencies.

   ```sh
   uv sync --frozen
   ```

5. Build the pinned Audiveris source.

   ```sh
   docker build -t solfeo-omr:5.11.0 .
   ```

6. Run the prototype.

   ```sh
   uv run --frozen python omr.py
   ```

The runner creates a unique directory under `output/`.
It selects images 1 through 10 and validates their presence before processing.
It resolves the image tag to an immutable image ID for the whole run.
Each container mounts 1 original image read-only and writes to its own output directory.
The runner removes only its own containers, including after a timeout.

Each image directory contains `run.json`, `console.log`, and any Audiveris output.
Successful exports use `sample.mxl`, which contains MusicXML.
`sample.omr` contains the Audiveris project, including diagnostic image data.
These files remain local.

The run directory also contains:

- `image.json`: Docker image ID, architecture, labels, and configuration.
- `settings.json`: effective settings.
- `docker-version.txt`: Docker client and server versions.
- `audiveris-version.txt`: Audiveris, Java, and OCR versions.
- `summary.json`: processing outcomes for all images.

The runner returns exit code `1` if any image fails or reaches its timeout.
It continues with the remaining images after an engine failure.
Docker setup errors stop the run with an explicit exception.
An `exported` outcome means that a file exists, not that its notation is correct.
The runner does not assign recognition percentages without manual event comparison.

### Configuration

All runtime settings use `Settings` from `pydantic-settings`.
Paths below are relative to `prototypes/omr/` when following the commands above.

| Variable | Default | Purpose |
|---|---|---|
| `OMR_IMAGE` | `solfeo-omr:5.11.0` | Locally built Audiveris image. |
| `OMR_SAMPLES_DIR` | `samples` | Directory containing the 10 selected images. |
| `OMR_OUTPUT_DIR` | `output` | Parent directory for unique runs. |
| `OMR_TIMEOUT_SECONDS` | `300` | Maximum processing time per image. |
| `OMR_CPUS` | `2` | Container CPU limit. |
| `OMR_MEMORY_MB` | `4096` | Container memory limit in Docker megabyte units. |
| `OMR_JAVA_OPTIONS` | See `.env.example`. | Heap limit and headless Java options. |

The default Java options limit the heap to 2 GiB and disable automatic display scaling.
The `-Dsun.java2d.uiScale=1` option avoids GTK initialization during headless startup.
Removing this option causes a missing GTK library error in this image.

### Prototype checks

1. Run the tests.

   ```sh
   uv run --frozen pytest -q
   ```

2. Check formatting and lint rules.

   ```sh
   uv run --frozen ruff format --check omr.py tests
   uv run --frozen ruff check omr.py tests
   ```

3. Check strict typing.

   ```sh
   uv run --frozen mypy omr.py tests
   ```

The tests cover exact classification boundaries, invalid counts, missing exports, timeouts, cleanup, configuration, sample selection, and runtime metadata.
They use synthetic data, not the owner's images.

## Recognition report: 2026-09-28

### Runtime and evidence

The native ARM64 image builds Audiveris `5.11.0` from the official source.
The source commit is `9e1e55cd2746037d059345881c53e6a6754bffbd`.
The Dockerfile pins the Java base image by digest.
Python dependency versions are in `prototypes/omr/uv.lock`.

| Component | Recorded value |
|---|---|
| Docker client / server | `28.2.2` / `27.4.0` |
| Container architecture | `linux/arm64` |
| Kernel | `6.8.0-50-generic` |
| Java | OpenJDK `25.0.4.1+1-LTS` |
| OCR engine | Tesseract `5.5.2` |
| Local image ID | `sha256:0d438974e4698d693ba08122082c4f65749a2b6532390d904c44ef1b7bcaffe3` |
| Final run | `20260928T201957Z-84f49a71` |

This locally built image has an image ID, not a published registry digest.
Source and base-image pins do not freeze operating-system package repositories.
The final run includes `os-packages.txt` as an additional local record.
An exact binary replay requires retaining the recorded local image.

Sources:

- [Official release](https://github.com/Audiveris/audiveris/releases/tag/5.11.0).
- [Pinned source](https://github.com/Audiveris/audiveris/tree/9e1e55cd2746037d059345881c53e6a6754bffbd).
- [Upstream CLI documentation](https://github.com/Audiveris/audiveris/blob/5.11.0/docs/_pages/guides/advanced/cli.md).

The final run uses unchanged original images and the default settings above.
No image preprocessing or Audiveris recognition tuning applies.
Enlarged copies assist manual review only; they are not recognition inputs.
Image 11 remains outside this evaluation.

The per-image processing times range from 1.279 s to 3.992 s, including container startup and cleanup.
Their sum is 35.199 s; this excludes image building and initial version checks.
The runner returns `1` because image 6 fails.
This is an observed recognition failure, not a failing prototype test.

### Per-image results

Copilot compares the MusicXML against a manual transcription of the original images.
Owner verification remains necessary.
`N` means expected events; `S`, `O`, and `X` mean substitutions, omissions, and extra events.
Percentages below use the approved event formula, not visual similarity.

| Original image | Export | N | S | O | X | Recognition | Classification |
|---|---|---:|---:|---:|---:|---:|---|
| `ejercicio_1.jpeg` | Yes | 21 | 0 | 0 | 0 | 100 % | Fully recognized |
| `ejercicio_2.jpeg` | Yes | 23 | 0 | 0 | 0 | 100 % | Fully recognized |
| `ejercicio_3.jpeg` | Yes | 28 | 0 | 0 | 0 | 100 % | Fully recognized |
| `ejercicio_4.jpeg` | Yes | 31 | 0 | 0 | 0 | 100 % | Fully recognized |
| `ejercicio_5.jpeg` | Yes | 33 | 0 | 0 | 0 | 100 % | Fully recognized |
| `ejercicio_6.jpeg` | No | 26 | — | — | — | Not evaluated | Failed |
| `ejercicio_7.jpeg` | Yes | 50 | 17 | 10 | 0 | 46 % | Failed |
| `ejercicio_8.jpeg` | Yes | 43 | 1 | 1 | 0 | 95.35 % | Fully recognized |
| `ejercicio_9.jpeg` | Yes | 25 | 1 | 2 | 0 | 88 % | Fully recognized |
| `ejercicio_10.jpeg` | Yes | 28 | 0 | 0 | 0 | 100 % | Fully recognized |

The result is 8 fully recognized images, 0 partly recognized images, and 2 failed images.
The `fully recognized` label does not imply error-free notation.
Image 8 has an unrounded recognition percentage of `100 × 41 / 43`.
Missing output for image 6 is not a measured 0 %.

### Notation and structural errors

| Images | Observed result |
|---|---|
| 1–5, 10 | No event errors found. Clefs, key signatures, time signatures, and 8 measure boundaries match. |
| 6 | Staff detection fails at `GRID` with `No system found`. Audiveris exits with code `1`; no MusicXML exists. |
| 7 | False octave-shifted treble clef and missing common-time signature. The first system contains incorrect pitches, durations, and omissions. |
| 8 | The first note is B2 instead of C3. Measure 4 omits its final quarter rest, leaving 3 beats instead of 4. |
| 9 | Measure 5 replaces 3 notes with one A2 half note. The expected events are E3 eighth, G3 quarter, and C4 eighth. |

Image 7 has 8, 4, 8, 4, 2, 0, 0, and 1 event errors across its 8 measures.
Its measures 1, 4, 5, and 8 have insufficient duration.
The final half rest is missing.
Image 9 also contains a `backup` element after the incorrect note in measure 5.

The comparison counts an incorrect pitch and duration on the same event as 1 substitution.
Matching later events prevents omissions from causing cascading substitutions.
Per-measure minimum edit distances independently confirm the recorded total event errors.
Clef-related pitch errors count as event errors; the report also identifies the incorrect clef.

Slurs, spacing, layout, and rendering appearance do not contribute to this event percentage.
The images do not establish quality for accidentals, complex notation, multiple voices, or other image sources.
No browser rendering or product approval workflow exists in this prototype.

### Local output locations

All paths below are relative to `prototypes/omr/`.
The run directory is `output/20260928T201957Z-84f49a71/`.

| Evidence | Path under the run directory |
|---|---|
| MusicXML for image N, except 6 | `ejercicio_N/sample.mxl` |
| Processing command, original checksum, exit code, and duration | `ejercicio_N/run.json` |
| Diagnostics, including image 6 | `ejercicio_N/console.log` |
| Audiveris project | `ejercicio_N/sample.omr` |
| Per-image event comparisons, except 6 | `ejercicio_N/review.json` |
| Combined reviewed results | `review-results.json` |

The manual reference is `output/manual-reference.json`.
The build log is `output/build.log`.
These local artifacts contain the evidence; Git contains only the prototype and this aggregate report.
The `classify` function in `omr.py` reproduces percentages from reviewed event counts.

For example:

```sh
uv run --frozen python -c 'from omr import classify; print(classify(43, 1, 1, 0))'
```

The result is `Classification(label='fully', percentage=95.34883720930233)`.

### Confirmed engine decision

**Continue with Audiveris. The owner confirms this recommendation on 2026-09-28.**
Do not replace the engine on this evidence alone.
Six images have no detected event errors, and 2 more meet the agreed threshold despite errors.
However, 2 images fail, and successful export does not establish correct notation.

The manager review requirement and original-image fallback remain essential.
The recommendation does not authorize automatic approval or a change to the existing product decisions.
`docs/DECISIONS.md` records the confirmed engine decision.
This confirmation does not establish completion of the detailed manual checks.

## Manual checks

- Confirm that the 10 images represent the intended exercises.
- Confirm that each prototype copy matches its original image.
- Review event counts and structural errors after the Audiveris run.
- Review the local evidence for images 6–9.
