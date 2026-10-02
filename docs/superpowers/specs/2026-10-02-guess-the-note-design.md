# Guess the Note — design spec

Date: 2026-10-02  
Status: approved

## 1. Overview

A self-contained "Guess the Note" game module inside the existing solfeo-exercises app. Children aged 6–9 see 1–4 natural notes on a music staff and tap the correct note names in order. The module adds player profiles (multiple children per parent account), server-authoritative rounds, seasons/stats, XP/levels/trophies, confusion analytics, a built-in avatar catalog, and AI-generated custom avatars.

## 2. Role mapping

| Spec term | Codebase value |
|---|---|
| "admin" | `manager` role (`User.role == 'manager'`) |
| "player account" | `student` role |
| "player profile" | new `Player` model, FK to `users.id` |
| note naming setting | `User.note_naming` — profiles inherit account's value |

## 3. Module layout

### Backend

```
backend/app/game/
  __init__.py
  config.py          # ALL numeric constants (task count, time limits, XP thresholds, etc.)
  models.py          # SQLAlchemy models, same Base as app.models
  services/
    players.py
    rounds.py
    seasons.py
    avatars.py
  api/
    players.py
    rounds.py
    seasons.py
    avatars.py
    admin.py

backend/migrations/versions/0008_game_guess_the_note.py
```

All routers registered in `app/main.py`. Models use the existing `Base` from `app.models` (shared metadata + naming convention).

### Frontend

```
frontend/src/features/game/
  GameTheme.tsx        # child MUI theme (cartoon palette, Fredoka font, 24px radius)
  index.tsx            # route entry, wraps everything in GameTheme
  setup/               # player pick → difficulty → note count
  play/                # staff SVG + note buttons + timer
  result/              # round result screen
  profile/             # player stats, trophies, confusion heatmap
  admin/               # manager-only: player list, season reset, stats drill-down
  staff/               # SVG renderer + pitch→position map
  audio/               # Web Audio synthesis (unlock, mute, play note)
  api/                 # TanStack Query fetch wrappers
```

New localization keys added to existing `frontend/src/i18n/locales/{ru,en,es}.json`.

## 4. Data model

### `players`

```
id            bigint PK
account_id    → users.id  NOT NULL
name          varchar(20) NOT NULL
avatar_animal varchar(20) nullable   -- builtin animal id (config constant)
custom_avatar → custom_avatars.id nullable
xp            integer DEFAULT 0
created_at    timestamptz
archived_at   timestamptz nullable   -- reserved; no archive endpoint required yet
UNIQUE (account_id, name)
```

`level` is computed from `xp` using the threshold array in `config.py` — not stored.

### `seasons`

```
id            bigint PK
player_id     → players.id
number        integer            -- sequential per player, starts at 1
started_at    timestamptz
ended_at      timestamptz nullable
UNIQUE (player_id) WHERE ended_at IS NULL  -- partial index: one active season
```

### `rounds`

```
id            bigint PK
player_id     → players.id
season_id     → seasons.id
difficulty    varchar(6)  CHECK ('easy','medium','hard')
note_count    smallint    CHECK (1,2,3,4)
note_naming   varchar(7)  -- snapshot of User.note_naming at round creation
status        varchar(9)  CHECK ('active','completed','expired')
score         smallint nullable
correct_count smallint nullable
created_at    timestamptz
completed_at  timestamptz nullable
expires_at    timestamptz
INDEX (player_id, season_id, difficulty, note_count)
```

### `task_attempts`

```
id             bigint PK
round_id       → rounds.id
season_id      → seasons.id   -- denormalized for heatmap queries
task_index     smallint (0–6)
clef           varchar(6)  CHECK ('treble','bass')
expected_notes jsonb        -- [{name:"C", octave:4}, ...]
given_notes    jsonb nullable  -- null on timeout
is_correct     boolean
timed_out      boolean
response_ms    integer nullable
issued_at      timestamptz
submitted_at   timestamptz nullable
score          smallint     -- +1 correct, −1 wrong/timeout
UNIQUE (round_id, task_index)
INDEX (season_id, player_id)
```

