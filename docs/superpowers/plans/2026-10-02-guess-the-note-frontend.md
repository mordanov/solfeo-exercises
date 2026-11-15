# Guess the Note — Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the player-facing and admin-facing React UI for the "Guess the Note" game — setup, play, result, profile, and admin screens — inside the existing app without touching unrelated code.

**Architecture:** A new `frontend/src/features/game/` package with its own MUI child theme (Fredoka font, 24px radius, candy palette). No React Router — routes are handled by extending the existing `App.tsx` `knownPath` regex and the `AuthArea.tsx` ternary chain. Staff rendered as custom SVG (no music library). Web Audio API synthesis with triangle oscillator. All game API calls wrapped in TanStack Query hooks. All UI strings in `i18n/locales/{ru,en,es}.json`.

**Tech Stack:** React 19 · MUI v9 · TanStack Query v5 · react-i18next v16 · `@fontsource/fredoka` (to be installed) · Web Audio API · Vitest v4

**Spec:** `docs/superpowers/specs/2026-10-02-guess-the-note-design.md`

## Global Constraints

- `@fontsource/fredoka` must be added to `frontend/package.json` — not loaded from CDN.
- No React Router. Routing via `window.location.pathname` as in the rest of the app.
- `GameTheme` wraps only `/game/*` subtree — zero impact on other routes.
- Staff SVG: custom, no opensheetmusicdisplay or any music library.
- Web Audio: triangle oscillator, no sample files, fire-and-forget, errors silently swallowed.
- Note buttons: rainbow palette is decoration only — never color the notes on the staff.
- All UI strings in `i18n/locales/{ru,en,es}.json` under a `game.*` namespace.
- Touch targets on note buttons: minimum 64×64 px.
- `prefers-reduced-motion`: CSS transitions optional, but must not run when media query matches.
- Timer driven by `Date.now` delta — NOT `setInterval`.

## Review Focus

- `staffPos` formula: middle-C (C4) is `staffPos("C",4,"treble") = −2` (below staff) and `staffPos("C",4,"bass") = 10` (above staff). Off-by-one in either direction shifts every note. Unit-test every note in both clef ranges.
- Double-tap on note submit: two rapid taps before the server responds must not send two submit requests — disable the submit button immediately on first tap and re-enable only on server response.
- AudioContext unlock: `new AudioContext()` before a user gesture throws on Safari/Chrome. Create it inside the first user-gesture handler (`onClick`), not at module load time.
- Tab-hidden timing: `Page Visibility API` pause — when the tab is hidden, the timer must freeze so the task isn't penalized for browser backgrounding.
- `knownPath` regex in `App.tsx`: failing to add `/game` paths causes the app to show a 404 for all game routes. Add `/game` prefix to the regex in Task 1 before any game routes are rendered.

---

### Task 1: Install Fredoka + GameTheme + routing scaffold

**Files:**
- Modify: `frontend/package.json` — add `@fontsource/fredoka`
- Create: `frontend/src/features/game/GameTheme.tsx`
- Create: `frontend/src/features/game/index.tsx`
- Modify: `frontend/src/App.tsx` — extend `knownPath` regex
- Modify: `frontend/src/features/auth/AuthArea.tsx` — add game area to routing chain

**Interfaces:**
- Produces: `<GameTheme>` wrapping component; `<GameArea>` placeholder rendered for `/game*` paths.

- [ ] **Step 1: Install `@fontsource/fredoka`**

```bash
cd frontend && npm install @fontsource/fredoka
```
Expected: package appears in `node_modules/@fontsource/fredoka`.

- [ ] **Step 2: Create `frontend/src/features/game/GameTheme.tsx`**

```tsx
import "@fontsource/fredoka/400.css";
import "@fontsource/fredoka/600.css";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import type { ReactNode } from "react";

const gameTheme = createTheme({
  palette: {
    primary: { main: "#FF6B6B" },     // coral
    secondary: { main: "#FFD93D" },   // sunflower
    success: { main: "#6BCB77" },     // mint
    background: { default: "#FFF9F0", paper: "#FFFFFF" },
  },
  shape: { borderRadius: 24 },
  typography: {
    fontFamily: "'Fredoka', 'Nunito', 'Comic Sans MS', cursive",
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          fontWeight: 600,
          textTransform: "none",
          boxShadow: "0 4px 0 rgba(0,0,0,0.18)",
          "&:active": { boxShadow: "0 1px 0 rgba(0,0,0,0.18)", transform: "translateY(3px)" },
          "@media (prefers-reduced-motion: reduce)": { transition: "none", transform: "none" },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: { boxShadow: "0 6px 0 rgba(0,0,0,0.12)", borderRadius: 24 },
      },
    },
  },
});

export default function GameTheme({ children }: { children: ReactNode }) {
  return <ThemeProvider theme={gameTheme}>{children}</ThemeProvider>;
}
```

- [ ] **Step 3: Create `frontend/src/features/game/index.tsx`** (placeholder — screens added in later tasks)

```tsx
import GameTheme from "./GameTheme";

export default function GameArea() {
  return (
    <GameTheme>
      <div style={{ padding: 24, fontFamily: "Fredoka, sans-serif" }}>
        🎵 Game area (coming soon)
      </div>
    </GameTheme>
  );
}
```

- [ ] **Step 4: Extend `knownPath` in `frontend/src/App.tsx`**

Find the `knownPath` regex (around line 40–44):

```ts
const knownPath =
  window.location.pathname === "/" ||
  /^\/(login|settings|manager\/users|manager\/exercises|manager\/journal|manager\/telegram|student)\/?$/.test(
    window.location.pathname,
  );
```

Replace with:

```ts
const knownPath =
  window.location.pathname === "/" ||
  /^\/(login|settings|manager\/users|manager\/exercises|manager\/journal|manager\/telegram|student|game(\/.*)?)\/?$/.test(
    window.location.pathname,
  );
```

- [ ] **Step 5: Add game area branch in `frontend/src/features/auth/AuthArea.tsx`**

Find the path-switching ternary chain (around line 275). It checks `path` against known route values. Add before the final fallback:

```tsx
: path.startsWith("/game")
? <GameArea />
```

And add the import at the top:
```tsx
import GameArea from "../game/index";
```

- [ ] **Step 6: Start dev server and verify `/game` loads without 404**

```bash
cd frontend && npm run dev
```
Open `http://localhost:5173/game` — should see "🎵 Game area (coming soon)", not a 404 page.

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/src/features/game/GameTheme.tsx frontend/src/features/game/index.tsx frontend/src/App.tsx frontend/src/features/auth/AuthArea.tsx
git commit -m "feat(game): Fredoka font, GameTheme, routing scaffold

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: i18n strings

**Files:**
- Modify: `frontend/src/i18n/locales/ru.json`
- Modify: `frontend/src/i18n/locales/en.json`
- Modify: `frontend/src/i18n/locales/es.json`

**Interfaces:**
- Produces: all `game.*` translation keys used in Tasks 3–10.

- [ ] **Step 1: Add Russian strings** — open `frontend/src/i18n/locales/ru.json` and add a top-level `"game"` key:

```json
"game": {
  "selectPlayer": "Кто играет?",
  "newPlayer": "Новый игрок",
  "selectDifficulty": "Выбери сложность",
  "difficulty": {
    "easy": "Легко",
    "medium": "Средне",
    "hard": "Сложно"
  },
  "selectNoteCount": "Сколько нот?",
  "noteCount": "{{count}} нота",
  "noteCount_other": "{{count}} ноты",
  "startRound": "Поехали!",
  "timer": {
    "hurry": "Быстрее! 🔥"
  },
  "noteNames": {
    "solfege": { "C": "До", "D": "Ре", "E": "Ми", "F": "Фа", "G": "Соль", "A": "Ля", "B": "Си" },
    "letters": { "C": "C", "D": "D", "E": "E", "F": "F", "G": "G", "A": "A", "B": "B" }
  },
  "correct": "Правильно! ⭐",
  "wrong": "Почти! 😊",
  "timeout": "Время вышло! ⏰",
  "result": {
    "win": "Ура! Ты выиграл! 🎉",
    "lose": "Молодец! В следующий раз получится! 🌟",
    "score": "Очки: {{score}}",
    "correct": "Правильно: {{count}} из 7",
    "xpGained": "+{{xp}} XP",
    "levelUp": "Новый уровень! 🎊",
    "newTrophy": "Новый трофей! 🏆",
    "playAgain": "Ещё раз!",
    "changePlayer": "Сменить игрока",
    "practiceHint_prefix": "Совет: "
  },
  "profile": {
    "title": "Профиль",
    "trophies": "Трофеи",
    "noTrophies": "Трофеев пока нет — играй дальше!",
    "stats": "Статистика",
    "confusion": "Анализ ошибок",
    "level": "Уровень {{level}}",
    "xpProgress": "{{current}} / {{next}} XP"
  },
  "admin": {
    "title": "Игроки",
    "resetSeason": "Сбросить сезон",
    "resetAll": "Сбросить всех",
    "confirmReset": "Введите RESET для подтверждения",
    "seasonReset": "Сезон сброшен"
  },
  "avatar": {
    "generate": "Создать аватар",
    "describe": "Опиши своего зверя",
    "generating": "Создаём... 🎨",
    "ready": "Готово! Нравится?",
    "use": "Выбрать",
    "discard": "Не нравится",
    "quota": "Осталось генераций: {{remaining}}",
    "quotaExhausted": "Генерации на сегодня закончились 😴",
    "flagged": "Ой! Опиши другого зверя 🐾",
    "error": "Что-то пошло не так. Попробуй позже."
  },
  "errors": {
    "roundNotActive": "Раунд уже закончился",
    "generic": "Что-то пошло не так"
  }
}
```

