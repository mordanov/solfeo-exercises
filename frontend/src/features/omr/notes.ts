import { ApiError, type NoteNaming } from "../../api/auth";
import type { Language } from "../../configuration";

const syllables: Record<Language, Record<string, string>> = {
  en: { C: "do", D: "re", E: "mi", F: "fa", G: "sol", A: "la", B: "si" },
  es: { C: "do", D: "re", E: "mi", F: "fa", G: "sol", A: "la", B: "si" },
  ru: { C: "до", D: "ре", E: "ми", F: "фа", G: "соль", A: "ля", B: "си" },
};
const accidentals: Record<string, string> = {
  "-2": "𝄫",
  "-1": "♭",
  "0": "",
  "1": "♯",
  "2": "𝄪",
};

export function injectNoteNames(
  xml: string,
  naming: NoteNaming,
  language: Language,
): string {
  const document = new DOMParser().parseFromString(xml, "application/xml");
  if (
    document.querySelector("parsererror") ||
    document.documentElement.tagName !== "score-partwise"
  )
    throw new ApiError("OMR_INVALID_SCORE");
  for (const note of document.querySelectorAll("part > measure > note")) {
    const pitch = note.querySelector("pitch");
    if (!pitch) continue;
    const step = pitch.querySelector("step")?.textContent ?? "";
    const alter = pitch.querySelector("alter")?.textContent ?? "0";
    const name = naming === "letters" ? step : syllables[language][step];
    if (!syllables.en[step] || !name || accidentals[alter] === undefined)
      throw new ApiError("OMR_INVALID_SCORE");
    note.querySelectorAll("lyric").forEach((lyric) => lyric.remove());
    const lyric = document.createElement("lyric");
    lyric.setAttribute("number", "1");
    const text = document.createElement("text");
    text.textContent = name + accidentals[alter];
    lyric.append(text);
    note.append(lyric);
  }
  return new XMLSerializer().serializeToString(document);
}
