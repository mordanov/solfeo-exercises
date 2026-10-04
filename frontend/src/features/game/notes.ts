import type { TFunction } from "i18next";
import type { NoteNaming } from "../../api/auth";
import type { Note } from "./api/hooks";

export const NOTE_NAMES = ["C", "D", "E", "F", "G", "A", "B"] as const;
export const PIANO_NOTES: readonly Note[] = [2, 3, 4, 5].flatMap((octave) =>
  NOTE_NAMES.map((name) => ({ name, octave })),
);
export const DIFFICULTIES = [
  { name: "easy", timeMs: 13000 },
  { name: "medium", timeMs: 10000 },
  { name: "hard", timeMs: 7000 },
] as const;
export interface GameOptions {
  showSoundHint: boolean;
  showCorrectAnswer: boolean;
}
export const DEFAULT_GAME_OPTIONS: GameOptions = {
  showSoundHint: true,
  showCorrectAnswer: false,
};

export function noteLabel(
  note: Note,
  naming: NoteNaming,
  t: TFunction,
): string {
  return t(`game.noteNames.${naming}.${note.name}`);
}