- [ ] **Step 2: Add English strings** — same structure in `en.json`:

```json
"game": {
  "selectPlayer": "Who's playing?",
  "newPlayer": "New player",
  "selectDifficulty": "Choose difficulty",
  "difficulty": {
    "easy": "Easy",
    "medium": "Medium",
    "hard": "Hard"
  },
  "selectNoteCount": "How many notes?",
  "noteCount": "{{count}} note",
  "noteCount_other": "{{count}} notes",
  "startRound": "Let's go!",
  "timer": { "hurry": "Hurry! 🔥" },
  "noteNames": {
    "solfege": { "C": "Do", "D": "Re", "E": "Mi", "F": "Fa", "G": "Sol", "A": "La", "B": "Si" },
    "letters": { "C": "C", "D": "D", "E": "E", "F": "F", "G": "G", "A": "A", "B": "B" }
  },
  "correct": "Correct! ⭐",
  "wrong": "Almost! 😊",
  "timeout": "Time's up! ⏰",
  "result": {
    "win": "You won! 🎉",
    "lose": "Great try! Better luck next time! 🌟",
    "score": "Score: {{score}}",
    "correct": "Correct: {{count}} of 7",
    "xpGained": "+{{xp}} XP",
    "levelUp": "Level up! 🎊",
    "newTrophy": "New trophy! 🏆",
    "playAgain": "Play again!",
    "changePlayer": "Change player",
    "practiceHint_prefix": "Tip: "
  },
  "profile": {
    "title": "Profile",
    "trophies": "Trophies",
    "noTrophies": "No trophies yet — keep playing!",
    "stats": "Statistics",
    "confusion": "Mistake analysis",
    "level": "Level {{level}}",
    "xpProgress": "{{current}} / {{next}} XP"
  },
  "admin": {
    "title": "Players",
    "resetSeason": "Reset season",
    "resetAll": "Reset all",
    "confirmReset": "Type RESET to confirm",
    "seasonReset": "Season reset"
  },
  "avatar": {
    "generate": "Create avatar",
    "describe": "Describe your creature",
    "generating": "Creating... 🎨",
    "ready": "Done! Do you like it?",
    "use": "Use it",
    "discard": "Discard",
    "quota": "Generations left: {{remaining}}",
    "quotaExhausted": "No generations left today 😴",
    "flagged": "Oops! Try a different creature 🐾",
    "error": "Something went wrong. Try again later."
  },
  "errors": {
    "roundNotActive": "Round already ended",
    "generic": "Something went wrong"
  }
}
```

- [ ] **Step 3: Add Spanish strings** — same structure in `es.json`:

```json
"game": {
  "selectPlayer": "¿Quién juega?",
  "newPlayer": "Nuevo jugador",
  "selectDifficulty": "Elige dificultad",
  "difficulty": { "easy": "Fácil", "medium": "Medio", "hard": "Difícil" },
  "selectNoteCount": "¿Cuántas notas?",
  "noteCount": "{{count}} nota",
  "noteCount_other": "{{count}} notas",
  "startRound": "¡Vamos!",
  "timer": { "hurry": "¡Rápido! 🔥" },
  "noteNames": {
    "solfege": { "C": "Do", "D": "Re", "E": "Mi", "F": "Fa", "G": "Sol", "A": "La", "B": "Si" },
    "letters": { "C": "C", "D": "D", "E": "E", "F": "F", "G": "G", "A": "A", "B": "B" }
  },
  "correct": "¡Correcto! ⭐",
  "wrong": "¡Casi! 😊",
  "timeout": "¡Tiempo! ⏰",
  "result": {
    "win": "¡Ganaste! 🎉",
    "lose": "¡Buen intento! 🌟",
    "score": "Puntos: {{score}}",
    "correct": "Correctas: {{count}} de 7",
    "xpGained": "+{{xp}} XP",
    "levelUp": "¡Subiste de nivel! 🎊",
    "newTrophy": "¡Nuevo trofeo! 🏆",
    "playAgain": "¡Otra vez!",
    "changePlayer": "Cambiar jugador",
    "practiceHint_prefix": "Consejo: "
  },
  "profile": {
    "title": "Perfil",
    "trophies": "Trofeos",
    "noTrophies": "¡Sin trofeos aún — sigue jugando!",
    "stats": "Estadísticas",
    "confusion": "Análisis de errores",
    "level": "Nivel {{level}}",
    "xpProgress": "{{current}} / {{next}} XP"
  },
  "admin": {
    "title": "Jugadores",
    "resetSeason": "Reiniciar temporada",
    "resetAll": "Reiniciar todos",
    "confirmReset": "Escribe RESET para confirmar",
    "seasonReset": "Temporada reiniciada"
  },
  "avatar": {
    "generate": "Crear avatar",
    "describe": "Describe tu criatura",
    "generating": "Creando... 🎨",
    "ready": "¡Listo! ¿Te gusta?",
    "use": "Usar",
    "discard": "Descartar",
    "quota": "Generaciones restantes: {{remaining}}",
    "quotaExhausted": "Sin generaciones hoy 😴",
    "flagged": "¡Uy! Prueba otra criatura 🐾",
    "error": "Algo salió mal. Inténtalo más tarde."
  },
  "errors": {
    "roundNotActive": "La ronda ya terminó",
    "generic": "Algo salió mal"
  }
}
```

- [ ] **Step 4: Verify i18n builds**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors from i18n files.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/i18n/
git commit -m "feat(game): i18n strings for game module (ru/en/es)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: `staffPos` utility + unit tests

**Files:**
- Create: `frontend/src/features/game/staff/staffPos.ts`
- Create: `frontend/src/features/game/staff/staffPos.test.ts`

**Interfaces:**
- Produces: `staffPos(name: string, octave: number, clef: 'treble' | 'bass'): number`
  - Returns integer where 0 = bottom staff line, +2 = second line, +4 = middle line, +8 = top line.
  - Negative = below staff (ledger lines), > 8 = above staff.

- [ ] **Step 1: Write the test file first**

