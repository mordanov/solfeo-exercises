import { afterEach, expect, it, vi } from "vitest";
import { ListeningTracker } from "./tracker";
import * as api from "../../api/listening";

vi.mock("../../api/listening");
afterEach(() => {
  vi.useRealTimers();
  vi.resetAllMocks();
});
const fixture = {
  exercise_id: 1,
  audio_id: "audio",
  mode: "sequential" as const,
  csrf_token: "csrf",
};

it("starts once, heartbeats only while playing and retains the session across pause", async () => {
  vi.useFakeTimers();
  vi.mocked(api.sendListeningEvent).mockResolvedValue();
  let position = 0;
  const tracker = new ListeningTracker(fixture, 20, () => position, vi.fn());
  tracker.play();
  await vi.advanceTimersByTimeAsync(0);
  const identifier = vi.mocked(api.sendListeningEvent).mock.calls[0][0]
    .session_id;
  position = 5;
  await vi.advanceTimersByTimeAsync(5000);
  tracker.pause();
  await vi.advanceTimersByTimeAsync(0);
  const calls = vi.mocked(api.sendListeningEvent).mock.calls.length;
  await vi.advanceTimersByTimeAsync(10000);
  expect(api.sendListeningEvent).toHaveBeenCalledTimes(calls);
  tracker.play();
  await tracker.finish();
  const events = vi
    .mocked(api.sendListeningEvent)
    .mock.calls.map(([value]) => value);
  expect(events.filter((value) => value.event === "start")).toHaveLength(1);
  expect(events.every((value) => value.session_id === identifier)).toBe(true);
  expect(events.at(-1)?.event).toBe("end");
});

it("reports 90 percent immediately, ends naturally, and creates a new replay session", async () => {
  vi.mocked(api.sendListeningEvent).mockResolvedValue();
  let position = 0;
  const tracker = new ListeningTracker(fixture, 10, () => position, vi.fn());
  tracker.play();
  position = 9;
  tracker.update();
  await tracker.finish(true);
  const events = vi
    .mocked(api.sendListeningEvent)
    .mock.calls.map(([value]) => value);
  expect(
    events.some(
      (value) => value.event === "heartbeat" && value.position_seconds === 9,
    ),
  ).toBe(true);
  expect(events.at(-1)?.event).toBe("ended");
  position = 0;
  tracker.play();
  await tracker.finish();
  expect(
    vi.mocked(api.sendListeningEvent).mock.calls.at(-1)?.[0].session_id,
  ).not.toBe(events[0].session_id);
});

it("sends a complete terminal beacon and avoids duplicate end events", async () => {
  vi.mocked(api.sendListeningEvent).mockResolvedValue();
  const tracker = new ListeningTracker(fixture, 20, () => 4, vi.fn());
  tracker.play();
  tracker.leave();
  tracker.leave();
  expect(api.beaconListeningEvent).toHaveBeenCalledOnce();
  expect(api.beaconListeningEvent).toHaveBeenCalledWith(
    expect.objectContaining({
      ...fixture,
      event: "end",
      position_seconds: 4,
    }),
    expect.any(Function),
  );
  await tracker.finish();
});

it("surfaces delivery failures and retries the same session on resumed playback", async () => {
  vi.mocked(api.sendListeningEvent)
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValue();
  const failed = vi.fn();
  const tracker = new ListeningTracker(fixture, 20, () => 0, failed);
  tracker.play();
  await vi.waitFor(() => expect(failed).toHaveBeenCalled());
  tracker.pause();
  tracker.play();
  await tracker.finish();
});
