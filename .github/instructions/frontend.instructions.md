---
applyTo: "frontend/**"
---

# Frontend rules

## Language and tooling
- React + TypeScript (strict) + Vite. Function components and hooks only.
- ESLint and Prettier must pass. No `any`. No `@ts-ignore` without a comment.
- Vitest and Testing Library. Test behavior that the user sees, not implementation details.

## i18n (mandatory)
- Every visible string uses `t("key")` from react-i18next. No hard-coded text in JSX, including `aria-label`, `title`, and `placeholder`.
- Languages: `ru`, `en`, `es`. Files: `src/i18n/locales/<lang>.json`. Keys are identical in all three files.
- A unit test loads all locale files and fails if a key is missing in any language or has an empty value.
- The backend returns error codes. Map each code to a key `errors.<CODE>`. Show a generic message for an unknown code.
- Dates and numbers: use `Intl` with the current UI language.
- Note names come from the user setting `note_naming` and the UI language. Put them in one module, not in components.

## Structure
- `src/api/` typed API client (one function per endpoint). `src/features/<name>/` for each feature. `src/components/` for shared UI.
- Server state: TanStack Query. Local UI state: `useState`. Do not add a global state library without asking.
- Route guards: manager routes and student routes are separate. A guard checks the role from `/api/auth/me`.

## Audio and player
- Target browsers: Chrome and Safari. Audio format is AAC (.m4a).
- Safari blocks audio without a user gesture. Start playback only from a click handler.
- Listening events: send `start`, then `heartbeat` every 5 seconds while playing, then `end`. On `pagehide` use `navigator.sendBeacon`.
- Use a random `session_id` (uuid) for each listening session.

## PWA
- Service worker handles the `share_target` POST. Store the shared file in IndexedDB, then redirect to `/share`.
- Never cache API responses or protected files in the service worker.

## Tests
- TDD for logic (hooks, parsers, note-name mapping, MusicXML lyric injection, share handler).
- Component tests for forms and role-based rendering.
- Do not test third-party libraries (OpenSheetMusicDisplay). Test our code around them.
