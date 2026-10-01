# Telegram audio prototype

This document preserves the historical checks for the superseded Telegram audio prototype.

Prerequisites:
- Read the Telegram import procedure in `manager.md`.
- Keep the old poller stopped while the product bot is active.

The product worker replaces the prototype poller in PHASE 4.
Use the Telegram import procedure in `manager.md`.
Do not restart the old poller while the product bot is active.

Historical prerequisites:
- Use `https://t.me/solfeo_exercises_bot`.
- Ask the operator to allow your numeric Telegram user ID.
- Wait for confirmation that the worker is active on the VPS.

The prototype activation record confirms an active worker on 2026-09-29.
The product transition later stops that prototype and preserves its files.
The owner confirms successful audio receipt and playback on 2026-09-29.
The Telegram bot replaces PWA sharing as the selected product audio import path.
The owner confirms the remaining manual checks on 2026-09-29.
The confirmation closes PHASE 0.5; device versions and per-message evidence remain unrecorded.

The bot stores audio on the server as AAC `.m4a`.
It does not create an exercise or provide a public download link.
The default limits are 20,000,000 bytes per file and 900 seconds of audio.
The bot reports a capacity error rather than deleting earlier files.

1. Open `https://t.me/solfeo_exercises_bot` in Telegram.
2. Send `/start`.
   The bot explains which attachments it accepts.
3. Send an audio file as an attachment.
   The bot confirms the generated filename and converted size after saving.
4. Forward a Telegram message containing an audio attachment.
   The bot confirms that it saved the audio.
5. Send or forward a voice message.
   The bot confirms that it saved the audio.
6. Send an audio file as a document.
   The bot checks the actual file contents before confirming receipt.
7. Send a message containing only a link.
   The bot reports `NO_AUDIO` and does not download the link.
8. Ask the operator to inspect the saved AAC files.
   The operator checks that the expected audio plays.
9. Record the Telegram version, tested attachment types, and any error codes.

For audio from WhatsApp, transfer the actual file into the Telegram bot's chat.
Save the audio first if direct sharing does not attach the file.
Sending only a message link does not transfer its audio.

The operator confirms that a VPS restart preserves the saved audio and update checkpoint on 2026-09-29.
The owner confirms the live unauthorized-sender check with the remaining checks.
An unauthorized sender receives no response, and the worker downloads no file.

Do not post the bot token in chat or include it in a screenshot.
The earlier PWA sharing failure remains recorded; PWA retesting is no longer required for this import path.
