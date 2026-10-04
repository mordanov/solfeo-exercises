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
| login session | A persistent authenticated session, distinct from a listening session or database session. |
| CSRF | Cross-site request forgery; origin and session-token checks reject unauthorized browser mutations. |
| color scheme | A predefined set of compatible colors for buttons, text, backgrounds, panels, and control states. |
| scrypt | A memory-hard password hashing algorithm with a random salt for each password. |
| multipart form | An HTTP request containing separate text and file parts. |
| MIME type | A content-type identifier determined from file signatures for uploads. |
| soft deletion | Marking an exercise as deleted while preserving its database record and files. |
| AAC | The audio codec used inside each converted MP4 audio file. |
| MiB | 1048576 bytes. |
| listening event | A start, heartbeat, end, or ended request for one listening session. |
| heartbeat | A periodic playback update that preserves the current session's maximum position. |
| beacon | A browser request queued during page exit without custom headers. |
| sequential pointer | The saved next exercise for one student in ordered mode. |
| snapshot | Values retained when the first listening event creates a journal row. |
| linking code | A single-use secret that associates a Telegram sender with an authenticated manager. |
| staged import | Converted audio owned by a manager before application to an exercise. |
| update offset | The next Telegram update ID requested after durable intake. |
| OMR lease | A time-limited job claim with a unique token that prevents stale results from replacing current results. |
| OpenSheetMusicDisplay | The browser library that draws a score from MusicXML. |
| speech clip | A generated recording of one public note name or accidental suffix. |
| speech receipt | A file that records a clip hash and the settings used for generation. |
| playback rate | The ratio between a clip's playback speed and its original speed. |
| CSP | Content Security Policy, which restricts browser resource loading and embedding. |
| HSTS | HTTP Strict Transport Security, which tells a browser to use HTTPS for the current hostname. |
| structured log | A JSON record with fixed fields for operational events, without request bodies or credentials. |
| disk reserve | Free storage retained after image downloads and extraction. |
| image budget | Free storage allocated for a new release's compressed images and extracted layers. |
| smoke check | A short end-to-end procedure that checks the deployed application's main functions. |
| Material UI | The React component library used for the application's visual design. |
| DataGrid | The Community table component that shows the existing server pages without additional filtering or sorting. |
| theme | The light or dark colors, typography, and shared visual rules for the application. |
| Emotion | The style engine used by Material UI. |
| Roboto | The application font, served from local assets. |
| AST | Abstract syntax tree, which represents code structure for comparison. |
| avatar | The character image associated with a game player. |
| player profile | A named game character owned by an account, with saved progress and an avatar. |
| round | A group of 7 questions in Guess the Note. |
| season | A numbered group of game rounds associated with one player profile. |
| avatar level | A character appearance numbered from 1 to 10, derived from the player's total XP. |
| XP | Experience points earned from correct game answers and a winning round, excluding assistance bonuses. |
| assistance bonus | Points added once per completed game round for disabled hint or correct-answer options. |
| rules version | The stored number that selects a round's grading and bonus rules. |
| sprite sheet | An original image containing multiple character appearances and emotions. |
| staff | The 5 horizontal lines that specify vertical note positions. |
| clef | A symbol that identifies the pitch of a reference line on a staff. |
| glyph | One symbol defined by a font's outline data. |
| SMuFL | Standard Music Font Layout, which specifies musical glyph names, code points, and registration conventions. |
| MIDI | Musical Instrument Digital Interface, whose note numbers identify pitches and octaves. |
| Web Audio | The browser API for generating, processing, and scheduling sound. |
| audio context | The Web Audio object that provides an audio clock and connects sound sources to output. |
| triangle tone | A synthesized musical sound with a triangle-shaped waveform. |
| piano sample | A recording of one piano pitch that Web Audio plays without generating an oscillator tone. |
| velocity layer | A separate recording made at one playing intensity, not an amplitude copy of another recording. |
| piano asset | The single public JSON file that contains the reduced piano's encoded AAC samples. |
| scientific octave | An octave number in which middle C is C4 and the next C is C5. |
