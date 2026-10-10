# Solfège Trainer: product brief

This file is the full requirement set. When it conflicts with a decision in DECISIONS.md, DECISIONS.md wins.

## Purpose
A web app for solfège homework. An exercise = sheet-music image and/or audio file + text description.
A child looks at the notes and listens to the audio.

## Roles
- manager: manages exercises (add/edit/delete/reorder), manages users (create, reset password, deactivate), reads the listening journal.
- student: listens to exercises, changes own settings, and plays Guess the Note with owned player profiles.
- player: plays Guess the Note with an owned profile and changes account settings and appearance.
  Players cannot access exercises, protected exercise files, scores, the listening journal, or manager functions.
  Managers create their game profiles, as for students.

## Stack (fixed, do not change)
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x (typed), Alembic, PostgreSQL, pytest, ruff, mypy (strict).
- Frontend: React + TypeScript + Vite, Material UI v9, Community DataGrid v9, react-i18next, Vitest + Testing Library, ESLint, Prettier.
- Infra: nginx (reverse proxy, TLS, serves protected files via X-Accel-Redirect), Docker Compose.
- Workers: OMR worker container (Audiveris, Java) + a Postgres-based job queue (SELECT ... FOR UPDATE SKIP LOCKED). No Redis.
- CI/CD: GitHub Actions. CI = pre-commit (ruff, ruff-format, mypy, eslint, prettier, tsc) + backend unit tests + frontend unit tests.
  CD = build Docker images -> push to GHCR -> deploy to VPS via SSH (docker compose pull/up, alembic upgrade, healthcheck, rollback to previous tag on failure).
- Target browsers: Chrome 117+ and Safari 17+ only. Backups are OUT OF SCOPE.

## Configuration
- ALL settings live in .env (pydantic-settings). Keep .env.example complete and documented. No secrets in git.
- Emergency manager: EMERGENCY_MANAGER_USERNAME / EMERGENCY_MANAGER_PASSWORD (plus first/last name).
  On EVERY backend start:
  - If both variables are set: create or update this user (role=manager, active, password reset to the .env value, flag is_emergency=true).
  - If they are not set: the user with is_emergency=true is deactivated (cannot log in).
  This is the first-user mechanism AND the disaster-recovery mechanism.

## Users and auth
- User: username (unique login), first_name, last_name, role (manager|student|player), password, is_active, is_emergency, settings.
- No email. Simple username+password. Hash passwords with a standard library scheme (bcrypt via passlib, or hashlib.scrypt). Never store plaintext. No Argon2.
- Session: httpOnly, Secure, SameSite=Lax cookie with a server-side session token, sliding expiry, long lifetime (env-configurable, default 90 days).
  The web application retains its session on mobile browsers.
- Login rate limit (per username+IP) in backend, plus nginx limit_req on /api/auth/login.
- Manager can create users and reset passwords. Optional flag "must change password on next login".
- Per-user settings (available to every role, stored on server): ui_language (ru|en|es), note_naming (letters|solfege). Defaults: env DEFAULT_LANGUAGE, note_naming=letters (C-D-E).
- Appearance settings also persist per account: independent light and dark color schemes, interface font, and base font size.
- Schemes: classic, forest, warm, plum. Fonts: Roboto, system, serif. Sizes: 16, 18, 20 px.
- Each scheme controls button backgrounds and text, page and panel backgrounds, text, links, borders, and interactive states.
- Preserve semantic error and success colors; maintain readable contrast in every scheme.
- Show a live example panel before saving; restore the standard appearance without changing language or note naming.
- Keep light/dark mode local to each browser. Appearance changes do not reset forms, restart playback, or change score engraving.

## i18n
- Every UI string goes through react-i18next. Ship ru, en, es from day one. A test must fail if any key is missing in any language.
- Backend returns stable error codes (not translated text); frontend translates them.
- Before login, use the first supported browser language, including regional variants; use English when none matches.
- Saved account language takes priority after login.

## Guess the Note

