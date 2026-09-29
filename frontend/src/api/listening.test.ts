import { expect, it, vi } from "vitest";
import {
  beaconListeningEvent,
  sendListeningEvent,
  type ListeningEvent,
} from "./listening";
import { dateBoundary, parseJournal } from "./journal";
const event: ListeningEvent = {
  session_id: "id",
  exercise_id: 1,
  audio_id: "audio",
  mode: "sequential",
  csrf_token: "csrf",
  event: "end",
  position_seconds: 2,
};
it("uses same-origin beacon JSON with a session-bound token", () => {
  const sendBeacon = vi.fn().mockReturnValue(true);
  vi.stubGlobal("navigator", { sendBeacon });
  beaconListeningEvent(event, vi.fn());
  expect(sendBeacon).toHaveBeenCalledWith(
    "/api/listening/events",
    expect.any(Blob),
  );
});
it("uses keepalive when the browser rejects the beacon queue", async () => {
  vi.stubGlobal("navigator", { sendBeacon: vi.fn().mockReturnValue(false) });
  const fetch = vi
    .fn()
    .mockResolvedValue(
      new Response(
        JSON.stringify({ session_id: "id", completed: false, ended_at: null }),
      ),
    );
  vi.stubGlobal("fetch", fetch);
  beaconListeningEvent(event, vi.fn());
  await vi.waitFor(() => expect(fetch).toHaveBeenCalled());
  expect(fetch.mock.calls[0][1]).toMatchObject({
    keepalive: true,
    credentials: "same-origin",
    body: JSON.stringify(event),
  });
});
it("validates event acknowledgments and journal shapes", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ session_id: "other" }))),
  );
  await expect(sendListeningEvent(event)).rejects.toMatchObject({
    code: "INVALID_RESPONSE",
  });
  expect(() => parseJournal({ id: 1 })).toThrow("INVALID_RESPONSE");
});
it("converts inclusive local date filters into UTC boundaries", () => {
  expect(dateBoundary("2026-09-29")).toBe(new Date(2026, 8, 29).toISOString());
  expect(dateBoundary("2026-09-29", true)).toBe(
    new Date(2026, 8, 30).toISOString(),
  );
  expect(dateBoundary("")).toBeUndefined();
});