```ts
// frontend/src/features/game/staff/staffPos.test.ts
import { describe, expect, it } from "vitest";
import { staffPos } from "./staffPos";

describe("staffPos treble", () => {
  // Bottom line = E4 (pos 0), top line = F5 (pos 8)
  it("E4 = 0 (bottom line)", () => expect(staffPos("E", 4, "treble")).toBe(0));
  it("F4 = 1 (first space)", () => expect(staffPos("F", 4, "treble")).toBe(1));
  it("G4 = 2 (second line)", () => expect(staffPos("G", 4, "treble")).toBe(2));
  it("A4 = 3 (second space)", () => expect(staffPos("A", 4, "treble")).toBe(3));
  it("B4 = 4 (middle line)", () => expect(staffPos("B", 4, "treble")).toBe(4));
  it("C5 = 5 (third space)", () => expect(staffPos("C", 5, "treble")).toBe(5));
  it("D5 = 6 (fourth line)", () => expect(staffPos("D", 5, "treble")).toBe(6));
  it("E5 = 7 (fourth space)", () => expect(staffPos("E", 5, "treble")).toBe(7));
  it("F5 = 8 (top line)", () => expect(staffPos("F", 5, "treble")).toBe(8));
  it("G5 = 9 (above top line)", () => expect(staffPos("G", 5, "treble")).toBe(9));
  // Ledger lines below
  it("D4 = -1 (below bottom, space)", () => expect(staffPos("D", 4, "treble")).toBe(-1));
  it("C4 = -2 (ledger line below)", () => expect(staffPos("C", 4, "treble")).toBe(-2));
});

describe("staffPos bass", () => {
  // Bottom line = G2 (pos 0), top line = A3 (pos 8)
  it("G2 = 0 (bottom line)", () => expect(staffPos("G", 2, "bass")).toBe(0));
  it("A2 = 1 (first space)", () => expect(staffPos("A", 2, "bass")).toBe(1));
  it("B2 = 2 (second line)", () => expect(staffPos("B", 2, "bass")).toBe(2));
  it("C3 = 3 (second space)", () => expect(staffPos("C", 3, "bass")).toBe(3));
  it("D3 = 4 (middle line)", () => expect(staffPos("D", 3, "bass")).toBe(4));
  it("E3 = 5 (third space)", () => expect(staffPos("E", 3, "bass")).toBe(5));
  it("F3 = 6 (fourth line)", () => expect(staffPos("F", 3, "bass")).toBe(6));
  it("G3 = 7 (fourth space)", () => expect(staffPos("G", 3, "bass")).toBe(7));
  it("A3 = 8 (top line)", () => expect(staffPos("A", 3, "bass")).toBe(8));
  it("B3 = 9 (above top line)", () => expect(staffPos("B", 3, "bass")).toBe(9));
  it("C4 = 10 (two above top)", () => expect(staffPos("C", 4, "bass")).toBe(10));
  // Ledger lines below
  it("F2 = -1 (below bottom, space)", () => expect(staffPos("F", 2, "bass")).toBe(-1));
  it("E2 = -2 (ledger line below)", () => expect(staffPos("E", 2, "bass")).toBe(-2));
});
```

- [ ] **Step 2: Run to verify FAIL**

```bash
cd frontend && npx vitest run src/features/game/staff/staffPos.test.ts
```
Expected: `Cannot find module './staffPos'`.

- [ ] **Step 3: Write `staffPos.ts`**

```ts
// frontend/src/features/game/staff/staffPos.ts
const DIATONIC: Record<string, number> = { C: 0, D: 1, E: 2, F: 3, G: 4, A: 5, B: 6 };
const abs = (name: string, octave: number) => octave * 7 + DIATONIC[name];
const CLEF_REF = { treble: abs("E", 4), bass: abs("G", 2) } as const; // 30, 18

export const staffPos = (name: string, octave: number, clef: "treble" | "bass"): number =>
  abs(name, octave) - CLEF_REF[clef];

// MIDI for audio synthesis: C4 = 60
const MIDI_C4 = 60;
export const toMidi = (name: string, octave: number): number =>
  MIDI_C4 + (octave - 4) * 12 + [0, 2, 4, 5, 7, 9, 11][DIATONIC[name]];
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/features/game/staff/staffPos.test.ts
```
Expected: all 26 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/game/staff/
git commit -m "feat(game): staffPos utility with full unit tests

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Staff SVG component

**Files:**
- Create: `frontend/src/features/game/staff/Staff.tsx`
- Create: `frontend/src/features/game/staff/clefPaths.ts`

**Interfaces:**
- Consumes: `staffPos` from `./staffPos`
- Produces: `<Staff notes={[{name, octave}]} clef="treble|bass" />` — renders 5 staff lines, clef glyph, note heads, stems, ledger lines.

- [ ] **Step 1: Create `clefPaths.ts`** — inline SVG path data for treble and bass clefs (free Bravura paths, SIL OFL). If Bravura paths are not yet available, use simple placeholder paths and add a comment with the Bravura download URL.

```ts
// frontend/src/features/game/staff/clefPaths.ts
// TODO: Replace with real Bravura glyph paths from:
// https://github.com/steinbergmedia/bravura/blob/master/redist/bravura.svg
// Both glyphs below are simplified placeholders — readable but not publication-quality.

export const TREBLE_CLEF_PATH =
  "M 6 38 C 6 32 10 28 14 28 C 18 28 22 32 22 38 C 22 50 12 56 12 68 " +
  "C 12 76 16 82 20 86 C 20 90 18 94 14 94 C 10 94 6 90 6 86 " +
  "C 6 76 14 70 14 60 C 14 48 8 44 8 38 Z " +
  "M 12 12 L 12 100"; // simplified stem

export const BASS_CLEF_PATH =
  "M 4 20 C 4 12 10 6 18 6 C 26 6 32 12 32 20 C 32 32 22 40 14 44 " +
  "L 14 60 M 36 14 C 36 14 38 14 38 16 C 38 18 36 18 36 16 Z " +
  "M 36 22 C 36 22 38 22 38 24 C 38 26 36 26 36 24 Z"; // simplified F clef
```

- [ ] **Step 2: Create `Staff.tsx`**

```tsx
// frontend/src/features/game/staff/Staff.tsx
import { staffPos } from "./staffPos";
import { BASS_CLEF_PATH, TREBLE_CLEF_PATH } from "./clefPaths";

interface Note {
  name: string;
  octave: number;
}

interface StaffProps {
  notes: Note[];
  clef: "treble" | "bass";
}

// Layout constants (viewBox units)
const LINE_SPACING = 12;   // px between staff lines
const STAFF_TOP = 40;      // y of top (5th) line
const NOTE_R = 7;          // note head radius
const CLEF_X = 10;
const FIRST_NOTE_X = 70;
const NOTE_X_GAP = 36;

function lineY(lineIndex: number): number {
  // lineIndex 0 = bottom, 4 = top
  return STAFF_TOP + (4 - lineIndex) * LINE_SPACING;
}

function posY(pos: number): number {
  // pos 0 = bottom line (lineIndex 0); each unit = half LINE_SPACING
  return lineY(0) - (pos * LINE_SPACING) / 2;
}

export default function Staff({ notes, clef }: StaffProps) {
  const staffWidth = FIRST_NOTE_X + notes.length * NOTE_X_GAP + 20;
  const viewHeight = 140;

  const positions = notes.map((n) => staffPos(n.name, n.octave, clef));

  // Ledger lines needed: pos < 0 (below) or pos > 8 (above), even positions only
  function ledgerLines(pos: number, x: number) {
    const lines: JSX.Element[] = [];
    if (pos <= -2) {
      for (let p = -2; p >= pos; p -= 2) {
        const y = posY(p);
        lines.push(
          <line key={`ld-${p}`} x1={x - NOTE_R - 3} y1={y} x2={x + NOTE_R + 3} y2={y}
            stroke="#222" strokeWidth={1.5} />
        );
      }
    }
    if (pos >= 10) {
      for (let p = 10; p <= pos; p += 2) {
        const y = posY(p);
        lines.push(
          <line key={`lu-${p}`} x1={x - NOTE_R - 3} y1={y} x2={x + NOTE_R + 3} y2={y}
            stroke="#222" strokeWidth={1.5} />
        );
      }
    }
    return lines;
  }

  return (
    <svg
      viewBox={`0 0 ${staffWidth} ${viewHeight}`}
      style={{ width: "100%", maxWidth: 480, display: "block", margin: "0 auto" }}
      aria-label={`${clef} clef staff with ${notes.length} note${notes.length > 1 ? "s" : ""}`}
      role="img"
    >
      {/* Staff paper background */}
      <rect x={0} y={0} width={staffWidth} height={viewHeight} fill="#FFFDF5" rx={8} />

      {/* 5 staff lines */}
      {[0, 1, 2, 3, 4].map((i) => (
        <line key={i} x1={6} y1={lineY(i)} x2={staffWidth - 6} y2={lineY(i)}
          stroke="#555" strokeWidth={1.2} />
      ))}

      {/* Clef glyph */}
      <path
        d={clef === "treble" ? TREBLE_CLEF_PATH : BASS_CLEF_PATH}
        fill="none"
        stroke="#333"
        strokeWidth={2}
        transform={`translate(${CLEF_X}, ${STAFF_TOP - 20})`}
      />

      {/* Notes */}
      {notes.map((note, idx) => {
        const pos = positions[idx];
        const x = FIRST_NOTE_X + idx * NOTE_X_GAP;
        const y = posY(pos);
        const stemUp = pos < 4; // below middle line → stem up
        return (
          <g key={idx}>
            {ledgerLines(pos, x)}
            <ellipse cx={x} cy={y} rx={NOTE_R} ry={NOTE_R * 0.72}
              fill="#1a1a1a" transform={`rotate(-15, ${x}, ${y})`} />
            {/* Stem */}
            {stemUp
              ? <line x1={x + NOTE_R - 1} y1={y} x2={x + NOTE_R - 1} y2={y - 36}
                  stroke="#1a1a1a" strokeWidth={1.5} />
              : <line x1={x - NOTE_R + 1} y1={y} x2={x - NOTE_R + 1} y2={y + 36}
                  stroke="#1a1a1a" strokeWidth={1.5} />
            }
          </g>
        );
      })}
    </svg>
  );
}
```

