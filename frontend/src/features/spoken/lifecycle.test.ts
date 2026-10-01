import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SpeechPlayer } from "./player";
import type { NoteEvent } from "./sequence";

const note: NoteEvent = {
  pitch: { step: "C", alter: 0, octave: 4 },
  beats: 1,
  noteIndices: [0],
};
class Context {
  static latest: Context;
  currentTime = 0;
  state = "running";
  destination = {};
  resume = vi.fn().mockResolvedValue(undefined);
  close = vi.fn().mockResolvedValue(undefined);
  decodeAudioData = vi.fn().mockResolvedValue({ duration: 0.2 });
  nodes: { start: ReturnType<typeof vi.fn>; stop: ReturnType<typeof vi.fn> }[] =
    [];
  constructor() {
    Context.latest = this;
  }
  createBufferSource() {
    const node = {
      buffer: null,
      playbackRate: { value: 1 },
      connect: vi.fn(),
      disconnect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
    };
    this.nodes.push(node);
    return node;
  }
}
beforeEach(() => {
  vi.stubGlobal("AudioContext", Context);
  vi.stubGlobal(
    "requestAnimationFrame",
    vi.fn(() => 1),
  );
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(new Uint8Array([1, 2, 3]), {
        headers: { "Content-Type": "audio/mp4" },
      }),
    ),
  );
});
afterEach(() => vi.unstubAllGlobals());

it("resumes synchronously, schedules only after loading, and stops every source", async () => {
  const position = vi.fn(),
    failed = vi.fn(),
    ready = vi.fn();
  const player = new SpeechPlayer(position, vi.fn(), failed);
  const pending = player.play(async () => [note], 72, "en", "letters", ready);
  expect(Context.latest.resume).toHaveBeenCalledTimes(1);
  await pending;
  expect(ready).toHaveBeenCalledTimes(1);
  expect(Context.latest.nodes[0].start).toHaveBeenCalledWith(0.05);
  player.stop();
  expect(Context.latest.nodes[0].stop).toHaveBeenCalledTimes(1);
  expect(Context.latest.close).toHaveBeenCalledTimes(1);
  expect(position).toHaveBeenLastCalledWith(null);
  expect(failed).not.toHaveBeenCalled();
});
it("stopping during authorization prevents late playback", async () => {
  let finish: (events: NoteEvent[]) => void = () => {};
  const load = new Promise<NoteEvent[]>((resolve) => {
    finish = resolve;
  });
  const ready = vi.fn(),
    failed = vi.fn();
  const player = new SpeechPlayer(vi.fn(), vi.fn(), failed);
  const pending = player.play(() => load, 72, "en", "letters", ready);
  await Promise.resolve();
  player.stop();
  finish([note]);
  await pending;
  expect(Context.latest.nodes).toHaveLength(0);
  expect(ready).not.toHaveBeenCalled();
  expect(failed).not.toHaveBeenCalled();
});
it("reports missing clips without emitting audio", async () => {
  vi.mocked(fetch).mockResolvedValue(new Response("", { status: 404 }));
  const failed = vi.fn();
  const player = new SpeechPlayer(vi.fn(), vi.fn(), failed);
  await player.play(async () => [note], 72, "ru", "solfege", vi.fn());
  expect(failed).toHaveBeenCalledWith(
    expect.objectContaining({ code: "SPOKEN_CLIPS_UNAVAILABLE" }),
  );
  expect(Context.latest.nodes).toHaveLength(0);
  expect(Context.latest.close).toHaveBeenCalled();
});
it("advances the highlighted note on the audio clock and closes after the final slot", async () => {
  const position = vi.fn(),
    ended = vi.fn();
  const player = new SpeechPlayer(position, ended, vi.fn());
  await player.play(async () => [note], 72, "en", "letters", vi.fn());
  Context.latest.currentTime = 0.1;
  vi.mocked(requestAnimationFrame).mock.calls.at(-1)?.[0](0);
  expect(position).toHaveBeenLastCalledWith(note);
  Context.latest.currentTime = 2;
  vi.mocked(requestAnimationFrame).mock.calls.at(-1)?.[0](0);
  expect(ended).toHaveBeenCalledTimes(1);
  expect(position).toHaveBeenLastCalledWith(null);
  expect(Context.latest.close).toHaveBeenCalledTimes(1);
});
it("cancels a late decoder result without scheduling sound", async () => {
  let finish: (value: { duration: number }) => void = () => {};
  const decode = new Promise<{ duration: number }>((resolve) => {
    finish = resolve;
  });
  const failed = vi.fn(),
    ready = vi.fn();
  const player = new SpeechPlayer(vi.fn(), vi.fn(), failed);
  const pending = player.play(async () => [note], 72, "en", "letters", ready);
  Context.latest.decodeAudioData.mockReturnValue(decode);
  await vi.waitFor(() =>
    expect(Context.latest.decodeAudioData).toHaveBeenCalled(),
  );
  player.stop();
  finish({ duration: 0.2 });
  await pending;
  expect(Context.latest.nodes).toHaveLength(0);
  expect(failed).not.toHaveBeenCalled();
  expect(ready).not.toHaveBeenCalled();
});
