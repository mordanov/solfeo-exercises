# Claude Code prompt: "Guess the Note" game module

Paste everything below the line into Claude Code.

---

You are a senior full-stack engineer. Implement a self-contained "Guess the Note" game module inside an EXISTING service.

# 0. Working rules
- Stack: React + Material UI (frontend), Python 3.12 (backend), PostgreSQL. First explore the repo: backend framework, ORM and migration tool, auth and roles, routing, theming, i18n, settings mechanism, file storage, and the existing OpenAI integration. Reuse them and follow existing conventions. Do not rewrite unrelated code.
- Before coding, output a short plan and list your assumptions. Then implement in phases: data model → backend → game UI → admin → progression/trophies → avatar generation → tests.
- Roles already exist in the app: use them (admin, player). Never add your own role system. Enforce permissions on the server, not only in the UI.
- Default UI language is Russian. Put all UI strings in the project's i18n layer (or one strings file) so other languages can be added.
- Mobile-first: big touch targets, usable one-handed.

# 0.1 Audience and visual style
The game is for children aged 6-9. The whole player-facing UI must be VERY cartoonish, playful and friendly.

Look and feel:
- Build a custom MUI theme for the game module: large border radius (24px+), thick soft outlines, "sticker" cards with a playful drop shadow, bright but harmonious candy palette, decorative background (clouds, stars, hills, sparkles) as lightweight inline SVG or CSS. No stock-corporate look.
- Rounded kid-friendly font (e.g. Fredoka, Baloo 2 or Nunito) with full Cyrillic support. Bundle it locally (@fontsource) rather than loading from a CDN, and keep a safe fallback stack.
- Big, chunky, pill-shaped buttons with a "pressed" 3D effect. Minimum touch target 64x64 px for game buttons. Spacing generous, never cramped.
- Note buttons: 7 buttons in a rainbow-like palette, each with a big label. Colors are decoration only: never color the notes on the staff and never let color give away the answer.
- The staff itself must stay maximally readable: high contrast, large note heads, clean lines, on a plain light "paper" panel. Cartoon style must never reduce readability of the staff.
- The player's avatar is a visible mascot on every game screen (start, task, feedback, result), shown in a round sticker frame with the level badge.

Language and UX for young readers:
- Very short texts, simple words, one idea per screen. Prefer icons + a few words over sentences. Large numerals for the timer and score.
- Friendly, encouraging tone. Wrong answers and losses are never shaming: use gentle messages like "Почти! Давай ещё раз!". Celebrate wins and level-ups with confetti-like static/CSS decorations and a big happy message.
- Timer bar looks like a fun object (e.g. a candy stick or a fuse) and turns warm-colored with an icon in the last 2 seconds; keep it calm, not scary.
- Task feedback uses big friendly icons (star/check, "oops" cloud) plus text.
- Animation is not required. Light CSS transitions (button press, bar shrinking, screen change) are fine; respect prefers-reduced-motion.
- Child safety: no ads, no external links, no chat, no external trackers, no dark patterns (no streak-loss guilt, no pressure mechanics). The AI-avatar description field is the only free-text input for kids: keep moderation strict and error messages friendly.
- Admin and parent-facing screens (player management, statistics reset, seasons, heatmap, detailed stats) may be cleaner and more neutral, but must still use the same theme tokens so the app feels consistent.
- Keep all text in the i18n layer; keep the vocabulary appropriate for 6-9 year olds.

# 1. Domain concepts
- Account = existing app user. Players are PROFILES inside one account (e.g. several children of one parent), not separate logins. Each profile has: id, account_id, name (1–20 chars, unique within account), avatar_id, xp, created_at, archived_at. Players are NEVER deleted (no delete endpoint or UI). Admins may create and edit players (name, avatar). Players/accounts can only see and play with their own account's profiles; admins can see all.
- Round = 7 tasks played one after another by one player.

# 2. Game setup (start screen)
The player picks, in this order:
1. Player profile (card with avatar, name, level prefix, quick stats).
2. Time difficulty: Easy = 13 s, Medium = 10 s, Hard = 7 s per task.
3. Number of notes per task: 1, 2, 3, or 4 (this replaces the old "levels").
The clef is NOT selectable: every task gets a random clef (treble or bass), independently.
All numbers (times, note counts, task count 7, win threshold, ranges) live in one config module.

