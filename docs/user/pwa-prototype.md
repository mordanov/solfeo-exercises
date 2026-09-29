# Android share prototype

This document explains how to test Android audio sharing with the disposable PWA prototype.

Prerequisites:
- Use Android Chrome with WhatsApp and Telegram.
- Prepare 1 audio file below 25 MiB.
- Record the device, Android version, Chrome version, and messenger versions.

The prototype stores only the latest successful share on your device.
It does not upload audio or create an exercise.
It does not provide product login or an offline page.

1. Open `https://solfeo.miveralta.ru/prototype-share/` in Chrome.
   The prototype page opens.
2. Wait for the service worker readiness message.
   The page reports that it can receive shares.
3. Install the PWA through the Chrome menu.
   Android adds the application.
4. Share 1 audio file from WhatsApp to the installed application.
   The receipt page shows the filename, type, and size.
5. Compare the receipt with the selected file.
   The details must match.
6. Reload the page.
   The stored file remains available.
7. Use the clear action.
   The page reports that no file remains.
8. Repeat the share from Telegram.
   The receipt page shows the new file.
9. Close the installed application.
   Android returns to the previous screen.
10. Repeat a messenger share.
    The application opens and shows the receipt.
11. Record any failure and the application versions.
    A desktop test does not replace this device check.
12. Clear the final test file.
    The prototype retains no shared file.

Send only 1 file per share.
An invalid share does not replace the previous successful file.
The receipt identifies the latest successful share.

## Current Android failure

The owner reports "No audio file was received" after sharing from Telegram or WhatsApp.
The cause remains under investigation.
Opening the application does not confirm that Android provides the audio file.

1. Record whether the selected item is a voice message, audio attachment, or message link.
2. Record the exact share action and the device and application versions.
3. Save the audio to the device if the messenger permits this action.
4. Share that saved file from the Android file manager to the PWA.
5. Record the result separately from the messenger result.

A successful file-manager share is a diagnostic control, not acceptance of messenger sharing.
Do not send private message contents or private links with the report.

After the phase, remove the prototype installation and its site data.
Do not remove another application's data.
