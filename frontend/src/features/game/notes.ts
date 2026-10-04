import type { TFunction } from "i18next";
import type { NoteNaming } from "../../api/auth";
import type { Note } from "./api/hooks";

export const GAME_NOTES: readonly Note[] = [4, 5].flatMap((octave) =>
  [..."CDEFGAB"].map((name) => ({ name, octave })),
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
  return t("game.noteLabel", {
    name: t(`game.noteNames.${naming}.${note.name}`),
    octave: note.octave,
  });
}