### `trophies_awarded`

```
id           bigint PK
player_id    → players.id
threshold    integer    -- 20, 100, 200, 500
awarded_at   timestamptz
UNIQUE (player_id, threshold)
```

### `custom_avatars`

```
id           bigint PK
account_id   → users.id
player_id    → players.id
description  text
status       varchar(7)  CHECK ('pending','ready','failed')
base_path    text nullable
happy_path   text nullable
sad_path     text nullable
created_at   timestamptz
completed_at timestamptz nullable
error_code   varchar(50) nullable
```

### `avatar_generation_log`

```
id           bigint PK
account_id   → users.id
flagged      boolean DEFAULT false
billable     boolean DEFAULT true    -- false = our-side error; doesn't count toward daily limit
created_at   timestamptz
INDEX (account_id, created_at)
```

`avatar_catalog` is a config constant (8 fixed animals) — not a DB table.

## 5. Game config (`config.py`)

All numeric constants in one place:

```python
TASKS_PER_ROUND = 7
WIN_THRESHOLD = 5             # correct tasks needed to win
TIME_EASY_S = 13
TIME_MEDIUM_S = 10
TIME_HARD_S = 7
XP_CORRECT_TASK = 1
XP_WIN_BONUS = 5
LEVEL_THRESHOLDS = [0, 30, 80, 150, 250, 400, 600, 850, 1150, 1500]
LEVEL_PREFIXES_RU = ["ути-пути","микро","мини","настоящий","супер",
                      "мега","убер","великий","величайший","божественный"]
TROPHY_THRESHOLDS = [20, 100, 200, 500]
NOTE_RANGE = {
    "treble": [("C",4), ..., ("G",5)],
    "bass":   [("E",2), ..., ("C",4)],
}
ANIMAL_IDS = ["unicorn","dragon","phoenix","griffin",
              "sphinx_cat","kitsune_fox","pegasus","mermaid"]
```

## 6. API endpoints

All under `/api/game/`. CSRF required on mutations. `Member` for player-facing routes; `Manager` for admin routes.

### Players

```
GET  /api/game/players                  own account's players (student) | all (manager)
POST /api/game/players                  manager; body: {name, avatar_animal}
GET  /api/game/players/{id}             profile + current-season stats + trophies
PATCH /api/game/players/{id}            manager; body: {name?, avatar_animal?, custom_avatar_id?}
```

### Round lifecycle (anti-cheat)

```
POST /api/game/rounds
  body: {player_id, difficulty, note_count}
  Server generates all 7 tasks, records issued_at=null.
  Returns: {round_id, task: {index:0, clef, notes:[{name,octave}]}}

POST /api/game/rounds/{id}/submit
  body: {task_index, answers:["До","Ре"]} | {task_index, timed_out:true}
  Server validates timing (issued_at + time_limit + grace_ms), scores, stores attempt.
  Returns: {is_correct, correct_answers, score_delta,
            next_task: {index,clef,notes} | null,
            result: RoundResult | null}
```

`RoundResult` includes: score, correct_count, is_win, xp_gained, level_up (bool),
new_trophy (threshold | null), avg_comparison, practice_hint (kid-friendly string).

Double-tap guard: second submit for same task_index returns the already-stored result idempotently.

### Seasons (manager)

```
GET  /api/game/players/{id}/seasons       list all seasons (read-only)
POST /api/game/players/{id}/seasons/reset  open new season (requires confirmation token)
POST /api/game/seasons/reset-all           reset all players
```

### Avatars

```
GET  /api/game/avatars/catalog            list builtin animal ids + display names
POST /api/game/avatars/generate           start AI job; body: {player_id, description}
GET  /api/game/avatars/{job_id}/status    pending|ready|failed + preview paths
POST /api/game/avatars/{job_id}/use       attach to player
DELETE /api/game/avatars/{job_id}         discard
GET  /api/game/avatars/quota              {used, limit, resets_at}
```