- Use natural pitches C4–A5 in the treble clef and E2–C4 in the bass clef.
- Show 7 answer buttons for C through B, without octave labels or octave grading.
- Follow the account's letters or solfege setting and interface language for buttons and revealed answers.
- Play the same sampled piano pitch from an answer button and the corresponding sound hint.
- Use `soundfont-player` with one reduced, licensed Salamander Grand Piano V3 asset and 4 real velocity layers.
- Do not load a complete SF2 or request an external soundfont in the browser.
- Load the piano before starting the scored round; report loading failures and permit retry.
- Offer independent setup switches for the sound hint and the correct answer.
- Enable the hint and disable answer revelation by default.
- Show the correct answer to the right of the staff during feedback when enabled.
- Show only the selected 13, 10, or 7 s limit in the difficulty hint.
- Show +1 point beside each disabled switch and 0 points beside each enabled switch.
- Add these points once per completed round, including losing rounds; preserve XP and the winning threshold.
- Keep the staff frame fixed across clefs and note counts.
- Show enabled answer feedback to the right of the centered playback control, never beside the staff.
- Limit new profiles to one per active, non-emergency account.
- Exclude occupied accounts and the emergency manager from profile creation.
- Show the all-assigned popup when no eligible accounts remain.
- Preserve existing profiles, progress, previous rounds, and manager-only creation.
- Make each player's statistics accessible from the selection screen, with compact rounds and win rate.
- Show rounds, wins, win rate, and average score by season, difficulty, note count, and the combined matrix.
- Show actual all-time XP, avatar level, and earned trophies.
- Permit students to read only their own profiles and past seasons.
- Give managers visible access to all profiles, season history, and mistake analysis.
- Show localized confusion counts, latest-round confusions, an accessible heatmap, and missed notes with a clef filter.
- Let only managers reset statistics for one player or all players, after explicit confirmation.
- Reset statistics by opening a new season; preserve history, XP, levels, trophies, and saved avatars.
- Exclude unfinished and expired rounds from all statistics and mistake analysis.
- Floor the final round score at 0 after adding the assistance bonus; retain raw -1 scores for incorrect answers.
- Serialize XP updates per player and return durable identical replies for repeated submissions.
- Issue the first question and subsequent questions with authoritative timestamps and deadlines.
- Account for the difference between server and client clocks when showing time remaining.
- Configure feedback through `GAME_FEEDBACK_MS`, default `900`.
- Return structured practice hints; translate note names and messages in the selected interface language.
- Compare the result with previous completed rounds at the same difficulty and note count across seasons.
- Omit the previous average when no matching completed round exists.

### Lifetime game prizes

- Provide 20 prizes, each awarded once per profile across completed rounds from all seasons.
- Show the collection after each round, not during round preparation.
- Keep the collection available in player statistics.
- Retain prizes through statistics resets; do not add XP for prizes.
- Preserve the existing trophies for 20, 100, 200, and 500 completed rounds.
- Use `GAME_TIMEZONE`, default `UTC`, for calendar-day conditions and generation quotas.
- Count correctly matched individual positions from expected and entered arrays, including partially correct answers.
- Use encouraging messages; never warn about losing a streak or punish a break.

| Code | Condition |
|---|---|
| `first_round` | Complete 1 round |
| `first_win` | Win with at least 5 correct answers |
| `perfect_round` | Answer all 7 questions correctly in 1 round |
| `correct_streak_10` | Answer 10 questions correctly in succession across completed rounds |
| `notes_100` | Match 100 individual note positions in completed rounds |
| `note_rainbow` | Match each of the 7 note names at least 10 times |
| `treble_25` | Answer 25 treble-clef questions correctly |
| `bass_25` | Answer 25 bass-clef questions correctly |
| `both_clefs` | Win 1 round with correct answers in both clefs |
| `duet` | Complete a perfect round with 2 notes per question |
| `trio` | Complete a perfect round with 3 notes per question |
| `quartet` | Complete a perfect round with 4 notes per question |
| `all_difficulties` | Win on all 3 difficulties |
| `independent_win` | Win with both assistance options disabled |
| `days_streak_3` | Complete rounds on 3 consecutive calendar days |
| `days_7` | Complete rounds on 7 different calendar days |
| `level_2` | Reach level 2 at 30 XP |
| `level_5` | Reach level 5 at 250 XP |
| `wins_10` | Win 10 rounds |
| `welcome_back` | Complete a round after a gap of at least 7 calendar days |

