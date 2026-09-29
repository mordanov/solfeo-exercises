# Product Telegram import

This document explains account linking, durable audio import, worker operation, and recovery.

Prerequisites:
- Read `auth.md`, `storage.md`, and `deploy.md`.
- Apply migration `0005_telegram`.
- Configure the dedicated bot token privately.
- Stop other pollers for this bot before starting the product worker.

## Account linking

A manager opens `/manager/telegram` and requests a linking code.
The API requires an authenticated active manager, completed password changes, allowed Origin, and the session CSRF token.
The code contains 256 random bits and expires after 600 seconds by default.
PostgreSQL stores only its SHA-256 hash.
A new code replaces the previous code for that manager.

The manager sends `/start <code>` in the bot's private chat.
The worker checks the sender ID and private chat ID before consuming the code.
Each manager links one Telegram sender; each sender links one manager.
An existing association with another manager cannot transfer through a new code.
Unlink the old account first.
Telegram usernames never grant permissions.

Unlinking removes the association and unused codes.
Password changes, password resets, role changes, and account deactivation also revoke them.
Emergency synchronization revokes the emergency manager's association on each backend start.
Use a normal manager account for a persistent association.
Already received imports remain owned by their original manager.

## Intake and conversion

The worker accepts `audio`, `voice`, and `document` attachments from linked, active managers.
It never downloads text links.
Unknown senders receive linking instructions, not import rights.
Groups and mismatched sender/chat identities cannot import.
The worker checks current permissions again before downloading queued audio.

Telegram's hosted API limits downloads to 20 MB.
`TELEGRAM_MAX_FILE_BYTES` defaults to a conservative 20,000,000 bytes and cannot exceed that value.
The worker also enforces `AUDIO_MAX_BYTES`.
Declared sizes and actual streamed bytes must fit the limits.
Downloads remain on `api.telegram.org`; redirects and unsafe returned file paths fail.
Network errors and rate limits return fixed error codes without logging token-bearing URLs.

The common media pipeline validates magic bytes and duration, then converts to AAC `.m4a`.
Media subprocesses do not inherit bot credentials.
An import uses a deterministic media UUID derived from its Telegram update ID.
Retrying interrupted conversion replaces the same generated output instead of creating duplicate final files.
The database commits the media reference and ready status together.
Temporary originals disappear after normal completion or failure.

An abrupt process kill can leave a private temporary directory.
It cannot expose that directory through nginx.
Do not remove media files referenced by exercises, imports, or journal rows.

## Durable processing

`telegram_state` stores the bot identity, next update offset, and heartbeat.
Changing the bot identity requires an explicit migration plan; the worker refuses it.
The worker checks the identity and refuses an existing webhook.
A PostgreSQL session advisory lock prevents concurrent product pollers.
It does not coordinate with the legacy prototype, which must remain stopped.

`telegram_updates` stores one row per accepted Telegram update ID.
The offset advances only after intake commits.
Replayed updates return the existing row.
Imports move from pending to ready or failed, then to applied.
Message-only rows preserve linking and error notifications separately from the import list.

The processor claims pending work through `FOR UPDATE SKIP LOCKED`.
It holds the transaction during download and conversion.
A crash releases the lock and leaves the import available for another attempt.
Transient errors persist attempts and the next retry time.
After the configured attempt limit, the manager can retry explicitly.
Invalid media and oversized files fail without repeated automatic downloads.

Notifications follow persistence.
If Telegram loses a reply acknowledgement, the worker can repeat the notification, but not the import or exercise.
Permanent reply rejection produces an explicit warning.
The web import list remains authoritative.

## Applying an import

Only the owning manager can list, preview, retry, or apply an import.
Previews use authenticated X-Accel-Redirect and support byte ranges.
Students and other managers cannot access the staged audio.

The manager chooses a new exercise or an existing exercise, then supplies the title and description.
Replacing audio preserves the original image, category, order, old media, and listening sessions.
The UI requires confirmation before replacing an existing audio attachment.
Applying the import reuses the converted media without another conversion.

An exercise update and the applied import status commit in one database transaction.
The import retains a hash of the selected destination, title, and description.
An identical retry returns the same exercise ID.
A retry with different choices returns `IMPORT_ALREADY_APPLIED`.
Deleting the exercise later does not make the import reusable.

## Operation

The `telegram` service uses the same immutable image as the backend.
It has no published ports, no proxy-network access, and a read-only root filesystem.
Its private media volume is writable; nginx retains read-only access.
The worker receives the bot token; the API does not need it.
An empty token disables polling explicitly.

Readiness requires a successful processing cycle in the current process and a recent database heartbeat.
The worker removes its private readiness marker at startup.
Stale state from an earlier process cannot make a new worker ready.
Deployment stops the worker before migrations and includes it in compatible rollback.
The PHASE 3 image cannot recognize `0005_telegram`; recovery needs a compatible image.

Automated checks use simulated Telegram responses and actual PostgreSQL, ffmpeg, nginx, and browser playback.
Live startup verifies the real bot identity and polling separately.
An owner-sent Telegram attachment remains part of final manual acceptance.
