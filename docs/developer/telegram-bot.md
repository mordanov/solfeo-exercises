# Telegram ingestion prototype

This document describes the restricted Telegram audio prototype and its VPS activation requirements.

Prerequisites:
- Read `docs/PHASES.md`, `docs/DECISIONS.md`, and `docs/STATUS.md`.
- Create a dedicated bot through the official Telegram `@BotFather`.
- Obtain the numeric Telegram user IDs that may send audio.
- Use Python 3.12, uv, Docker, ffmpeg, ffprobe, and file.

## Scope and current state

The owner approves a Telegram bot prototype and deployment on the existing VPS.
This remains PHASE 0.5, not the product exercise workflow.
The owner selects the bot to replace product PWA audio sharing on 2026-09-29.
The historical PWA result remains failed and no longer gates the selected import path.

The worker accepts private messages only from the configured sender allowlist.
It accepts `audio`, `voice`, and `document` attachments, including forwarded attachments.
It downloads through Telegram `getFile`, checks the actual file type, and converts audio to AAC `.m4a`.
It does not download message links.
It does not create exercises, expose files, or add a database or Redis.

The implementation, image publication, and VPS activation are complete.
The owner supplies the dedicated token and sender allowlist privately.
The bot runs at `https://t.me/solfeo_exercises_bot`.
The owner confirms one successful real audio receipt and playback.
The remaining manual checklist results are not recorded.

### Initial staging: 2026-09-29

| Item | Result |
|---|---|
| Application commit | `ac3442ebcc1a05df5fe2ccde2ce6d274e5d78641` |
| Shared configuration commit | `3b94837`, on shared `main` and the VPS |
| Published and pinned digest | `sha256:5cc577ff83e00f2bb66ecbd1dae24defa5baccdbb553db857cc1048667db5d67` |
| Runtime | x86-64, UID 1000 |
| Python checks | 27 tests, Ruff, and strict mypy pass locally and in CI |
| Container check | Simulated Telegram, actual Opus-to-AAC conversion, file permissions, and durable offset pass |
| Existing services | All 43 containers retain their IDs and start times |
| Live Telegram access | Not attempted; dedicated credentials are missing |

