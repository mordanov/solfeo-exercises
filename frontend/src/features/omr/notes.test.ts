import { describe, expect, it } from "vitest";
import { injectNoteNames } from "./notes";

const score = `<score-partwise><part id="P1"><measure number="1">
<note><pitch><step>C</step><alter>1</alter><octave>4</octave></pitch><duration>1</duration></note>
<note><rest/><duration>1</duration></note>
<note><pitch><step>B</step><alter>-1</alter><octave>4</octave></pitch><duration>2</duration><lyric><text>old</text></lyric></note>
</measure></part></score-partwise>`;

describe("localized note lyrics", () => {
  it.each([
    ["en", "letters", ["C♯", "B♭"]],
    ["es", "solfege", ["do♯", "si♭"]],
    ["ru", "solfege", ["до♯", "си♭"]],
  ] as const)("uses %s %s and skips rests", (language, naming, expected) => {
    const xml = new DOMParser().parseFromString(
      injectNoteNames(score, naming, language),
      "text/xml",
    );
    expect(
      [...xml.querySelectorAll("lyric text")].map((node) => node.textContent),
    ).toEqual(expected);
    expect(
      xml.querySelector("rest")?.parentElement?.querySelector("lyric"),
    ).toBeNull();
  });
  it("does not duplicate labels on repeated injection", () => {
    expect(
      injectNoteNames(injectNoteNames(score, "letters", "en"), "letters", "en"),
    ).toBe(injectNoteNames(score, "letters", "en"));
  });
  it("rejects invalid XML instead of silently rendering nothing", () => {
    expect(() => injectNoteNames("<broken>", "letters", "en")).toThrow();
  });
});