# 3. Gameplay rules
- A round has 7 tasks. Each task shows N notes on a staff (clef drawn at left) and the player taps note-name buttons in the left-to-right order the notes are written.
- Note buttons: 7 large buttons. Slots under the staff show entered answers; a "backspace" button removes the last entered note.
- Naming: two naming systems, selected by an existing/new app setting (per account, fallback to global): (a) solfège: До Ре Ми Фа Соль Ля Си, (b) letters: C D E F G A B. The setting must affect buttons, feedback, error analysis, and stats screens.
- Notes are natural only (no sharps/flats), rendered range configurable. Defaults: treble from C4 to G5, bass from E2 to C4 (allow at most 2 ledger lines). Pick random notes; never repeat the exact same task twice in a row.
- Timer: numeric countdown + shrinking progress bar; bar changes color (and shows an icon, not only color) in the last 2 seconds.
- Scoring per task: all N notes correct and in order = +1; wrong answer = −1; timeout = −1. A wrong answer is judged once N notes are entered (no partial credit).
- Round score = sum of task scores (−7…+7). Average score is per ROUND (the 7-task sum), not per task.
- WIN = at least 5 correct tasks out of 7 (config constant; note this equals score ≥ 3).
- After each task show ~1 s feedback (correct/incorrect + the right answer, with icon and text, not only color), then the next task.
- Sound: when the player taps a note button, play that note. Use Web Audio API synthesis (no sample files), real pitches. Register: use the octave nearest to the middle of the current clef's range. Unlock the AudioContext on the first user gesture; provide a mute toggle remembered per device; sound must never block input.
- Avatar mood: the avatar shown during the game uses the "happy" image after a correct answer or win, "sad" after wrong/timeout/loss, "neutral" otherwise. No animations required, just image swapping.
- Result screen: keep it short and visual: big score, stars, avatar reaction (happy/sad image), WIN/LOSE in one friendly line. Show: round score, correct count, comparison with the player's average for the same difficulty × note-count combination, XP gained (and level-up notice if any), newly earned trophy (if any), and a simple child-friendly practice hint instead of raw statistics (see §8). Buttons: "Play again" and "Change player".

# 4. Server-authoritative rounds (anti-cheat, timing robustness)
- POST /rounds creates a round and its 7 tasks server-side. The client receives only what it needs to render (clef, notes) for the current task; correct answers are NOT sent ahead of time.
- Each task: server stores issued_at; client submits the answer; the server validates correctness and time (time limit + small configurable grace for network latency) and computes the score. Late or missing answers = timeout.
- Client countdown uses timestamps (performance.now / Date.now delta), never interval counting; a hidden/backgrounded tab must not grant extra time. Guard against double taps and the race at the timeout boundary (one result per task, idempotent submit).
- Abandoned rounds (never finished) are not counted in statistics; expire them after a configurable period.

# 5. Seasons (versioned statistics)
- Statistics are versioned by season. Each player has exactly one active season at a time. A season has: id, player_id, number, started_at, ended_at (null while active).
- Admin "reset statistics" = close the player's active season and open a new one (for one player or for all players). Nothing is deleted; confirmation dialog required.
- Every round and task attempt references its season. Provide an admin/player view to browse past seasons (read-only).
- Statistics per player per season: rounds played, wins, win rate, average round score. Always break down by difficulty (Easy/Medium/Hard) AND by note count (1–4), including the combined matrix difficulty × note count. Show them in the profile and a compact version on the player selection screen.
- Trophies and XP/level are all-time and independent of seasons (a reset never removes them).

# 6. Progression (10 levels) and trophies
- XP: +1 per correct task, +5 bonus for a winning round. Errors never subtract XP. No difficulty multiplier. Level never decreases.
- Level thresholds (cumulative XP), configurable: 0, 30, 80, 150, 250, 400, 600, 850, 1150, 1500.
- Level prefixes for the avatar name, in order (Russian UI strings): ути-пути, микро, мини, настоящий, супер, мега, убер, великий, величайший, божественный. Display as e.g. "Супер Единорог" next to the avatar, with a level badge and XP progress bar to the next level.
- Trophies for completed (finished) rounds, all-time: 20, 100, 200, 500. Award each exactly once per player, record awarded_at, show a trophy shelf in the profile, and show a celebratory message when earned.

# 7. Avatars
Built-in avatars:
- A fixed catalog of 8 magical animals in a catalog table/config. Animal ids (lowercase, snake_case): unicorn, dragon, phoenix, griffin, sphinx_cat, kitsune_fox, pegasus, mermaid.
- Each animal needs images per level stage (10) × mood (neutral, happy, sad). The user will generate real art later (see the separate avatar-generation prompt), so use THIS exact convention:
  - Path: assets/avatars/{animal_id}/{stage}_{mood}.png (svg also accepted by the resolver)
  - stage is ALWAYS zero-padded two digits: 01..10 (01 = ути-пути … 10 = божественный)
  - mood is one of: neutral | happy | sad
  - Example: assets/avatars/dragon/10_sad.png