## Game avatar artwork

- Provide 11 characters: unicorn, dragon, phoenix, griffin, sphinx cat, fox, pegasus, mermaid, lion, panda, and rhino.
- Show the character's XP-based appearance through 10 avatar levels.
- Use transparent owner-supplied artwork and preserve the original sheets.
- Permit repeated source appearances where sheets contain fewer than 10 groups.
- Show happy for 5–7 correct answers, neutral for 3–4, and sad for 0–2.
- Use the question-mark choice for explicit custom generation with quota, manager review, approved preview, selection, and discard.
- Generate custom artwork through 1 image request for a sheet with 10 levels and 3 emotions.
- Show 10 distinct growth stages while keeping cell size and camera framing consistent.
- Apply neutral, happy, and sad expressions to every level without changing its outfit.
- Save the original sheet, all 30 frames, and a hash manifest in persistent private storage.
- Show generation phases, actual saved-image counts, and an explicitly approximate remaining time.
- Permit reopening pending jobs and reusing saved avatars without another paid image request.
- Make every ready approved custom avatar available to every player profile for preview and selection.
- Keep pending and rejected avatars private to their owner and managers.
- Let users delete saved custom avatars they can manage; never allow deletion of built-in avatars.
- Prevent deletion while another player profile uses the avatar.
- Keep legacy 3-emotion avatars available without automatic regeneration.
- Reject incomplete sheets explicitly; never repeat a paid image request automatically after interruption.
- Preserve custom selection across reloads and serve generated images only after an authentication check.
- Keep built-in selection available when the paid generation service is not configured.
- Automatically moderate both the description and generated image before placing the result in the manager queue.
- Let managers inspect all 30 frames and approve or reject the result.
- Deny student access to unapproved generated images, including direct protected-file requests.
- Show the packaged wordless hourglass while approval is pending.
- Activate the waiting avatar after approval without another student action.
- Preserve a later explicit built-in choice instead of replacing it when an older pending avatar receives approval.
- Show the question-mark artwork after rejection.
- Preserve existing ready avatars as approved during migration without regeneration.
- Preserve the owner's original artwork outside the frontend; package the new wordless icon as `under_moderation.png`.

## Mobile installation
- Provide a favicon, dedicated iPad icons, and localized application manifests.
- Offer installation on mobile devices, using the native browser prompt when available.
- Explain Safari Share and Add to Home Screen when native installation is unavailable.
- Require a network connection; do not cache protected files or introduce a share target.
- Show service status only on the Settings page.

## Exercises
- Fields: id, title, description (text), category/level (optional string), position (integer, manager can reorder), image (optional), audio (optional), score (optional, see OMR), deleted_at (soft delete).
- Validation: at least one of image or audio is required.
- Soft delete only. The journal must keep working for deleted exercises.
- Student progress: per-student "next exercise" pointer for sequential mode. Random mode never repeats the immediately previous exercise (if more than one exists).

## Files
- Stored on a Docker volume. Never served directly. nginx internal location + X-Accel-Redirect after backend auth check. Range requests must work (audio seeking in Safari).
- Upload checks: size limits from .env, MIME check by magic bytes (not by extension or client header), allowed types only.
- Audio: accept anything ffmpeg can read (WhatsApp/Telegram .opus/.ogg/.m4a/.mp3/.wav/.aac). Always convert to AAC in an MP4 container (.m4a, audio/mp4). Keep only the converted file. Store duration in seconds.
- Images: png/jpeg/webp. Keep the ORIGINAL image always (needed for OMR review and as fallback).

## Listening journal
- One row per listening session: id, user_id, exercise_id, session_id (uuid from client), started_at, last_heartbeat_at, ended_at (nullable), max_position_sec, audio_duration_sec, completed (bool).
- Client sends: start, heartbeat every 5 s while playing, end. Also navigator.sendBeacon on pagehide.
- completed = max_position_sec >= 90% of duration OR the "ended" event. A closed tab must still leave a valid row.
- Only managers can read the journal (filter by student, exercise, date; pagination).

