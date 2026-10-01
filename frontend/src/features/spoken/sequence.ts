import { ApiError } from "../../api/auth";
import { isStep, type Step } from "./vocabulary";

export type Pitch = { step: Step; alter: number; octave: number };
export type NoteEvent = {
  pitch: Pitch | null;
  beats: number;
  noteIndices: number[];
};

function invalid(): never {
  throw new ApiError("SPOKEN_UNSUPPORTED_SCORE");
}
function positive(value: string | null): number {
  if (value === null || !value.trim()) invalid();
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) invalid();
  return number;
}

export function parseSequence(xml: string): NoteEvent[] {
  if (xml.length > 5242880 || /<!ENTITY/i.test(xml)) invalid();
  const document = new DOMParser().parseFromString(xml, "application/xml");
  const root = document.documentElement;
  if (
    document.querySelector("parsererror") ||
    root.tagName !== "score-partwise"
  )
    invalid();
  const parts = root.querySelectorAll(":scope > part");
  if (
    parts.length !== 1 ||
    root.querySelector(
      "backup, forward, chord, grace, unpitched, repeat, ending, measure-repeat, beat-repeat, ornaments, transpose, time > senza-misura, sound[dacapo], sound[dalsegno], sound[tocoda]",
    )
  )
    invalid();
  let divisions = 0;
  let tied: NoteEvent | null = null;
  let index = 0;
  const events: NoteEvent[] = [];
  for (const measure of parts[0].querySelectorAll(":scope > measure")) {
    const before = index;
    const voices = new Set<string>();
    for (const note of measure.children) {
      if (note.tagName === "attributes") {
        const value = note.querySelector(":scope > divisions")?.textContent;
        if (value !== undefined) divisions = positive(value);
        const staves = note.querySelector(":scope > staves")?.textContent;
        if (staves && staves.trim() !== "1") invalid();
        continue;
      }
      if (note.tagName !== "note") continue;
      if (++index > 2000 || !divisions) invalid();
      voices.add(note.querySelector("voice")?.textContent?.trim() ?? "1");
      if (voices.size !== 1) invalid();
      const staff = note.querySelector("staff")?.textContent;
      if (staff && staff !== "1") invalid();
      const beats =
        positive(note.querySelector("duration")?.textContent ?? null) /
        divisions;
      if (!Number.isFinite(beats) || beats <= 0) invalid();
      const pitchElement = note.querySelector("pitch");
      let pitch: Pitch | null = null;
      if (pitchElement) {
        if (note.querySelector("rest")) invalid();
        const step = pitchElement.querySelector("step")?.textContent ?? "";
        const octaveText =
          pitchElement.querySelector("octave")?.textContent ?? "";
        const alterText =
          pitchElement.querySelector("alter")?.textContent ?? "0";
        const alter = Number(alterText);
        if (
          !isStep(step) ||
          !/^[0-9]$/.test(octaveText) ||
          !alterText.trim() ||
          !Number.isInteger(alter) ||
          Math.abs(alter) > 2
        )
          invalid();
        pitch = { step, octave: Number(octaveText), alter };
      } else if (!note.querySelector("rest")) invalid();
      const ties = [...note.querySelectorAll(":scope > tie")].map((tie) =>
        tie.getAttribute("type"),
      );
      if (
        ties.some((type) => type !== "start" && type !== "stop") ||
        new Set(ties).size !== ties.length
      )
        invalid();
      const start = ties.includes("start"),
        stop = ties.includes("stop");
      if ((start || stop) && !pitch) invalid();
      if (stop) {
        if (!tied || JSON.stringify(tied.pitch) !== JSON.stringify(pitch))
          invalid();
        tied.beats += beats;
        tied.noteIndices.push(index - 1);
        if (!start) tied = null;
      } else {
        if (tied) invalid();
        const event = { pitch, beats, noteIndices: [index - 1] };
        events.push(event);
        if (start) tied = event;
      }
    }
    if (index === before) invalid();
  }
  if (!events.length || tied) invalid();
  return events;
}
