import type { NoteNaming } from "../../api/auth";
import type { Language } from "../../configuration";
import vocabulary from "./vocabulary.json";

export type Step = keyof typeof vocabulary.en.solfege;
export function isStep(value: string): value is Step {
  return Object.hasOwn(vocabulary.en.solfege, value);
}
export function noteName(step: Step, language: Language, naming: NoteNaming) {
  return naming === "letters" ? step : vocabulary[language].solfege[step];
}
export function clipPaths(
  step: Step,
  alter: number,
  language: Language,
  naming: NoteNaming,
): string[] {
  const root = `/solfege/${language}/${naming}/`;
  const suffix = (
    {
      "-2": "double-flat",
      "-1": "flat",
      "1": "sharp",
      "2": "double-sharp",
    } as Record<string, string>
  )[alter];
  return [root + step + ".m4a", ...(suffix ? [root + suffix + ".m4a"] : [])];
}