### Stats / confusion

```
GET /api/game/players/{id}/stats        matrix: difficulty × note_count (current season)
GET /api/game/players/{id}/confusion    heatmap 7×7 + top confusions (manager only)
```

## 7. Frontend design

### GameTheme

Child MUI theme wrapping only `/game/*` routes. Does not affect the rest of the app.

- Palette: coral primary, sunflower secondary, mint success
- Border radius: 24px
- Shadows: thick soft drop-shadow ("sticker" feel)
- Font: Fredoka via `@fontsource/fredoka` (Cyrillic-capable); fallback: Nunito, Comic Sans MS, cursive
- Buttons: pill-shaped; 3D "pressed" via box-shadow delta on `:active`; min 64×64px touch target for note buttons

### Screen flow

```
/game                     player selection
/game/setup/:playerId     difficulty → note count
/game/play/:roundId       game (staff + buttons + timer)
/game/result/:roundId     result
/game/profile/:playerId   player profile (stats, trophies, confusion)
/game/admin               manager: player list + season reset
/game/admin/:playerId     manager: player detail + heatmap
```

Avatar (round sticker frame + level badge) is visible on every game screen. Mood swaps are plain `<img src>` changes — no animation required.

### Staff SVG renderer

Pitch → staff position (integer, 0 = bottom line, even = lines, odd = spaces):

```ts
const DIATONIC = { C:0, D:1, E:2, F:3, G:4, A:5, B:6 }
const abs = (name, octave) => octave * 7 + DIATONIC[name]
const CLEF_REF = { treble: abs('E',4), bass: abs('G',2) }  // 30, 18
export const staffPos = (name, octave, clef) => abs(name, octave) - CLEF_REF[clef]
// treble: C4→−2, E4→0, B4→4, F5→8(top line), G5→9
// bass:   E2→−2, G2→0, D3→4, A3→8(top line), C4→10
```

SVG renders: 5 staff lines, clef glyph (inline Bravura SVG path, SIL OFL), note heads + stems, ledger lines only where needed (position < 0 or > 8). Staff background is plain white/cream; cartoon styling lives in the wrapper, not inside the SVG. Responsive via `viewBox`. Unit-tested for every note in both clef ranges.

### Timer

CSS-animated "candy stick" shrinks horizontally driven by `Date.now` delta (not `setInterval`). Full time → teal; last 2 s → warm orange + 🔥 icon (color + icon, never color alone). Tab hidden → Page Visibility API pauses/expires task.

### Note buttons

7 pill buttons (До–Си / C–B), rainbow decorative palette. Answer slots below the staff (N boxes) + backspace. Disabled after N answers entered.

### Web Audio synthesis

No sample files. Frequency: `440 * 2^((midi−69)/12)`. Triangle oscillator, 0.3 s decay envelope, octave nearest clef midpoint. AudioContext unlocked on first user gesture. Mute toggle in localStorage. Fire-and-forget; errors silently swallowed — never blocks input.

### Avatar image resolver

Fallback order:
1. `assets/avatars/{animal}/{stage}_{mood}.png`
2. `assets/avatars/{animal}/{stage}_neutral.png`
3. `assets/avatars/{animal}/01_neutral.png`
4. Generic inline SVG placeholder

Stage is always zero-padded two digits (`01`–`10`). Custom avatars use base/happy/sad paths served from `media_root`.

Placeholder SVGs generated by `scripts/gen_avatar_placeholders.py` (colored circle + animal emoji + mood face + stage badge).

## 8. Avatar AI generation

Follows the OMR worker pattern:

