import { expect, it, vi } from "vitest";
import { fetchHealth } from "./health";

it("requests the same-origin endpoint without caching", async () => {
  const fetch = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ status: "ok" }), {
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetch);
  expect(await fetchHealth(new AbortController().signal, 5000)).toEqual({
    status: "ok",
  });
  expect(fetch).toHaveBeenCalledWith(
    "/api/health",
    expect.objectContaining({
      cache: "no-store",
      signal: expect.any(AbortSignal),
    }),
  );
});

it.each([
  [new Response("unavailable", { status: 503 }), "SERVICE_UNAVAILABLE"],
  [new Response('{"status":"broken"}'), "INVALID_RESPONSE"],
  [new Response("<html>not JSON</html>"), "INVALID_RESPONSE"],
  [new Response("null"), "INVALID_RESPONSE"],
])(
  "rejects unsuccessful or malformed health responses",
  async (response, code) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
    await expect(
      fetchHealth(new AbortController().signal, 5000),
    ).rejects.toMatchObject({ code });
  },
);

it("reports network failure explicitly", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
  await expect(
    fetchHealth(new AbortController().signal, 5000),
  ).rejects.toMatchObject({
    code: "NETWORK_ERROR",
  });
});

it("aborts stalled requests and reports a timeout", async () => {
  vi.useFakeTimers();
  try {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, options: RequestInit) =>
          new Promise<Response>((_resolve, reject) => {
            options.signal?.addEventListener("abort", () =>
              reject(options.signal?.reason),
            );
          }),
      ),
    );
    const pending = expect(
      fetchHealth(new AbortController().signal, 10),
    ).rejects.toMatchObject({ code: "REQUEST_TIMEOUT" });
    await vi.advanceTimersByTimeAsync(10);
    await pending;
  } finally {
    vi.useRealTimers();
  }
});

it("does not fetch an already cancelled request", async () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  const controller = new AbortController();
  controller.abort();
  await expect(fetchHealth(controller.signal, 5000)).rejects.toBeDefined();
  expect(fetch).not.toHaveBeenCalled();
});

it("cancels an in-flight request when its caller aborts", async () => {
  const controller = new AbortController();
  vi.stubGlobal(
    "fetch",
    vi.fn(
      (_url: string, options: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          options.signal?.addEventListener("abort", () =>
            reject(options.signal?.reason),
          );
        }),
    ),
  );
  const pending = fetchHealth(controller.signal, 5000);
  controller.abort();
  await expect(pending).rejects.toBe(controller.signal.reason);
});
