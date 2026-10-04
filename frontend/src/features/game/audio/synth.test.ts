import { beforeEach, expect, it, vi } from "vitest";

const { load } = vi.hoisted(() => ({ load: vi.fn() }));
vi.mock("soundfont-player", () => ({ default: { instrument: load } }));

class Context {
  static instances: Context[] = [];
  state = "running";
  currentTime = 10;
  resume = vi.fn(async () => {
    this.state = "running";
  });
  constructor() {
    Context.instances.push(this);
  }
}
class Source extends EventTarget {
  stop = vi.fn();
}
const nodes: { source: Source }[] = [];
const play = vi.fn<
  (key: string, when: number, options: object) => { source: Source }
>(() => {
  const node = { source: new Source() };
  nodes.push(node);
  return node;
});
const buffers = Object.fromEntries(
  [2, 3, 4, 5].flatMap((octave) =>
    [..."CDEFGAB"].flatMap((name) =>
      [4, 8, 12, 16].map((layer) => [
        `${name}${octave}-v${layer}`,
        { duration: 2.5 },
      ]),
    ),
  ),
);

beforeEach(() => {
  vi.resetModules();
  localStorage.clear();
  Context.instances = [];
  nodes.length = 0;
  play.mockClear();
  load.mockReset().mockResolvedValue({ buffers, play });
  vi.stubGlobal("AudioContext", Context);
});
async function scheduled(count: number) {
  await vi.waitFor(() => expect(nodes).toHaveLength(count));
}
it("loads one local piano asset once with no external soundfont fallback", async () => {
  const { preparePiano, PIANO_ASSET } = await import("./synth");
  await Promise.all([preparePiano(), preparePiano()]);
  await preparePiano();
  expect(load).toHaveBeenCalledOnce();
  const options = load.mock.calls[0][2];
  expect(options.nameToUrl()).toBe(PIANO_ASSET);
  expect(options.map("C4-v8")).toBe("C4-v8");
});
it("schedules exact octave-specific samples with unchanged sample pitch", async () => {
  const { playNotes } = await import("./synth");
  const finished = playNotes(
    [
      { name: "E", octave: 2 },
      { name: "B", octave: 5 },
    ],
    new AbortController().signal,
  );
  await scheduled(2);
  expect(play.mock.calls).toEqual([
    ["E2-v8", 10, { duration: 0.5, gain: 0.8 }],
    ["B5-v8", 10.75, { duration: 0.5, gain: 0.8 }],
  ]);
  nodes[1].source.dispatchEvent(new Event("ended"));
  await finished;
});
it("selects actual recorded velocity layers without changing pitch", async () => {
  const { sampleKey } = await import("./synth");
  for (const [velocity, layer] of [
    [1, 4],
    [43, 4],
    [44, 8],
    [64, 8],
    [65, 12],
    [96, 12],
    [97, 16],
    [127, 16],
  ]) {
    expect(sampleKey({ name: "A", octave: 4 }, velocity)).toBe(`A4-v${layer}`);
  }
  for (const velocity of [0, 128, NaN, 1.5]) {
    expect(() => sampleKey({ name: "A", octave: 4 }, velocity)).toThrow();
  }
});
it("stops both current and scheduled samples on cancellation", async () => {
  const { playNotes } = await import("./synth");
  const controller = new AbortController();
  const finished = playNotes(
    [
      { name: "C", octave: 4 },
      { name: "G", octave: 5 },
    ],
    controller.signal,
  );
  await scheduled(2);
  controller.abort();
  await finished;
  nodes.forEach((node) => expect(node.source.stop).toHaveBeenCalledOnce());
});
it("never schedules cancelled audio after a pending asset load", async () => {
  let ready: (value: object) => void = () => {};
  load.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        ready = resolve;
      }),
  );
  const { playNotes } = await import("./synth");
  const controller = new AbortController();
  const finished = playNotes([{ name: "C", octave: 4 }], controller.signal);
  controller.abort();
  ready({ buffers, play });
  await finished;
  expect(play).not.toHaveBeenCalled();
});
it("resumes interrupted audio before scheduling on its resumed clock", async () => {
  const { preparePiano, playNotes } = await import("./synth");
  await preparePiano();
  const context = Context.instances[0];
  context.state = "interrupted";
  context.resume.mockImplementation(async () => {
    context.state = "running";
    context.currentTime = 12;
  });
  const finished = playNotes(
    [{ name: "A", octave: 4 }],
    new AbortController().signal,
  );
  await scheduled(1);
  expect(context.resume).toHaveBeenCalledOnce();
  expect(play).toHaveBeenCalledWith("A4-v8", 12, expect.any(Object));
  nodes[0].source.dispatchEvent(new Event("ended"));
  await finished;
});
it("reports loading failures and retries rather than switching to an oscillator", async () => {
  load.mockRejectedValueOnce(new Error("Asset unavailable"));
  const { preparePiano } = await import("./synth");
  await expect(preparePiano()).rejects.toThrow("Asset unavailable");
  await preparePiano();
  expect(load).toHaveBeenCalledTimes(2);
});
it("rejects incomplete assets", async () => {
  load.mockResolvedValueOnce({ buffers: {}, play });
  const { preparePiano } = await import("./synth");
  await expect(preparePiano()).rejects.toThrow("GAME_AUDIO_MISSING_SAMPLE");
});
it("rejects invalid, out-of-range, empty and muted playback explicitly", async () => {
  const { playNotes } = await import("./synth");
  for (const notes of [
    [],
    [{ name: "C", octave: 1 }],
    [{ name: "C", octave: 6 }],
    [{ name: "H", octave: 4 }],
  ]) {
    await expect(
      playNotes(notes, new AbortController().signal),
    ).rejects.toThrow();
  }
  localStorage.setItem("game_muted", "1");
  await expect(
    playNotes([{ name: "C", octave: 4 }], new AbortController().signal),
  ).rejects.toThrow("GAME_AUDIO_MUTED");
  expect(load).not.toHaveBeenCalled();
});
it("rejects scheduling failures instead of resolving cancellation as success", async () => {
  play.mockImplementationOnce(() => {
    throw new Error("Scheduling failed");
  });
  const { playNotes } = await import("./synth");
  await expect(
    playNotes([{ name: "C", octave: 4 }], new AbortController().signal),
  ).rejects.toThrow("Scheduling failed");
});
