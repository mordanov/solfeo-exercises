# Student checks

This document explains the student's manual checks for the current health page.

Prerequisites:
- Use Chrome or Safari.
- Start the local stand with `docs/developer/setup.md` only for localhost checks.

The current page does not provide sign-in, exercises, playback, or saved user settings.
It does not grant manager access or let a student import audio.
The PostgreSQL foundation does not change these limits or add new student actions.
The deployed health page is available at `https://solfeo.miveralta.ru/`.
Use this HTTPS address for final VPS acceptance instead of the local address below.

1. Open `http://127.0.0.1:18080/`.
   The page shows the service status.
2. Select Russian, English, and Spanish in the language selector.
   The page text and browser title change.
3. Click the button to check the status again.
   The page shows the backend result or an explicit error.

The language selection lasts only until a reload.
The status does not confirm that exercises or the Telegram bot are available.
For final VPS acceptance, repeat these checks in Chrome and Safari at the HTTPS address.
The Telegram bot and `/prototype-share/` remain separate.
