# Glossary

This document defines terms for the risk prototypes.

Prerequisites:
- Read `docs/PRODUCT_BRIEF.md`.

| Term | Meaning |
|---|---|
| OMR | Optical music recognition, which converts an original image into machine-readable notation. |
| MusicXML | The notation format that Audiveris exports. |
| event | One written note or rest in the original image or MusicXML. |
| recognition percentage | The percentage calculated from event errors against the original image. |
| structural error | An incorrect clef, key signature, time signature, or measure structure. |
| risk prototype | Disposable code that tests a technical requirement before product implementation. |
| MXL | A ZIP container for MusicXML, with the `.mxl` extension. |
| image ID | The SHA-256 identifier of a locally built Docker image. |
| substitution | One expected event with an incorrect pitch or duration in the recognized output. |
| omission | One expected event missing from the recognized output. |
| extra event | One recognized event absent from the original image. |