The successful publication run is
[`36539611695`](https://github.com/mordanov/solfeo-exercises/actions/runs/36539611695).
The published image is available on the VPS, and the shared `.env` pins its digest.
The staging commit excludes the worker from the global manifest.
The staging commit uses `[skip ci]` to avoid the unrelated general deployment.
The isolated runtime check uses a separate temporary volume and no network.
The temporary test volumes are removed after verification.

### Verified activation: 2026-09-29

The owner fills the ignored local `prototypes/telegram/.env`.
Both the local configuration and the shared VPS `.env` use mode `0600`.
Only validated bot settings cross SSH; the transfer does not print values or create a secret patch file.
The VPS data path remains `/data`, and the image digest remains unchanged.

Shared commit `5e2f6c0` registers the worker under `workers` in `sites.yaml`.
The commit uses `[skip ci]` to avoid the general deployment.
The targeted start adds only `web-folders-solfeo-telegram-prototype-1`.
All 43 pre-existing containers retain their IDs and start times.

| Check | Result |
|---|---|
| Telegram identity and webhook | Checks pass locally and from the VPS; no webhook exists |
| Worker state | Running and healthy, with 0 restarts during verification |
| Polling | The heartbeat advances during repeated Telegram polls |
| Isolation | UID 1000, read-only root filesystem, no published ports |
| Audio at activation check | 0 saved files; no processed-update checkpoint yet |

No real audio message reaches the worker during this activation check.
Startup verification does not replace the owner's attachment tests.
### Owner-confirmed receipt: 2026-09-29

The owner reports that the bot works and confirms its success reply.
The reply identifies `199163078.m4a`, with a converted size of 636644 bytes.
This confirms one successful real-message receipt, not only a simulated API check.
The owner subsequently confirms successful playback of the saved audio.
The specific attachment type is not recorded.
The remaining attachment and unauthorized-sender checks remain open.
The owner explicitly replaces the product PWA requirement with Telegram audio import.

### Restart verification: 2026-09-29

A targeted VPS restart preserves the hash of the saved audio and the recorded bot identity.
The persisted update offset does not regress.
The worker returns to healthy status.
All 43 unrelated containers retain their IDs and start times.
The comparison runs on the VPS without copying audio or private state into this repository.

### Product follow-up

PHASE 4 integrates the bot with manager accounts, exercises, and the common file pipeline.
The prototype remains a risk check, not product authentication or exercise creation.
The product must verify that a linked Telegram sender is an active manager.
The account-linking method and import interaction require a PHASE 4 plan.
The web application remains the main interface; the bot supplies the audio import path.
Do not remove the deployed PWA prototype or its evidence without a separate cleanup task.

## Local setup

Warning: tokens must not appear in Git, chat, screenshots, shell history, or logs.

1. Open `prototypes/telegram/`.
2. Copy `.env.example` to `.env`.
3. Restrict the configuration file with `chmod 600 .env`.
4. Edit the token and allowed user IDs locally.

   ```dotenv
   SOLFEO_TELEGRAM_PROTOTYPE_TOKEN=<dedicated-BotFather-token>
   SOLFEO_TELEGRAM_PROTOTYPE_ALLOWED_USER_IDS=[123456789]
   ```

5. Install locked dependencies with `uv sync --frozen`.
6. Run the checks.

   ```sh
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy bot.py tests
   uv run pytest -q
   ```

7. Start the Docker worker with `docker compose up --build -d --wait`.
8. Stop the local worker before starting the same bot on the VPS.

Do not run 2 pollers for the same bot.
Startup checks `getMe` and refuses a configured webhook.
The worker does not remove existing webhooks automatically.
An exclusive volume lock also prevents concurrent workers using the same data directory.

The prototype uses HTTPX for bounded streaming and pydantic-settings for validated configuration.
It does not require a Telegram SDK.
The Docker image installs ffmpeg and file for conversion and magic-byte inspection.
The Python base image and Python dependencies are pinned; operating-system package repositories remain unpinned.

## Configuration

All application settings use the `SOLFEO_TELEGRAM_PROTOTYPE_` prefix.
The complete variable names and defaults appear in `.env.example`.

| Suffix | Default | Purpose |
|---|---|---|
| `TOKEN` | Required | Dedicated BotFather token; secret |
| `ALLOWED_USER_IDS` | Required | Nonempty JSON array of positive numeric user IDs |
| `LANGUAGE` | `ru` | Bot replies: `ru`, `en`, or `es` |
| `DATA_DIR` | `data` locally; `/data` in Docker | Private audio and checkpoint directory |
| `MAX_FILE_BYTES` | `20000000` | Maximum downloaded and converted file size |
| `STORAGE_LIMIT_BYTES` | `200000000` | Admission limit for retained audio |
| `MIN_FREE_BYTES` | `100000000` | Free disk reserve, in addition to download/conversion space |
| `MAX_AUDIO_SECONDS` | `900` | Maximum audio duration |
| `POLL_SECONDS` | `25` | Telegram long-poll duration |
| `HTTP_TIMEOUT_SECONDS` | `15` | Network timeout; polling adds its wait duration |
| `DOWNLOAD_TIMEOUT_SECONDS` | `90` | Overall download budget, checked between chunks |
| `MEDIA_TIMEOUT_SECONDS` | `120` | Timeout for each media subprocess |
| `RETRY_SECONDS` | `5` | Retry delay for temporary API failures |
| `HEALTH_MAX_AGE_SECONDS` | `600` | Maximum checkpoint age for a healthy worker |
| `FILE_BINARY` | `/usr/bin/file` | Magic-byte inspection executable |
| `FFPROBE_BINARY` | `/usr/bin/ffprobe` | Audio inspection executable |
| `FFMPEG_BINARY` | `/usr/bin/ffmpeg` | AAC conversion executable |
| `AUDIO_BITRATE` | `128k` | AAC output bitrate |

The shared VPS configuration also defines `SOLFEO_TELEGRAM_PROTOTYPE_IMAGE`.
Set it to a published registry digest.
The local Compose file overrides the data path to match its private volume.

The hosted Telegram API limits downloads to 20 MB.
See the [official FAQ](https://core.telegram.org/bots/faq#how-do-i-download-files).
The prototype uses a conservative 20,000,000-byte maximum.
Storage admission reserves the maximum file size, even for a smaller incoming file.
It rejects new files when capacity is insufficient; it does not delete previously accepted audio.

## Processing and failure behavior

The worker checks both the sender ID and private chat ID before making file API calls.
Unauthorized messages produce an `ACCESS_DENIED` log entry without a reply or download.
The worker does not log tokens, request URLs, message contents, sender IDs, or original filenames.

The download stays on `api.telegram.org`.
Redirects and unsafe returned paths fail explicitly.
Declared sizes and streamed byte counts must satisfy the size limit.
Downloads with an inconsistent reported size fail without claiming receipt.

The file utility inspects magic bytes, not the Telegram MIME label or filename.
ffprobe checks for audio, duration, and unwanted video streams.
Attached cover art does not prevent audio extraction.
Media subprocesses receive no bot credentials and cannot use network protocols.
Conversion bounds duration, output size, and subprocess execution time.

The private volume stores generated names such as `10.m4a`, never client-supplied paths.
Successful conversion removes the temporary downloaded original.
An abrupt process kill can leave a private temporary directory; no public route serves it.
The worker saves and synchronizes the final file before sending a success reply.
Replies state explicitly that no exercise exists.

The worker checkpoints the next update offset only after processing and replying.
After a retry, an existing saved file prevents duplicate conversion.
A lost reply acknowledgement can cause a repeated reply; exactly-once notification is not guaranteed.
Temporary API errors retry, and Telegram's `retry_after` controls rate-limit waits.
Corrupt checkpoints, changed bot identity, and webhook conflicts fail explicitly instead of resetting state.
Persistent reply failures require operator attention; the worker does not silently acknowledge them.

The heartbeat records successful polling and completed processing.
Health fails when the heartbeat is missing, invalid, or too old.
The worker runs as UID 1000 with a read-only root filesystem and a private writable volume.

## VPS staging and activation

The target image is `ghcr.io/mordanov/solfeo-telegram-prototype`.
The publishing workflow validates the prototype before publishing an x86-64 commit tag.
It does not deploy automatically.

Warning: pushing shared `main` normally triggers the general deployment.
Use the established targeted synchronization procedure instead of restarting unrelated services.

The shared service uses the optional `solfeo-telegram-prototype` profile.
It has no ports, nginx dependency, domain, or certificate requirement.
Do not add it to `sites.yaml` before credentials exist.
The general deployment starts explicitly listed services, even when their profiles are optional.

After the owner provides the dedicated credentials:

1. Validate the local `.env` without printing secret values.
2. Transfer only this bot's settings to the shared VPS `.env` through SSH.
3. Set `DATA_DIR` to `/data` on the VPS.
4. Set `IMAGE` to the verified registry digest.
5. Add the worker registration to the shared manifest.

   ```yaml
   - id: solfeo-telegram-prototype
     compose_services: [solfeo-telegram-prototype]
   ```

6. Commit and synchronize that configuration without triggering the general deployment.
7. Start only the bot.

   ```sh
   docker compose pull solfeo-telegram-prototype
   docker compose up -d --no-deps --wait solfeo-telegram-prototype
   ```

8. Confirm `BOT_VERIFIED`, successful polling, and healthy status.
9. Run the owner's real-message checklist in `docs/user/telegram-prototype.md`.

Do not copy the shared `.env` into this repository.
Do not print `docker compose config` output containing credentials.
Do not replace the VPS `.env` with the local prototype file.

For rollback, restore the prior image digest and recreate only this worker.
Preserve the audio volume and checkpoint.
Do not reuse that volume with a different bot identity.
The current worker is active, and the owner confirms successful receipt and playback.
Full checklist acceptance remains pending.