- [ ] **Step 3: Smoke-test the component renders in the game area**

Edit `frontend/src/features/game/index.tsx` temporarily:

```tsx
import Staff from "./staff/Staff";
import GameTheme from "./GameTheme";

export default function GameArea() {
  return (
    <GameTheme>
      <div style={{ padding: 24 }}>
        <Staff notes={[{ name: "G", octave: 4 }]} clef="treble" />
        <Staff notes={[{ name: "C", octave: 3 }, { name: "E", octave: 3 }]} clef="bass" />
      </div>
    </GameTheme>
  );
}
```

Open `http://localhost:5173/game` and visually confirm two staffs render with note heads and stems.

- [ ] **Step 4: Revert `index.tsx` to placeholder** (undo the smoke-test change)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/game/staff/
git commit -m "feat(game): Staff SVG component with clef, note heads, ledger lines

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Web Audio synthesis

**Files:**
- Create: `frontend/src/features/game/audio/synth.ts`

**Interfaces:**
- Consumes: `toMidi` from `../staff/staffPos`
- Produces:
  - `playNote(name: string, octave: number): void` — fire-and-forget, errors silently swallowed
  - `setMuted(muted: boolean): void`
  - `isMuted(): boolean`

- [ ] **Step 1: Create `frontend/src/features/game/audio/synth.ts`**

```ts
// frontend/src/features/game/audio/synth.ts
import { toMidi } from "../staff/staffPos";

let ctx: AudioContext | null = null;
const MUTE_KEY = "game_muted";

export function isMuted(): boolean {
  try {
    return localStorage.getItem(MUTE_KEY) === "1";
  } catch {
    return false;
  }
}

export function setMuted(muted: boolean): void {
  try {
    localStorage.setItem(MUTE_KEY, muted ? "1" : "0");
  } catch {/* ignore */}
}

function getCtx(): AudioContext {
  if (!ctx) ctx = new AudioContext();
  return ctx;
}

export function unlockAudio(): void {
  // Call on first user gesture to satisfy browser autoplay policy
  try { getCtx().resume(); } catch {/* ignore */}
}

export function playNote(name: string, octave: number): void {
  if (isMuted()) return;
  try {
    const ac = getCtx();
    if (ac.state === "suspended") ac.resume();
    const midi = toMidi(name, octave);
    const freq = 440 * Math.pow(2, (midi - 69) / 12);
    const osc = ac.createOscillator();
    const gain = ac.createGain();
    osc.type = "triangle";
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.35, ac.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.3);
    osc.connect(gain);
    gain.connect(ac.destination);
    osc.start(ac.currentTime);
    osc.stop(ac.currentTime + 0.3);
  } catch {
    // Audio errors must never block input
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/game/audio/
git commit -m "feat(game): Web Audio triangle oscillator synth

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 6: API client layer (TanStack Query)

**Files:**
- Create: `frontend/src/features/game/api/client.ts`
- Create: `frontend/src/features/game/api/hooks.ts`

**Interfaces:**
- Consumes: existing `fetch` wrapper / base URL pattern from `frontend/src/api/` (check how existing API calls are made and follow that convention)
- Produces (all TanStack Query hooks):
  - `usePlayers()` — `GET /api/game/players`
  - `useCreatePlayer(options)` — `POST /api/game/players`
  - `useStartRound(options)` — `POST /api/game/rounds`
  - `useSubmitTask(roundId, options)` — `POST /api/game/rounds/{id}/submit`
  - `usePlayerStats(playerId)` — `GET /api/game/players/{id}/stats`
  - `usePlayerConfusion(playerId)` — `GET /api/game/players/{id}/confusion`
  - `useAvatarQuota()` — `GET /api/game/avatars/quota`
  - `useGenerateAvatar(options)` — `POST /api/game/avatars/generate`
  - `useAvatarStatus(jobId)` — `GET /api/game/avatars/{jobId}/status`
  - `useSeasons(playerId)` — `GET /api/game/players/{id}/seasons`
  - `useResetSeason(options)` — `POST /api/game/players/{id}/seasons/reset`

- [ ] **Step 1: Read how existing API calls work** to understand the fetch wrapper pattern:

```bash
grep -r "fetch\|apiGet\|apiPost" frontend/src/api/ | head -20
```

- [ ] **Step 2: Create `frontend/src/features/game/api/client.ts`** — follow exactly the existing `frontend/src/api/` conventions. If the app uses a typed `apiFetch(path, options)` helper, import and reuse it. If it uses raw `fetch`, follow that. Example (adapt to match existing convention):

```ts
// frontend/src/features/game/api/client.ts
// Adapt this to match the existing fetch wrapper found in frontend/src/api/
import { apiFetch } from "../../../api/client"; // adjust import path to actual location

export const gameFetch = {
  get: <T>(path: string) => apiFetch<T>(`/api/game${path}`),
  post: <T>(path: string, body?: unknown) =>
    apiFetch<T>(`/api/game${path}`, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(path: string, body?: unknown) =>
    apiFetch<T>(`/api/game${path}`, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string) =>
    apiFetch<T>(`/api/game${path}`, { method: "DELETE" }),
};
```

> **Note:** Check `frontend/src/api/` for the real fetch helper name and import path before writing this file. Match it exactly.

- [ ] **Step 3: Create `frontend/src/features/game/api/hooks.ts`**

```ts
// frontend/src/features/game/api/hooks.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { gameFetch } from "./client";

// --- Players ---
export const usePlayers = () =>
  useQuery({ queryKey: ["game", "players"], queryFn: () => gameFetch.get<Player[]>("/players") });

export const useCreatePlayer = (options?: MutationOptions) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; avatar_animal?: string }) =>
      gameFetch.post<Player>("/players", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["game", "players"] }),
    ...options,
  });
};

// --- Rounds ---
export const useStartRound = (options?: MutationOptions) =>
  useMutation({
    mutationFn: (body: { player_id: number; difficulty: string; note_count: number }) =>
      gameFetch.post<{ round_id: number; task: Task }>("/rounds", body),
    ...options,
  });

export const useSubmitTask = (roundId: number, options?: MutationOptions) =>
  useMutation({
    mutationFn: (body: { task_index: number; answers?: Note[] | null; timed_out?: boolean }) =>
      gameFetch.post<SubmitResponse>(`/rounds/${roundId}/submit`, body),
    ...options,
  });

// --- Stats ---
export const usePlayerStats = (playerId: number) =>
  useQuery({
    queryKey: ["game", "stats", playerId],
    queryFn: () => gameFetch.get<StatsMatrix>(`/players/${playerId}/stats`),
  });

export const usePlayerConfusion = (playerId: number) =>
  useQuery({
    queryKey: ["game", "confusion", playerId],
    queryFn: () => gameFetch.get<ConfusionData>(`/players/${playerId}/confusion`),
  });

// --- Avatars ---
export const useAvatarQuota = () =>
  useQuery({ queryKey: ["game", "avatar-quota"], queryFn: () => gameFetch.get<QuotaData>("/avatars/quota") });

export const useGenerateAvatar = (options?: MutationOptions) =>
  useMutation({
    mutationFn: (body: { player_id: number; description: string }) =>
      gameFetch.post<{ job_id: number }>("/avatars/generate", body),
    ...options,
  });

export const useAvatarStatus = (jobId: number | null) =>
  useQuery({
    queryKey: ["game", "avatar-status", jobId],
    queryFn: () => gameFetch.get<AvatarJob>(`/avatars/${jobId}/status`),
    enabled: jobId !== null,
    refetchInterval: (query) => (query.state.data?.status === "pending" ? 2000 : false),
  });

// --- Seasons ---
export const useSeasons = (playerId: number) =>
  useQuery({
    queryKey: ["game", "seasons", playerId],
    queryFn: () => gameFetch.get<Season[]>(`/players/${playerId}/seasons`),
  });

