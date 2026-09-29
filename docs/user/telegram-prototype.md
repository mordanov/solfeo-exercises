# Telegram audio prototype

This document explains how to check audio ingestion through the dedicated Telegram bot.

Prerequisites:
- Obtain the dedicated bot's username from the operator.
- Ask the operator to allow your numeric Telegram user ID.
- Wait for confirmation that the worker is active on the VPS.

The bot stores audio on the server as AAC `.m4a`.
It does not create an exercise or provide a public download link.
The default limits are 20,000,000 bytes per file and 900 seconds of audio.
The bot reports a capacity error rather than deleting earlier files.

1. Open the bot's private chat in Telegram.
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

The operator must also test an unauthorized sender and a worker restart.
An unauthorized sender receives no response, and the worker downloads no file.
A restart must preserve accepted audio and the update checkpoint.

Do not post the bot token in chat or include it in a screenshot.
Bot success does not confirm that the separate PWA sharing path works.
