import { ApiError, type NoteNaming } from "../../api/auth";
import type { Language } from "../../configuration";
import { isStep, noteName } from "../spoken/vocabulary";
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
    if (!isStep(step) || accidentals[alter] === undefined)
      throw new ApiError("OMR_INVALID_SCORE");
    const name = noteName(step, language, naming);
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
