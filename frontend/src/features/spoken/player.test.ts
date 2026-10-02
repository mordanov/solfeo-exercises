import { expect, it } from "vitest";
import { planPlayback, tempoRange, chooseTempo } from "./player";
import { readSpokenConfiguration } from "../../configuration";
import type { NoteEvent } from "./sequence";
import timings from "../../../public/solfege/timings.json";

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
it("chooses a tempo that fits short notes and their accidental clips", () => {
  const short = [{ ...events[0], beats: 0.125 }];
  const range = tempoRange(short, durations, "en", "letters", config);
  expect(range.max).toBe(22);
  expect(range.min).toBe(1);
  const bpm = chooseTempo(72, range);
  expect(bpm).toBe(22);
  expect(() =>
    planPlayback(short, durations, bpm, "en", "letters", {
      ...config,
      minBpm: range.min,
    }),
  ).not.toThrow();
});
it("preserves a slower saved tempo and accounts for rests and the total duration limit", () => {
  const range = tempoRange(events, durations, "en", "letters", config);
  expect(chooseTempo(60, range)).toBe(60);
  expect(() => chooseTempo(NaN, range)).toThrow("SPOKEN_INVALID_TEMPO");
  expect(() =>
    tempoRange(events, durations, "en", "letters", {
      ...config,
      maxSeconds: 0.01,
    }),
  ).toThrow("SPOKEN_TOO_LONG");
  expect(() => tempoRange(events, new Map(), "en", "letters", config)).toThrow(
    "SPOKEN_CLIPS_UNAVAILABLE",
  );
});
it("fits every committed language, naming, pitch and accidental across short and long notes", () => {
  const clips = new Map(Object.entries(timings));
  expect(clips.size).toBe(66);
  let checked = 0;
  for (const language of ["en", "ru", "es"] as const)
    for (const naming of ["letters", "solfege"] as const)
      for (const step of ["C", "D", "E", "F", "G", "A", "B"] as const)
        for (const alter of [-2, -1, 0, 1, 2])
          for (const beats of [0.0625, 0.125, 0.25, 0.5, 1, 2, 4]) {
            const sequence = [
              { pitch: { step, alter, octave: 4 }, beats, noteIndices: [0] },
            ];
            const range = tempoRange(sequence, clips, language, naming);
            const bpm = chooseTempo(config.defaultBpm, range);
            const plan = planPlayback(sequence, clips, bpm, language, naming, {
              ...config,
              minBpm: range.min,
            });
            expect(
              plan.clips.every(
                (clip) => clip.rate >= 1 && clip.rate <= config.maxRate,
              ),
            ).toBe(true);
            const last = plan.clips.at(-1);
            expect(last).toBeDefined();
            expect(
              (last?.start ?? 0) + (last?.duration ?? 0),
            ).toBeLessThanOrEqual(plan.total + 1e-9);
            checked++;
          }
  expect(checked).toBe(1470);
});