export const useResetSeason = (options?: MutationOptions) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ playerId, confirmation }: { playerId: number; confirmation: string }) =>
      gameFetch.post(`/players/${playerId}/seasons/reset`, { confirmation }),
    onSuccess: (_, { playerId }) => {
      qc.invalidateQueries({ queryKey: ["game", "seasons", playerId] });
      qc.invalidateQueries({ queryKey: ["game", "stats", playerId] });
    },
    ...options,
  });
};

// Types (inline — no separate file needed)
type MutationOptions = Record<string, unknown>;
interface Player { id: number; name: string; avatar_animal?: string; custom_avatar_id?: number; xp: number; }
interface Note { name: string; octave: number; }
interface Task { index: number; clef: string; notes: Note[]; }
interface SubmitResponse { is_correct: boolean; correct_answers: Note[]; score_delta: number; next_task: Task | null; result: RoundResult | null; }
interface RoundResult { score: number; correct_count: number; is_win: boolean; xp_gained: number; level_up: boolean; new_trophy: number | null; practice_hint: string; }
interface StatsMatrix { [difficulty: string]: { [noteCount: string]: { rounds: number; total_correct: number; avg_score: number } } }
interface ConfusionData { heatmap: Record<string, Record<string, number>>; top_confusions: Array<{ expected: string; given: string; count: number }> }
interface QuotaData { used: number; limit: number | null; resets_at: string | null; }
interface AvatarJob { id: number; status: string; base_path?: string; happy_path?: string; sad_path?: string; error_code?: string; }
interface Season { id: number; player_id: number; number: number; started_at: string; ended_at: string | null; }
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/game/api/
git commit -m "feat(game): TanStack Query API client layer

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Setup screens (player pick → difficulty → note count)

**Files:**
- Create: `frontend/src/features/game/setup/PlayerSelect.tsx`
- Create: `frontend/src/features/game/setup/GameSetup.tsx`
- Create: `frontend/src/features/game/setup/AvatarImage.tsx`
- Modify: `frontend/src/features/game/index.tsx` — wire routing to setup/play

**Interfaces:**
- Consumes: `usePlayers`, `useStartRound` from `../api/hooks`; `GameTheme` from `../GameTheme`
- Produces: `/game` → player selection; `/game/setup/:playerId` → difficulty + note count → starts round and navigates to `/game/play/:roundId`

- [ ] **Step 1: Create `AvatarImage.tsx`** — resolver with fallback

```tsx
// frontend/src/features/game/setup/AvatarImage.tsx
interface AvatarImageProps {
  animalId: string;
  stage?: number;   // 1–10
  mood?: "neutral" | "happy" | "sad";
  size?: number;
  customBasePath?: string | null;
  customMoodPath?: string | null;
}

const PLACEHOLDER_COLORS: Record<string, string> = {
  unicorn: "#e8b4f0", dragon: "#f0b4b4", phoenix: "#f0d4b4", griffin: "#d4c4a8",
  sphinx_cat: "#c4d4f0", kitsune_fox: "#f0c4a8", pegasus: "#b4d4f0", mermaid: "#b4f0e8",
};
const ANIMAL_EMOJI: Record<string, string> = {
  unicorn: "🦄", dragon: "🐉", phoenix: "🦅", griffin: "🦁",
  sphinx_cat: "🐱", kitsune_fox: "🦊", pegasus: "🐴", mermaid: "🧜",
};

function placeholderSvgUrl(animalId: string, stage: number, mood: string): string {
  const bg = PLACEHOLDER_COLORS[animalId] ?? "#ddd";
  const emoji = ANIMAL_EMOJI[animalId] ?? "?";
  const mood_emoji = mood === "happy" ? "😊" : mood === "sad" ? "😢" : "😐";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">
    <circle cx="60" cy="60" r="56" fill="${bg}" stroke="#fff" stroke-width="4"/>
    <text x="60" y="62" font-size="40" text-anchor="middle" dominant-baseline="middle">${emoji}</text>
    <text x="96" y="26" font-size="22" text-anchor="middle" dominant-baseline="middle">${mood_emoji}</text>
    <circle cx="24" cy="96" r="14" fill="#888"/>
    <text x="24" y="100" font-size="12" font-family="monospace" fill="#fff" text-anchor="middle" dominant-baseline="middle">${String(stage).padStart(2,"0")}</text>
  </svg>`;
  return "data:image/svg+xml;utf8," + encodeURIComponent(svg);
}

export default function AvatarImage({
  animalId, stage = 1, mood = "neutral", size = 80,
  customBasePath = null, customMoodPath = null,
}: AvatarImageProps) {
  const moodPath = mood === "neutral" ? customBasePath : customMoodPath;
  if (moodPath) {
    return <img src={moodPath} width={size} height={size} alt={animalId}
      style={{ borderRadius: "50%", objectFit: "cover" }} />;
  }
  const pad = String(stage).padStart(2, "0");
  const base = `/assets/avatars/${animalId}/`;
  const fallbackSrc = placeholderSvgUrl(animalId, stage, mood);

  return (
    <img
      src={`${base}${pad}_${mood}.png`}
      width={size} height={size} alt={animalId}
      style={{ borderRadius: "50%", objectFit: "cover" }}
      onError={(e) => {
        const img = e.currentTarget;
        if (!img.dataset.s1) {
          img.dataset.s1 = "1";
          img.src = `${base}${pad}_neutral.png`;
        } else if (!img.dataset.s2) {
          img.dataset.s2 = "1";
          img.src = `${base}01_neutral.png`;
        } else {
          img.src = fallbackSrc;
          img.onerror = null;
        }
      }}
    />
  );
}
```

- [ ] **Step 2: Create `PlayerSelect.tsx`**

```tsx
// frontend/src/features/game/setup/PlayerSelect.tsx
import { Box, Button, Card, CardActionArea, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { usePlayers } from "../api/hooks";
import AvatarImage from "./AvatarImage";

interface Props { onSelect: (playerId: number) => void; }

export default function PlayerSelect({ onSelect }: Props) {
  const { t } = useTranslation();
  const { data: players = [], isLoading } = usePlayers();

  if (isLoading) return <Box sx={{ p: 4, textAlign: "center" }}>…</Box>;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 3, textAlign: "center", fontWeight: 700 }}>
        {t("game.selectPlayer")}
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2, justifyContent: "center" }}>
        {players.map((p) => (
          <Card key={p.id} sx={{ width: 140 }}>
            <CardActionArea
              onClick={() => onSelect(p.id)}
              sx={{ p: 2, display: "flex", flexDirection: "column", alignItems: "center", gap: 1 }}
            >
              <AvatarImage animalId={p.avatar_animal ?? "unicorn"} size={80} />
              <Typography variant="body1" fontWeight={600} textAlign="center">{p.name}</Typography>
              <Typography variant="caption" color="text.secondary">{p.xp} XP</Typography>
            </CardActionArea>
          </Card>
        ))}
      </Box>
    </Box>
  );
}
```

- [ ] **Step 3: Create `GameSetup.tsx`** — difficulty + note count selection

```tsx
// frontend/src/features/game/setup/GameSetup.tsx
import { Box, Button, Typography } from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useStartRound } from "../api/hooks";
import { unlockAudio } from "../audio/synth";

const DIFFICULTIES = ["easy", "medium", "hard"] as const;
const NOTE_COUNTS = [1, 2, 3, 4] as const;

interface Props { playerId: number; onRoundStarted: (roundId: number, firstTask: Task) => void; }
interface Task { index: number; clef: string; notes: Array<{ name: string; octave: number }>; }

