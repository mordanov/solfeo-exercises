# OMR risk prototype

This document defines the sample set and evaluation criteria for the PHASE 0.5 OMR prototype.

Prerequisites:
- Read `docs/PRODUCT_BRIEF.md`, `docs/PHASES.md`, and `docs/DECISIONS.md`.
- Obtain the owner's local `examples/` directory.
- Read the terms in `docs/developer/glossary.md`.

## Scope and current state

The owner approves these criteria on 2026-09-28.
The first task prepares the samples and criteria only.
Audiveris has not run, and no recognition results exist.
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

## Manual checks

- Confirm that the 10 images represent the intended exercises.
- Confirm that each prototype copy matches its original image.
- Review event counts and structural errors after the Audiveris run.
- Review the recommendation before accepting or replacing Audiveris.
