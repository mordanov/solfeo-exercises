# Manager checks

This document explains the manager's manual checks for the current local health page.

Prerequisites:
- Ask the operator to start the local stand with `docs/developer/setup.md`.
- Use Chrome or Safari on the same computer.

The current page does not provide sign-in, user management, or exercise management.
The Telegram prototype remains separate and does not create exercises.
The local stand now includes PostgreSQL and an empty schema.
Ask the operator to use `docs/developer/data-model.md` for the database restart check.
This change adds no manager actions to the web page.
After successful CD, the same health page is available at `https://solfeo.miveralta.ru/`.
The operator confirms deployment before the VPS checks.

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
Use browser developer tools to simulate an offline connection without stopping the production backend.
The next status check shows an error; restoring the connection lets a repeated check succeed.
The Telegram bot and `/prototype-share/` remain separate.