export default function GameSetup({ playerId, onRoundStarted }: Props) {
  const { t } = useTranslation();
  const [difficulty, setDifficulty] = useState<string>("easy");
  const [noteCount, setNoteCount] = useState<number>(1);
  const startRound = useStartRound();

  const handleStart = () => {
    unlockAudio();
    startRound.mutate(
      { player_id: playerId, difficulty, note_count: noteCount },
      { onSuccess: (data) => onRoundStarted(data.round_id, data.task) }
    );
  };

  return (
    <Box sx={{ p: 3, maxWidth: 400, mx: "auto" }}>
      <Typography variant="h5" sx={{ mb: 2, fontWeight: 700 }}>{t("game.selectDifficulty")}</Typography>
      <Box sx={{ display: "flex", gap: 1, mb: 3 }}>
        {DIFFICULTIES.map((d) => (
          <Button key={d} variant={difficulty === d ? "contained" : "outlined"}
            onClick={() => setDifficulty(d)} sx={{ flex: 1 }}>
            {t(`game.difficulty.${d}`)}
          </Button>
        ))}
      </Box>

      <Typography variant="h5" sx={{ mb: 2, fontWeight: 700 }}>{t("game.selectNoteCount")}</Typography>
      <Box sx={{ display: "flex", gap: 1, mb: 4 }}>
        {NOTE_COUNTS.map((n) => (
          <Button key={n} variant={noteCount === n ? "contained" : "outlined"}
            onClick={() => setNoteCount(n)} sx={{ flex: 1, minHeight: 64, fontSize: "1.4rem" }}>
            {n}
          </Button>
        ))}
      </Box>

      <Button variant="contained" size="large" fullWidth onClick={handleStart}
        disabled={startRound.isPending} sx={{ minHeight: 64, fontSize: "1.2rem" }}>
        {t("game.startRound")}
      </Button>
    </Box>
  );
}
```

- [ ] **Step 4: Wire routing in `frontend/src/features/game/index.tsx`**

```tsx
import { useState } from "react";
import GameTheme from "./GameTheme";
import PlayerSelect from "./setup/PlayerSelect";
import GameSetup from "./setup/GameSetup";

type Screen =
  | { name: "players" }
  | { name: "setup"; playerId: number }
  | { name: "play"; roundId: number; firstTask: Task };

interface Task { index: number; clef: string; notes: Array<{ name: string; octave: number }>; }

export default function GameArea() {
  const path = window.location.pathname;
  const [screen, setScreen] = useState<Screen>(() => {
    const m = path.match(/^\/game\/setup\/(\d+)/);
    if (m) return { name: "setup", playerId: Number(m[1]) };
    return { name: "players" };
  });

  return (
    <GameTheme>
      {screen.name === "players" && (
        <PlayerSelect onSelect={(id) => {
          window.history.pushState(null, "", `/game/setup/${id}`);
          setScreen({ name: "setup", playerId: id });
        }} />
      )}
      {screen.name === "setup" && (
        <GameSetup
          playerId={screen.playerId}
          onRoundStarted={(roundId, firstTask) => {
            window.history.pushState(null, "", `/game/play/${roundId}`);
            setScreen({ name: "play", roundId, firstTask });
          }}
        />
      )}
      {screen.name === "play" && (
        <div style={{ padding: 24 }}>Play screen coming in Task 8</div>
      )}
    </GameTheme>
  );
}
```

- [ ] **Step 5: Verify in browser** — open `/game`, pick a player card, see difficulty/note count buttons, click "Поехали!". Should transition to "Play screen coming in Task 8".

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/game/setup/ frontend/src/features/game/index.tsx
git commit -m "feat(game): setup screens — player select, difficulty, note count

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 8: Play screen (staff + note buttons + timer)

**Files:**
- Create: `frontend/src/features/game/play/Timer.tsx`
- Create: `frontend/src/features/game/play/NoteButtons.tsx`
- Create: `frontend/src/features/game/play/PlayScreen.tsx`
- Modify: `frontend/src/features/game/index.tsx` — wire play screen

**Interfaces:**
- Consumes: `Staff` from `../staff/Staff`; `playNote` from `../audio/synth`; `useSubmitTask` from `../api/hooks`
- Produces: full play loop — renders staff for current task, note buttons, timer; on submit calls API, shows 1s feedback, advances to next task or shows result

- [ ] **Step 1: Create `Timer.tsx`**

```tsx
// frontend/src/features/game/play/Timer.tsx
import { Box, Typography } from "@mui/material";
import { useEffect, useRef, useState } from "react";

interface Props {
  totalMs: number;
  onExpire: () => void;
  paused?: boolean;
}

export default function Timer({ totalMs, onExpire, paused = false }: Props) {
  const startRef = useRef(Date.now());
  const pausedAtRef = useRef<number | null>(null);
  const [remaining, setRemaining] = useState(totalMs);
  const expiredRef = useRef(false);

  useEffect(() => {
    if (paused) {
      pausedAtRef.current = Date.now();
      return;
    }
    if (pausedAtRef.current !== null) {
      startRef.current += Date.now() - pausedAtRef.current;
      pausedAtRef.current = null;
    }

    const tick = () => {
      const elapsed = Date.now() - startRef.current;
      const left = Math.max(0, totalMs - elapsed);
      setRemaining(left);
      if (left <= 0 && !expiredRef.current) {
        expiredRef.current = true;
        onExpire();
      }
    };
    const id = setInterval(tick, 50);
    return () => clearInterval(id);
  }, [paused, totalMs, onExpire]);

  // Page visibility: pause when hidden
  useEffect(() => {
    const handler = () => {
      if (document.hidden) pausedAtRef.current = Date.now();
      else if (pausedAtRef.current !== null) {
        startRef.current += Date.now() - pausedAtRef.current;
        pausedAtRef.current = null;
      }
    };
    document.addEventListener("visibilitychange", handler);
    return () => document.removeEventListener("visibilitychange", handler);
  }, []);

  const pct = (remaining / totalMs) * 100;
  const hurry = remaining < 2000;

  return (
    <Box sx={{ mb: 2 }}>
      {hurry && (
        <Typography variant="caption" sx={{ display: "block", textAlign: "center", color: "#e55" }}>
          🔥 {Math.ceil(remaining / 1000)}
        </Typography>
      )}
      <Box sx={{
        height: 14, borderRadius: 99, overflow: "hidden",
        background: "#eee", position: "relative",
        "@media (prefers-reduced-motion: reduce)": { "& > div": { transition: "none" } },
      }}>
        <Box sx={{
          position: "absolute", left: 0, top: 0, bottom: 0,
          width: `${pct}%`,
          background: hurry ? "#FF6B35" : "#6BCB77",
          transition: "width 0.05s linear, background 0.3s",
        }} />
      </Box>
    </Box>
  );
}
```

- [ ] **Step 2: Create `NoteButtons.tsx`**

```tsx
// frontend/src/features/game/play/NoteButtons.tsx
import { Box, Button } from "@mui/material";
import { useTranslation } from "react-i18next";
import { playNote } from "../audio/synth";

const NOTE_NAMES = ["C", "D", "E", "F", "G", "A", "B"] as const;
const RAINBOW = ["#FF6B6B","#FF8E53","#FFD93D","#6BCB77","#4EC9B0","#4D96FF","#9B59B6"];

interface Props {
  clef: "treble" | "bass";
  noteNaming: "solfege" | "letters";
  onAnswer: (name: string) => void;
  disabled?: boolean;
}

// Play the note nearest to the clef midpoint
const CLEF_OCTAVE = { treble: 5, bass: 3 };

