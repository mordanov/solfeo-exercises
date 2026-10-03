import { beforeEach, expect, it, vi } from "vitest";

class Oscillator {
  type = "";
  frequency = { value: 0 };
  onended: (() => void) | null = null;
  connect = vi.fn();
  disconnect = vi.fn();
  start = vi.fn();
  stop = vi.fn();
}
class Gain {
  gain = {
    setValueAtTime: vi.fn(),
    exponentialRampToValueAtTime: vi.fn(),
  };
  connect = vi.fn();
  disconnect = vi.fn();
}
class Context {
  static instances: Context[] = [];
  state = "running";
  currentTime = 10;
  destination = {};
  oscillators: Oscillator[] = [];
  gains: Gain[] = [];
  resume = vi.fn(async () => {
    this.state = "running";
  });
  createOscillator = vi.fn(() => {
    const oscillator = new Oscillator();
    this.oscillators.push(oscillator);
    return oscillator;
  });
  createGain = vi.fn(() => {
    const gain = new Gain();
    this.gains.push(gain);
    return gain;
  });
  constructor() {
    Context.instances.push(this);
  }
}

beforeEach(() => {
  vi.resetModules();
  localStorage.clear();
  Context.instances = [];
  vi.stubGlobal("AudioContext", Context);
});

it("plays all displayed pitches and octaves in order without overlap", async () => {
  const { playNotes } = await import("./synth");
  const finished = playNotes(
    [
      { name: "C", octave: 4 },
      { name: "G", octave: 4 },
      { name: "A", octave: 5 },
      { name: "F", octave: 3 },
    ],
    new AbortController().signal,
  );
  const context = Context.instances[0];
  expect(context.oscillators).toHaveLength(4);
  [261.625565, 391.995436, 880, 174.614116].forEach((frequency, index) => {
    const oscillator = context.oscillators[index];
    expect(oscillator.frequency.value).toBeCloseTo(frequency, 4);
    expect(oscillator.type).toBe("triangle");
    expect(oscillator.start).toHaveBeenCalledWith(10 + index * 0.45);
    expect(oscillator.stop).toHaveBeenCalledWith(10 + index * 0.45 + 0.3);
    expect(context.gains[index].gain.setValueAtTime).toHaveBeenCalledWith(
      0.35,
      10 + index * 0.45,
    );
  });
  context.oscillators[3].onended?.();
  await finished;
  expect(
    context.oscillators.every(
      (oscillator) => oscillator.disconnect.mock.calls.length === 1,
    ),
  ).toBe(true);
  expect(
    context.gains.every((gain) => gain.disconnect.mock.calls.length === 1),
  ).toBe(true);
});

it("stops current and future notes when cancelled", async () => {
  const { playNotes } = await import("./synth");
  const controller = new AbortController();
  const finished = playNotes(
    [
      { name: "C", octave: 2 },
      { name: "B", octave: 3 },
    ],
    controller.signal,
  );
  controller.abort();
  await finished;
  for (const oscillator of Context.instances[0].oscillators) {
    expect(oscillator.stop).toHaveBeenLastCalledWith();
    expect(oscillator.disconnect).toHaveBeenCalledOnce();
    expect(oscillator.onended).toBeNull();
  }
});

it("resumes suspended Safari audio and schedules against its resumed clock", async () => {
  const { playNotes, unlockAudio } = await import("./synth");
  unlockAudio();
  const context = Context.instances[0];
  context.state = "suspended";
  context.resume.mockImplementation(async () => {
    context.state = "running";
    context.currentTime = 12;
  });
  const finished = playNotes(
    [{ name: "A", octave: 4 }],
    new AbortController().signal,
  );
  await Promise.resolve();
  expect(context.resume).toHaveBeenCalledTimes(2);
  expect(context.oscillators[0].start).toHaveBeenCalledWith(12);
  context.oscillators[0].onended?.();
  await finished;
});

it("does not schedule audio after cancellation during resume", async () => {
  const { playNotes, unlockAudio } = await import("./synth");
  unlockAudio();
  const context = Context.instances[0];
  context.state = "suspended";
  let resume: () => void = () => {};
  context.resume.mockImplementation(
    () =>
      new Promise<void>((resolve) => {
        resume = resolve;
      }),
  );
  const controller = new AbortController();
  const finished = playNotes([{ name: "C", octave: 4 }], controller.signal);
  controller.abort();
  resume();
  await finished;
  expect(context.oscillators).toHaveLength(0);
});

it("resumes interrupted audio and reports a rejected browser resume", async () => {
  const { playNotes, unlockAudio } = await import("./synth");
  unlockAudio();
  const context = Context.instances[0];
  context.state = "interrupted";
  context.resume.mockRejectedValueOnce(new Error("Resume blocked"));
  await expect(
    playNotes([{ name: "A", octave: 4 }], new AbortController().signal),
  ).rejects.toThrow("Resume blocked");
  expect(context.oscillators).toHaveLength(0);
  const finished = playNotes(
    [{ name: "A", octave: 4 }],
    new AbortController().signal,
  );
  await Promise.resolve();
  expect(context.oscillators).toHaveLength(1);
  context.oscillators[0].onended?.();
  await finished;
});

it("reports unavailable Web Audio", async () => {
  const { playNotes } = await import("./synth");
  vi.stubGlobal("AudioContext", undefined);
  await expect(
    playNotes([{ name: "A", octave: 4 }], new AbortController().signal),
  ).rejects.toThrow();
});

it("cleans up allocated sources and propagates scheduling errors", async () => {
  const { playNotes, unlockAudio } = await import("./synth");
  unlockAudio();
  const context = Context.instances[0];
  context.createOscillator
    .mockImplementationOnce(() => {
      const oscillator = new Oscillator();
      context.oscillators.push(oscillator);
      return oscillator;
    })
    .mockImplementationOnce(() => {
      throw new Error("Audio unavailable");
    });
  await expect(
    playNotes(
      [
        { name: "C", octave: 4 },
        { name: "D", octave: 4 },
      ],
      new AbortController().signal,
    ),
  ).rejects.toThrow("Audio unavailable");
  expect(context.oscillators[0].stop).toHaveBeenLastCalledWith();
  expect(context.oscillators[0].disconnect).toHaveBeenCalledOnce();
});

it("reports mute and invalid pitches instead of pretending to play", async () => {
  const { playNotes } = await import("./synth");
  localStorage.setItem("game_muted", "1");
  await expect(
    playNotes([{ name: "A", octave: 4 }], new AbortController().signal),
  ).rejects.toThrow();
  localStorage.clear();
  for (const note of [
    { name: "H", octave: 4 },
    { name: "C", octave: NaN },
  ]) {
    await expect(
      playNotes([note], new AbortController().signal),
    ).rejects.toThrow();
  }
  expect(Context.instances).toHaveLength(0);
});

it("creates no audio for a cancelled or empty sequence", async () => {
  const { playNotes } = await import("./synth");
  const controller = new AbortController();
  controller.abort();
  await playNotes([{ name: "C", octave: 4 }], controller.signal);
  await expect(playNotes([], new AbortController().signal)).rejects.toThrow();
  expect(Context.instances).toHaveLength(0);
});
