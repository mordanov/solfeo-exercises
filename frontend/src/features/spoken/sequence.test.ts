import { expect, it } from "vitest";
import { parseSequence } from "./sequence";
import scale from "../../../../backend/tests/fixtures/omr/scale.musicxml?raw";
import rhythm from "../../../../backend/tests/fixtures/omr/rhythm.musicxml?raw";
import accidentals from "../../../../backend/tests/fixtures/omr/accidentals.musicxml?raw";

it("reads pitches, octaves and quarter-note durations", () => {
  const result = parseSequence(scale);
  expect(result.map((event) => event.pitch?.step).join("")).toBe("CDEFGABC");
  expect(result.map((event) => event.beats)).toEqual(Array(8).fill(1));
  expect(result[7].pitch?.octave).toBe(5);
});
it("preserves dotted durations and silence, and merges ties across measures", () => {
  const result = parseSequence(rhythm);
  expect(result.map((event) => event.beats)).toEqual([1.5, 0.5, 1, 2, 1, 2]);
  expect(result[2].pitch).toBeNull();
  expect(result[3].noteIndices).toEqual([3, 4]);
});
it("uses effective pitch alteration, including natural cancellation", () => {
  expect(parseSequence(accidentals).map((event) => event.pitch?.alter)).toEqual(
    [1, -1, 0, 0],
  );
});
it("applies divisions changes in order, including fractional beats", () => {
  const xml = `<score-partwise><part><measure><attributes><divisions>2</divisions></attributes>
  <note><rest/><duration>1</duration></note><attributes><divisions>3</divisions></attributes>
  <note><pitch><step>F</step><alter>2</alter><octave>5</octave></pitch><duration>1</duration></note>
  </measure></part></score-partwise>`;
  const events = parseSequence(xml);
  expect(events.map((event) => event.beats)).toEqual([0.5, 1 / 3]);
  expect(events[1].pitch?.alter).toBe(2);
});
it.each([
  "<invalid/>",
  scale.replace("<duration>2</duration>", "<duration>0</duration>"),
  scale.replace("<duration>2</duration>", "<duration>NaN</duration>"),
  scale.replace("<divisions>2</divisions>", "<divisions>0</divisions>"),
  scale.replace("<step>C</step>", "<step>X</step>"),
  scale.replace("<note>", "<note><chord/>"),
  scale.replace("<note>", "<note><grace/>"),
  scale.replace(
    "</measure>",
    "<backup><duration>2</duration></backup></measure>",
  ),
  scale.replace(
    "</measure>",
    '<barline><repeat direction="backward"/></barline></measure>',
  ),
  rhythm.replace('<tie type="stop"/>', ""),
  rhythm.replace('<tie type="start"/>', ""),
  scale.replace("</part>", "<measure/></part>"),
  scale.replace("<note>", "<note><rest/>"),
  scale.replace(
    "<divisions>2</divisions>",
    "<divisions>2</divisions><staves>2</staves>",
  ),
  scale.replace("</score-partwise>", "<part/></score-partwise>"),
  scale.replace("<note>", "<note><voice>2</voice>"),
  scale.replace(
    "</measure>",
    '<measure-style><measure-repeat type="start">1</measure-repeat></measure-style></measure>',
  ),
])("rejects unsupported or malformed notation explicitly", (xml) => {
  expect(() => parseSequence(xml)).toThrow();
});
