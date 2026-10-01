# Adding a language

This document explains the coordinated changes required for an approved additional interface language.

Prerequisites:
- Read `env-variables.md`, `glossary.md`, and `spoken-notes.md`.
- Obtain approval before expanding the supported Russian, English, and Spanish language set.
- Prepare the locked development tools from `setup.md`.

The current product supports only `ru`, `en`, and `es`.
Adding a translation file alone does not add a supported language.
Account schemas, database constraints, frontend configuration, Telegram replies, and speech vocabulary must agree.

1. Add the language to `frontend/src/configuration.ts` and its validation tests.
2. Add a complete locale file under `frontend/src/i18n/locales/`.
3. Register that resource in `frontend/src/i18n/index.ts` and `locales.test.ts`.
4. Add the translated selector name in every locale and update `components/AccountUi.tsx`.
5. Extend the backend settings, API literals, and account model constraints.
6. Add an Alembic migration for existing database constraints.
7. Add Telegram replies in `worker/telegram.py`.
8. Extend the note labels and spoken vocabulary.
9. Obtain separate approval before generating additional paid speech assets.
10. Update the generator's accent instructions and the manifest expectations.
11. Update the environment reference and both user guides.
12. Run all tests, quality hooks, dependency audits, and container checks.
13. Check saved settings, labels, speech, and unknown-page messages in Chrome and Safari.

Keep existing language defaults unchanged unless the owner approves a separate behavior change.
Do not regenerate the existing 66 clips to add unrelated translations.
Use a compatible migration plan before production deployment.