## OMR (part of MVP)
- On image upload, enqueue an OMR job. Worker runs Audiveris in batch mode -> MusicXML. Engine sits behind a Python interface (OmrEngine) so it can be replaced (for example by oemer).
- Score status: none | pending | processing | needs_review | approved | rejected | failed.
- Manager review shows the rendered score without a duplicate original image; actions Approve / Reject / Re-run remain.
- The exercise preview retains the original image for comparison.
- Students always see the original image when available, including after recognition approval.
- Students also see the rendered score when available and approved; unapproved results remain hidden.
- Rendering: OpenSheetMusicDisplay in the browser.
- Toggle "show note names" on the staff: client-side, inject <lyric> elements into the MusicXML before rendering. Naming from user setting (letters: C D E F G A B; solfege: do re mi fa sol la si; localized).
- Assumptions: printed, monophonic, single-staff exercises. Complex scores may fail; the fallback (image) covers this.

### Photo quality requirements
A low-quality photo is the main cause of OMR errors. Follow these rules before upload:
- Frame one exercise only. Two staff systems in one photo can look like a second movement to the engine.
- Keep the page flat. Avoid page curl and camera angle. A curved or tilted staff often fails staff detection.
- Use even, direct light. Avoid shadows and glare. Low contrast between ink and paper hides the staff lines.
- Take the photo in focus. Keep noteheads separate. A blurry or noisy photo can look like extra chords.
- Check every note, rest, and measure before approval, even for a clear photo. The engine can still misread notes.
- Reject a score with a wrong note, a missing measure, or an extra chord. Reshoot the image instead.
- The spoken notes feature also refuses a score with these errors. It reports code `SPOKEN_UNSUPPORTED_SCORE`.

## Spoken notes
- Not singing. Notes are SPOKEN (do-re-mi or C-D-E per user setting and UI language).
- MusicXML durations determine note timing; the preferred tempo is 72 BPM.
- Automatically reduce tempo when short notes require more speech time; preserve complete words and bounded playback rates.
- Remember adjusted tempo in this browser per account, exercise, score version, language, and naming choice.
- Implementation: pre-generated syllable clips (script calls OpenAI TTS once, output committed to frontend/public/solfege/<lang>/<naming>/), played with Web Audio API. Fit each note to its duration: play the word at its natural pitch (rate 1) and fill the rest with silence; speed up only when the word does not fit, up to a bounded maximum rate. Rests = silence. Sharps/flats = extra suffix clip.
- Available only when score status = approved.
- When an exercise has no recorded audio, the student sees the spoken notes controls instead of an audio control.

## Telegram audio import

The owner replaces PWA audio sharing with a Telegram bot on 2026-09-29.
The web application remains the interface for exercises, users, listening, and the journal.
Audio import does not require an Android share target, IndexedDB share hand-off, or application installation.
Optional online installation returns separately on 2026-10-02.

- A manager sends or forwards an audio attachment to the bot in a private Telegram chat.
- Accept `audio`, `voice`, and audio sent as `document`; text or a link alone is not an audio file.
- Authorize the Telegram sender against an active manager before accepting an import.
- Students and unknown senders cannot create exercises or attach files through the bot.
- Reuse the product file pipeline: size limits, magic-byte checks, AAC `.m4a` conversion, duration, and protected storage.
- Preserve the manager's choice: create an exercise or attach audio to an existing exercise, with title and description.
- Confirm completion only after persistence; retries must not duplicate imported files or exercises.
- Keep tokens and configuration in `.env`; do not expose tokens or received media in logs or public URLs.
- Document the hosted Telegram API download limit and reject oversized attachments explicitly.
- For WhatsApp audio, transfer the actual file into Telegram or save it before attaching it to the bot.
- Select the manager-account linking method and import interaction during PHASE 4 planning.

The risk prototype's numeric sender allowlist is not a replacement for product role checks.
The bot does not replace website login or grant manager access by Telegram username.
The failed PWA prototype remains historical evidence, not an acceptance requirement for the replacement flow.
