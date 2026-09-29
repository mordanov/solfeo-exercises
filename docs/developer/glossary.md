# Glossary

This document defines terms for the application and its risk prototypes.

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
| byte range | A requested portion of a file, identified by byte offsets. |
| internal location | An nginx location that rejects direct client requests. |
| X-Accel-Redirect | A response header that instructs nginx to serve an internal location. |
| Basic authentication | HTTP authentication with a username and password; this prototype uses disposable local credentials. |
| fast start | MP4 layout with playback metadata before the audio data. |
| PWA | Progressive web app that supports installation through the browser. |
| share target | A manifest entry that lets an installed PWA receive shared data. |
| service worker | Browser code that handles requests within a defined scope. |
| IndexedDB | Browser storage for structured data and files. |
| Telegram bot | A service that receives Telegram messages through the Bot API. |
| audio import | Transfer of an audio attachment into the application, with manager authorization and file validation. |
| database session | A SQLAlchemy object that manages database operations within one request or worker operation. |
| connection pool | A bounded set of database connections that the backend reuses. |
| migration | A versioned change to the database schema. |
| schema revision | The migration identifier recorded in the database by Alembic. |
| liveness | Confirmation that the backend process responds, without proving database readiness. |
| DML | Data operations such as selecting, inserting, updating, and deleting table rows. |
| release bundle | An archive with verified image references, deployment files, source provenance, and file hashes. |