1. `POST /api/game/avatars/generate` writes `custom_avatars` row (`status='pending'`), writes log row, returns `{job_id}`.
2. `worker/generate_avatar.py` polls: `SELECT … FOR UPDATE SKIP LOCKED`.
3. Worker: run description through OpenAI moderation → if flagged, `status='failed'`, `billable=false`. Else: generate base image (DALL-E, `settings.avatar_image_model`), generate happy + sad variants via image edit with base as reference. Save to `media_root/avatars/custom/{job_id}/`. Set `status='ready'`.
4. Client polls `GET /api/game/avatars/{job_id}/status` every 2 s.
5. Preview shown on `ready` → "Use this" / "Discard".

Daily limit: count `avatar_generation_log` rows WHERE `account_id=? AND billable=true AND created_at >= today`. Managers bypass.

Settings additions to `Settings`:

```python
avatar_image_model: str = "dall-e-3"
avatar_gen_daily_limit: int = 3
avatar_gen_grace_ms: int = 500
avatar_round_expire_s: int = 3600
```

OpenAI called via `httpx` (no new dependency), following the `generate_spoken.py` pattern.

## 9. Confusion analytics

Every `task_attempt` stores `expected_notes` + `given_notes`. A confusion is `(expected_name, given_name)` at each position where they differ. Timeouts tracked as `timed_out=true`.

- **Kid-facing result screen**: one friendly hint based on top confusion in the round, e.g. "Потренируем Ре и Фа?" No tables, no counts.
- **Admin/parent player profile**: top-3 confusions ("Ре вместо Фа ×2"), 7×7 heatmap (expected × entered), filterable by clef, "most missed notes" list. Numbers in cells (not only color intensity).

Aggregation in SQL with indexes on `(season_id, player_id)`.

## 10. Tests

### Backend unit tests

| Subject | File |
|---|---|
| Scoring: +1/−1, win threshold, round sum | `tests/game/test_scoring.py` |
| Task generation: range, no immediate repeat, random clef | `tests/game/test_rounds.py` |
| Server-side timeout + grace: late submit → timed_out | `tests/game/test_rounds.py` |
| Idempotent submit (double-tap guard) | `tests/game/test_rounds.py` |
| XP accumulation + level thresholds | `tests/game/test_progression.py` |
| Trophy awarded exactly once per threshold | `tests/game/test_progression.py` |
| Season reset: XP/trophies preserved, new season opened | `tests/game/test_seasons.py` |
| Stats aggregation by difficulty × note_count | `tests/game/test_stats.py` |
| Confusion aggregation | `tests/game/test_stats.py` |
| Daily avatar limit (billable logic) | `tests/game/test_avatars.py` |
| Avatar resolver fallback order + stage naming | `tests/game/test_avatars.py` |
| Role checks: student → 403 on all manager endpoints | `tests/game/test_auth.py` |

### Frontend unit tests

`staff/staffPos.test.ts` — every note in both clef ranges, ledger-line boundaries.

### Integration test

One full round via API: 5 correct + 1 wrong + 1 timeout → assert score=4, correct_count=5, is_win=true, xp_delta=10, no trophy (below threshold).

OpenAI mocked with `respx` in all tests.

## 11. What remains for the owner to supply

- Real avatar PNG art (`assets/avatars/{animal}/{stage}_{mood}.png`)
- Actual Bravura clef SVG paths (free, SIL OFL — download from Bravura repo)
- `.env` values: `API_AVATAR_IMAGE_MODEL`, `API_OPENAI_API_KEY` (already present)
- Decision: add `generate_avatar` worker to `docker-compose.yml` alongside existing OMR worker

## 12. Assumptions

- `opensheetmusicdisplay` is NOT used for this module (custom SVG per owner's decision)
- Avatar stage images for built-in animals use zero-padded two-digit stage (`01`–`10`)
- Note naming for a round is snapshotted from `User.note_naming` at round creation; mid-round setting changes don't affect an active round
- `archived_at` field exists on `players` but no archive/unarchive endpoint is built (spec §10)
- Placeholder SVGs are auto-generated; real PNGs are drop-in replacements
- The confusion heatmap is parent/admin-only; the child result screen shows only the friendly hint
