# Manager checks

This document explains the manager's manual checks for the current health page.

Prerequisites:
- Use Chrome or Safari.
- Start the local stand with `docs/developer/setup.md` only for localhost checks.

The current page does not provide sign-in, user management, or exercise management.
The Telegram prototype remains separate and does not create exercises.
The local stand now includes PostgreSQL and an empty schema.
Ask the operator to use `docs/developer/data-model.md` for the database restart check.
This change adds no manager actions to the web page.
The deployed health page is available at `https://solfeo.miveralta.ru/`.
Use this HTTPS address for final VPS acceptance instead of the local address below.

1. Open `http://127.0.0.1:18080/`.
   The page shows the service status.
2. Select Russian, English, and Spanish in the language selector.
   The page text and browser title change.
3. Click the button to check the status again.
   The page shows a pending state, then the current result.
4. Ask the operator to stop only the local backend.
5. Click the button to check the status again.
   The page shows an error instead of an old successful result.
6. Ask the operator to restart the local backend.
7. Click the button to check the status again.
   The page confirms that the backend is available.

The status checks the backend process, not the database or Telegram bot.
The language selection does not persist after a reload.
For final VPS acceptance, repeat the language and status checks in Chrome and Safari at the HTTPS address.
Block `/api/health` in browser developer tools for the failure scenario.
The next status check shows an error; removing the block lets a repeated check succeed.
The Telegram bot and `/prototype-share/` remain separate.