- Implement a resolver with fallback order: exact stage+mood → same stage neutral → 01 neutral of the animal → generic placeholder. Never show a broken image.
- Create generated PLACEHOLDER SVGs for all 8 × 10 × 3 combinations (simple, consistent style: colored circle with the animal emoji/initial, a different face for each mood, stage number badge) so the app works end-to-end. Generate them with a script (include the script) so they are easy to regenerate. Real PNGs dropped into the same folders must take priority over placeholders.
- Document in a README how to drop in real images and the naming convention.
- The level prefix and a stage frame/border color are drawn by the UI, so a missing stage image falls back gracefully.

AI-generated avatars (OpenAI API; reuse the app's existing OpenAI client/config/keys; the image model name is a config value):
- A player (via their account) can describe a magical animal in free text and generate a custom avatar. Limit: 3 generations per day per account (configurable; counted per calendar day in the app's timezone; failed generations caused by our side do not count). Admins: unlimited.
- Always wrap the user description in a server-side system template: cute, child-friendly, single magical creature, consistent flat cartoon illustration style, plain/transparent background, no text, no real people, no brands/characters from existing franchises. Never pass the raw user text alone.
- Moderation is mandatory: run the description through OpenAI moderation before generation; reject with a friendly message if flagged; also screen the generated image if the moderation API supports it. Log rejections.
- Output: generate ONE base image first, then generate "happy" and "sad" variants of the same creature using the base image as reference (image edit) to keep it consistent. Custom avatars do NOT get 10 stage images: the UI applies the level prefix, level badge, and stage frame around the base/mood image.
- Generation is asynchronous: start job → poll status → preview → "Use this avatar" or "Discard". Store files in the project's existing storage. Custom avatars belong to the account's profiles only (not public).
- Handle API errors, timeouts, and rate limits gracefully; show the remaining daily quota in the UI with kid-friendly wording.
- Do not hardcode secrets; read config from the existing mechanism.

# 8. Mistake analysis
- Persist every task attempt: round_id, season_id, task_index, clef, expected notes (with octaves), given notes, per-position correctness, is_correct, timed_out, response_time_ms.
- A "confusion" = (expected note name, entered note name) at a position. Timeouts are tracked separately as "missed".
- Child-facing result screen: show only a simple, friendly practice hint based on the round's top confusion, e.g. "Потренируем Ре и Фа?" (respect the naming setting). No tables, no counts, no shaming.
- Parent/admin-facing player profile (not shown in the kid's game flow): top-3 confusions of the round phrased like "Ре вместо Фа ×2", confusion heatmap (7×7 matrix, expected × entered) for the current season, filterable by clef, a "most missed notes" list, and an analytic hint such as "Often mixes up Re and Fa — practice these". Aggregate in SQL with proper indexes.
- Make the heatmap accessible (numbers in cells, not only color intensity).

# 9. Staff rendering
- Draw the staff yourself with SVG (5 lines, treble and bass clef glyphs, note heads, stems, ledger lines). Use a lightweight open-licensed clef glyph path or an inline SVG path; avoid heavy music-notation libraries unless one already exists in the repo.
- Responsive: stays readable at 4 notes on a 360 px wide phone. Correct note positions for both clefs (unit-test the pitch → staff-position mapping).

# 10. Admin features
- Admin section (hidden from non-admins; admin endpoints return 403 for others): list all accounts' players; create/edit player (name, avatar); archive/unarchive is NOT required, deletion is forbidden.
- Reset statistics: per player and for all players → creates new season(s), with confirmation.
- View any player's stats, seasons, trophies, confusion analysis.

# 11. API/Data notes
- Provide DB migrations with the project's migration tool. Suggested tables: players, seasons, rounds, task_attempts, trophies_awarded, avatar_catalog, custom_avatars, avatar_generation_log. Add sensible constraints and indexes.
- Validate inputs on client and server, return clear error messages, document endpoints (OpenAPI if the framework supports it).

# 12. Accessibility & quality
- aria-labels on all buttons, sufficient contrast, feedback never conveyed by color alone, keyboard support on desktop (keys for notes optional but nice).
- Handle loading/error/empty states in every screen.

# 13. Tests
Unit tests: scoring, win determination, task generation (ranges, no immediate repeats, random clef), pitch→staff-position mapping, XP/level calculation and thresholds, trophy awarding (exactly once), season reset (data preserved, new season opened, trophies/XP untouched), stats aggregation by difficulty × note count, confusion aggregation, avatar daily-limit logic, avatar resolver fallback order and 01..10 naming, role checks (player gets 403 on admin endpoints), server-side timeout/grace handling.
Integration/e2e: one full round with a correct answer, a wrong answer, and a timeout, ending in a result screen with correct score and XP. Mock OpenAI in tests.

# 14. Final output
List created/changed files, how to run migrations/app/tests, the assumptions you made, and anything left for me to decide or to replace (placeholder avatars, real clef glyphs, image model name).