export default function NoteButtons({ clef, noteNaming, onAnswer, disabled = false }: Props) {
  const { t } = useTranslation();

  return (
    <Box sx={{
      display: "flex", flexWrap: "wrap", gap: 1.5,
      justifyContent: "center", mt: 3,
    }}>
      {NOTE_NAMES.map((name, i) => (
        <Button
          key={name}
          variant="contained"
          disabled={disabled}
          onClick={() => {
            playNote(name, CLEF_OCTAVE[clef]);
            onAnswer(name);
          }}
          sx={{
            minWidth: 64, minHeight: 64,
            fontSize: "1.1rem", fontWeight: 700,
            background: RAINBOW[i],
            "&:hover": { background: RAINBOW[i], filter: "brightness(1.1)" },
            "&.Mui-disabled": { opacity: 0.4, background: RAINBOW[i] },
          }}
          aria-label={t(`game.noteNames.${noteNaming}.${name}` as const)}
        >
          {t(`game.noteNames.${noteNaming}.${name}` as const)}
        </Button>
      ))}
    </Box>
  );
}
```

- [ ] **Step 3: Create `PlayScreen.tsx`**

```tsx
// frontend/src/features/game/play/PlayScreen.tsx
import { Alert, Box, Button, Typography } from "@mui/material";
import { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Staff from "../staff/Staff";
import { useSubmitTask } from "../api/hooks";
import NoteButtons from "./NoteButtons";
import Timer from "./Timer";

interface Note { name: string; octave: number; }
interface Task { index: number; clef: string; notes: Note[]; }
interface RoundResult {
  score: number; correct_count: number; is_win: boolean;
  xp_gained: number; level_up: boolean; new_trophy: number | null;
  practice_hint: string;
}

interface Props {
  roundId: number;
  initialTask: Task;
  noteNaming?: "solfege" | "letters";
  noteCount: number;
  difficulty: string;
  timeLimitMs: number;
  onResult: (result: RoundResult) => void;
}

type FeedbackState = "idle" | "correct" | "wrong" | "timeout";

export default function PlayScreen({
  roundId, initialTask, noteNaming = "solfege", noteCount, difficulty, timeLimitMs, onResult,
}: Props) {
  const { t } = useTranslation();
  const [task, setTask] = useState<Task>(initialTask);
  const [answers, setAnswers] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<FeedbackState>("idle");
  const [timerKey, setTimerKey] = useState(0);
  const submittingRef = useRef(false);
  const submitTask = useSubmitTask(roundId);

  const doSubmit = useCallback((givenAnswers: string[] | null, timedOut: boolean) => {
    if (submittingRef.current) return;
    submittingRef.current = true;

    const body = timedOut
      ? { task_index: task.index, timed_out: true }
      : {
          task_index: task.index,
          answers: givenAnswers?.map((name) => ({ name, octave: task.notes[0].octave })) ?? null,
        };

    submitTask.mutate(body as Parameters<typeof submitTask.mutate>[0], {
      onSuccess: (data) => {
        setFeedback(timedOut ? "timeout" : data.is_correct ? "correct" : "wrong");
        setTimeout(() => {
          submittingRef.current = false;
          if (data.result) {
            onResult(data.result);
          } else if (data.next_task) {
            setTask(data.next_task);
            setAnswers([]);
            setFeedback("idle");
            setTimerKey((k) => k + 1);
          }
        }, 900);
      },
      onError: () => { submittingRef.current = false; },
    });
  }, [task.index, submitTask, onResult]);

  const handleAnswer = (name: string) => {
    if (feedback !== "idle") return;
    const next = [...answers, name];
    setAnswers(next);
    if (next.length === noteCount) {
      doSubmit(next, false);
    }
  };

  const handleBackspace = () => {
    if (feedback !== "idle" || answers.length === 0) return;
    setAnswers((a) => a.slice(0, -1));
  };

  const handleTimeout = useCallback(() => doSubmit(null, true), [doSubmit]);

  const isWaiting = feedback !== "idle";
  const clef = task.clef as "treble" | "bass";

  return (
    <Box sx={{ p: 2, maxWidth: 480, mx: "auto" }}>
      <Typography variant="caption" sx={{ display: "block", textAlign: "center", mb: 1, color: "#888" }}>
        {task.index + 1} / 7
      </Typography>

      <Timer key={timerKey} totalMs={timeLimitMs} onExpire={handleTimeout} paused={isWaiting} />

      {feedback !== "idle" && (
        <Alert severity={feedback === "correct" ? "success" : "error"} sx={{ mb: 1 }}>
          {feedback === "correct" ? t("game.correct")
            : feedback === "timeout" ? t("game.timeout")
            : t("game.wrong")}
        </Alert>
      )}

      <Box sx={{ background: "#FFFDF5", borderRadius: 3, p: 2, my: 2 }}>
        <Staff notes={task.notes} clef={clef} />
      </Box>

      {/* Answer slots */}
      <Box sx={{ display: "flex", gap: 1, justifyContent: "center", mb: 1 }}>
        {Array.from({ length: noteCount }).map((_, i) => (
          <Box key={i} sx={{
            width: 48, height: 48, borderRadius: 2,
            border: "2px solid #ccc",
            background: answers[i] ? "#FFD93D" : "#fff",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontWeight: 700, fontSize: "1rem",
          }}>
            {answers[i] ? t(`game.noteNames.${noteNaming}.${answers[i]}` as const) : ""}
          </Box>
        ))}
        {answers.length > 0 && !isWaiting && (
          <Button onClick={handleBackspace} variant="outlined" sx={{ minWidth: 48, minHeight: 48 }}
            aria-label="Backspace">⌫</Button>
        )}
      </Box>

      <NoteButtons
        clef={clef}
        noteNaming={noteNaming}
        onAnswer={handleAnswer}
        disabled={isWaiting || answers.length >= noteCount}
      />
    </Box>
  );
}
```

- [ ] **Step 4: Wire play screen in `frontend/src/features/game/index.tsx`**

Add import:
```tsx
import PlayScreen from "./play/PlayScreen";
```

Replace the `screen.name === "play"` branch:
```tsx
{screen.name === "play" && (
  <PlayScreen
    roundId={screen.roundId}
    initialTask={screen.firstTask}
    noteCount={screen.noteCount}
    difficulty={screen.difficulty}
    timeLimitMs={screen.timeLimitMs}
    onResult={(result) => {
      window.history.pushState(null, "", `/game/result/${screen.roundId}`);
      setScreen({ name: "result", roundId: screen.roundId, result, playerId: screen.playerId });
    }}
  />
)}
```

> Also update `GameSetup` to pass `noteCount`, `difficulty`, and `timeLimitMs` back in `onRoundStarted`.

The time limit map for `index.tsx`:
```ts
const TIME_LIMIT_MS: Record<string, number> = { easy: 13000, medium: 10000, hard: 7000 };
```

- [ ] **Step 5: Verify in browser** — play a full round: staff renders, note buttons respond, timer shrinks, feedback appears for 1s, next task loads. Tab away during a task — timer must freeze.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/game/play/ frontend/src/features/game/index.tsx
git commit -m "feat(game): play screen — staff, note buttons, timer, submit flow

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 9: Result screen

**Files:**
- Create: `frontend/src/features/game/result/ResultScreen.tsx`
- Modify: `frontend/src/features/game/index.tsx`

**Interfaces:**
- Consumes: `RoundResult` from `../play/PlayScreen` (inline type)
- Produces: score display, stars, XP gained, level-up notice, trophy notice, practice hint, "Play again" + "Change player" buttons

- [ ] **Step 1: Create `ResultScreen.tsx`**

```tsx
// frontend/src/features/game/result/ResultScreen.tsx
import { Box, Button, Chip, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

interface RoundResult {
  score: number; correct_count: number; is_win: boolean;
  xp_gained: number; level_up: boolean; new_trophy: number | null;
  practice_hint: string;
}

interface Props {
  result: RoundResult;
  onPlayAgain: () => void;
  onChangePlayer: () => void;
}

function Stars({ correct }: { correct: number }) {
  const filled = Math.round((correct / 7) * 3);
  return (
    <Box sx={{ display: "flex", justifyContent: "center", gap: 1, my: 1 }}>
      {[0, 1, 2].map((i) => (
        <Typography key={i} sx={{ fontSize: "2.5rem" }}>
          {i < filled ? "⭐" : "☆"}
        </Typography>
      ))}
    </Box>
  );
}

export default function ResultScreen({ result, onPlayAgain, onChangePlayer }: Props) {
  const { t } = useTranslation();

  return (
    <Box sx={{ p: 3, textAlign: "center", maxWidth: 400, mx: "auto" }}>
      <Typography variant="h3" sx={{ fontWeight: 800, mb: 1 }}>
        {result.is_win ? t("game.result.win") : t("game.result.lose")}
      </Typography>

      <Stars correct={result.correct_count} />

      <Typography variant="h5" sx={{ mb: 0.5 }}>
        {t("game.result.score", { score: result.score })}
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
        {t("game.result.correct", { count: result.correct_count })}
      </Typography>

      <Chip label={t("game.result.xpGained", { xp: result.xp_gained })}
        color="primary" sx={{ fontWeight: 700, fontSize: "1rem", mb: 1.5 }} />

      {result.level_up && (
        <Typography variant="h6" sx={{ color: "#FFD93D", mb: 1 }}>
          {t("game.result.levelUp")}
        </Typography>
      )}
      {result.new_trophy && (
        <Typography variant="h6" sx={{ mb: 1 }}>
          {t("game.result.newTrophy")}
        </Typography>
      )}

      <Typography variant="body2" color="text.secondary" sx={{ mb: 3, fontStyle: "italic" }}>
        {t("game.result.practiceHint_prefix")}{result.practice_hint}
      </Typography>

      <Box sx={{ display: "flex", gap: 2, justifyContent: "center" }}>
        <Button variant="contained" size="large" onClick={onPlayAgain} sx={{ minWidth: 140 }}>
          {t("game.result.playAgain")}
        </Button>
        <Button variant="outlined" size="large" onClick={onChangePlayer} sx={{ minWidth: 140 }}>
          {t("game.result.changePlayer")}
        </Button>
      </Box>
    </Box>
  );
}
```

- [ ] **Step 2: Wire result screen in `frontend/src/features/game/index.tsx`**

Add import and handle `screen.name === "result"`:
```tsx
import ResultScreen from "./result/ResultScreen";
// ...
{screen.name === "result" && (
  <ResultScreen
    result={screen.result}
    onPlayAgain={() => {
      window.history.pushState(null, "", `/game/setup/${screen.playerId}`);
      setScreen({ name: "setup", playerId: screen.playerId });
    }}
    onChangePlayer={() => {
      window.history.pushState(null, "", "/game");
      setScreen({ name: "players" });
    }}
  />
)}
```

- [ ] **Step 3: Verify in browser** — complete a round and see result screen with stars, XP chip, and buttons.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/game/result/ frontend/src/features/game/index.tsx
git commit -m "feat(game): result screen — score, stars, XP, level-up, trophy

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 10: Profile + admin screens

**Files:**
- Create: `frontend/src/features/game/profile/ProfileScreen.tsx`
- Create: `frontend/src/features/game/admin/AdminScreen.tsx`
- Create: `frontend/src/features/game/admin/AdminPlayerDetail.tsx`
- Modify: `frontend/src/features/game/index.tsx`

**Interfaces:**
- Consumes: `usePlayerStats`, `usePlayerConfusion`, `useSeasons`, `useResetSeason` from `../api/hooks`
- Produces: `/game/profile/:playerId` — stats by difficulty × note_count, trophy shelf, confusion hint; `/game/admin` — player list + season reset; `/game/admin/:playerId` — confusion heatmap

- [ ] **Step 1: Create `ProfileScreen.tsx`**

```tsx
// frontend/src/features/game/profile/ProfileScreen.tsx
import { Box, Chip, Divider, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { usePlayerStats } from "../api/hooks";

const TROPHY_ICONS: Record<number, string> = { 20: "🥉", 100: "🥈", 200: "🥇", 500: "🏆" };
const DIFFICULTIES = ["easy", "medium", "hard"];
const NOTE_COUNTS = ["1", "2", "3", "4"];

interface Props { playerId: number; trophies?: number[]; xp?: number; }

export default function ProfileScreen({ playerId, trophies = [], xp = 0 }: Props) {
  const { t } = useTranslation();
  const { data: stats = {} } = usePlayerStats(playerId);

  return (
    <Box sx={{ p: 3, maxWidth: 600, mx: "auto" }}>
      <Typography variant="h5" fontWeight={700} mb={2}>{t("game.profile.stats")}</Typography>

      {/* Stats matrix */}
      <Box sx={{ overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell />
              {NOTE_COUNTS.map((n) => (
                <TableCell key={n} align="center">{n} {n === "1" ? "нота" : "ноты"}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {DIFFICULTIES.map((d) => (
              <TableRow key={d}>
                <TableCell>{t(`game.difficulty.${d}`)}</TableCell>
                {NOTE_COUNTS.map((n) => {
                  const cell = stats[d]?.[n];
                  return (
                    <TableCell key={n} align="center">
                      {cell ? `${cell.rounds} / ${(cell.avg_score ?? 0).toFixed(1)}` : "—"}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Divider sx={{ my: 3 }} />

      <Typography variant="h5" fontWeight={700} mb={1}>{t("game.profile.trophies")}</Typography>
      {trophies.length === 0
        ? <Typography color="text.secondary">{t("game.profile.noTrophies")}</Typography>
        : <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap" }}>
            {trophies.map((th) => (
              <Chip key={th} label={`${TROPHY_ICONS[th] ?? "🏅"} ${th}`} variant="outlined" />
            ))}
          </Box>
      }
    </Box>
  );
}
```

- [ ] **Step 2: Create `AdminScreen.tsx`**

```tsx
// frontend/src/features/game/admin/AdminScreen.tsx
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField, Typography } from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { usePlayers, useResetSeason } from "../api/hooks";
import AvatarImage from "../setup/AvatarImage";

interface Props { onPlayerDetail: (playerId: number) => void; }

export default function AdminScreen({ onPlayerDetail }: Props) {
  const { t } = useTranslation();
  const { data: players = [] } = usePlayers();
  const [resetTarget, setResetTarget] = useState<number | "all" | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const resetSeason = useResetSeason();

  const handleReset = () => {
    if (confirmation !== "RESET") return;
    if (resetTarget === "all") {
      players.forEach((p) => resetSeason.mutate({ playerId: p.id, confirmation: "RESET" }));
    } else if (resetTarget !== null) {
      resetSeason.mutate({ playerId: resetTarget, confirmation: "RESET" });
    }
    setResetTarget(null);
    setConfirmation("");
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h5" fontWeight={700}>{t("game.admin.title")}</Typography>
        <Button variant="outlined" color="error" onClick={() => setResetTarget("all")}>
          {t("game.admin.resetAll")}
        </Button>
      </Box>

      {players.map((p) => (
        <Box key={p.id} sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1.5,
          p: 1.5, borderRadius: 3, background: "#fff", boxShadow: "0 2px 0 rgba(0,0,0,0.07)" }}>
          <AvatarImage animalId={p.avatar_animal ?? "unicorn"} size={48} />
          <Box sx={{ flex: 1 }}>
            <Typography fontWeight={600}>{p.name}</Typography>
            <Typography variant="caption" color="text.secondary">{p.xp} XP</Typography>
          </Box>
          <Button size="small" onClick={() => onPlayerDetail(p.id)}>Детали</Button>
          <Button size="small" color="warning" onClick={() => setResetTarget(p.id)}>
            {t("game.admin.resetSeason")}
          </Button>
        </Box>
      ))}

      <Dialog open={resetTarget !== null} onClose={() => setResetTarget(null)}>
        <DialogTitle>{t("game.admin.resetSeason")}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus value={confirmation}
            onChange={(e) => setConfirmation(e.target.value)}
            label={t("game.admin.confirmReset")}
            fullWidth sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetTarget(null)}>Отмена</Button>
          <Button onClick={handleReset} color="error" disabled={confirmation !== "RESET"}>
            {t("game.admin.resetSeason")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
```

- [ ] **Step 3: Create `AdminPlayerDetail.tsx`** — confusion heatmap

```tsx
// frontend/src/features/game/admin/AdminPlayerDetail.tsx
import { Box, Paper, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { usePlayerConfusion } from "../api/hooks";

const NOTE_NAMES = ["C", "D", "E", "F", "G", "A", "B"];

interface Props { playerId: number; }

export default function AdminPlayerDetail({ playerId }: Props) {
  const { t } = useTranslation();
  const { data } = usePlayerConfusion(playerId);

  if (!data) return null;
  const maxVal = Math.max(1, ...Object.values(data.heatmap).flatMap((row) => Object.values(row)));

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" fontWeight={700} mb={2}>{t("game.profile.confusion")}</Typography>

      {/* Top confusions */}
      {data.top_confusions.map((c) => (
        <Typography key={`${c.expected}-${c.given}`} sx={{ mb: 0.5 }}>
          {t(`game.noteNames.letters.${c.expected}`)} вместо {t(`game.noteNames.letters.${c.given}`)} ×{c.count}
        </Typography>
      ))}

      {/* 7×7 heatmap */}
      <Box sx={{ overflowX: "auto", mt: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Ожид. \ Введено</TableCell>
              {NOTE_NAMES.map((n) => <TableCell key={n} align="center">{n}</TableCell>)}
            </TableRow>
          </TableHead>
          <TableBody>
            {NOTE_NAMES.map((expected) => (
              <TableRow key={expected}>
                <TableCell>{expected}</TableCell>
                {NOTE_NAMES.map((given) => {
                  const val = data.heatmap[expected]?.[given] ?? 0;
                  const intensity = val / maxVal;
                  return (
                    <TableCell key={given} align="center"
                      sx={{ background: val > 0 ? `rgba(255,107,107,${0.1 + intensity * 0.7})` : undefined }}>
                      {val > 0 ? val : ""}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Box>
  );
}
```

- [ ] **Step 4: Wire profile + admin in `index.tsx`**

Add screen states and imports; handle paths `/game/profile/:id`, `/game/admin`, `/game/admin/:id`.

- [ ] **Step 5: Verify in browser** — navigate to `/game/admin` as a manager: player list renders, confusion heatmap shows numbers in cells (not color alone).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/game/profile/ frontend/src/features/game/admin/ frontend/src/features/game/index.tsx
git commit -m "feat(game): profile screen, admin player list, confusion heatmap

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
