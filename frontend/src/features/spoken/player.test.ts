import { expect, it } from "vitest";
import { planPlayback } from "./player";
import { readSpokenConfiguration } from "../../configuration";
import type { NoteEvent } from "./sequence";

const config = readSpokenConfiguration();
const events: NoteEvent[] = [
  { pitch: { step: "C", alter: 1, octave: 4 }, beats: 1, noteIndices: [0] },
  { pitch: null, beats: 1, noteIndices: [1] },
  { pitch: { step: "D", alter: 0, octave: 4 }, beats: 4, noteIndices: [2] },
];
const durations = new Map([
  ["/solfege/en/letters/C.m4a", 0.3],
  ["/solfege/en/letters/sharp.m4a", 0.2],
  ["/solfege/en/letters/D.m4a", 0.4],
]);
it("fits name and accidental inside the beat, preserves rest and long-note silence", () => {
  const plan = planPlayback(events, durations, 60, "en", "letters", config);
  expect(plan.total).toBe(6);
  [0, 0.3, 2].forEach((start, index) =>
    expect(plan.clips[index].start).toBeCloseTo(start),
  );
  expect(
    plan.clips.every((clip) => clip.rate >= 1 && clip.rate <= config.maxRate),
  ).toBe(true);
  expect(plan.markers.map((marker) => marker.start)).toEqual([0, 1, 2]);
  // A long note plays the word at its natural pitch; silence fills the rest.
  expect(plan.clips[2].duration).toBeCloseTo(0.4);
});
it("refuses to truncate a word or overlap the next beat", () => {
  expect(() =>
    planPlayback(
      [{ ...events[0], beats: 0.1 }],
      durations,
      160,
      "en",
      "letters",
      config,
    ),
  ).toThrow("SPOKEN_TEMPO_TOO_FAST");
});
it("rejects missing clips, out-of-range tempo and excessive total duration", () => {
  expect(() =>
    planPlayback(events, new Map(), 72, "en", "letters", config),
  ).toThrow("SPOKEN_CLIPS_UNAVAILABLE");
  expect(() =>
    planPlayback(events, durations, 0, "en", "letters", config),
  ).toThrow();
  expect(() =>
    planPlayback(events, durations, 60, "en", "letters", {
      ...config,
      maxSeconds: 1,
    }),
  ).toThrow();
});
it("validates public playback configuration", () => {
  expect(config.defaultBpm).toBe(72);
  expect(() => readSpokenConfiguration('{"defaultBpm":0}')).toThrow();
  expect(() =>
    readSpokenConfiguration(JSON.stringify({ ...config, maxRate: 0.5 })),
  ).toThrow();
});
