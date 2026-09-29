import { expect, it, vi } from "vitest";
import { ApiError, fetchMe, login, parseUser, saveSettings } from "./auth";

it("distinguishes expired sessions from unavailable servers", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValueOnce(
        new Response('{"error":"AUTH_REQUIRED"}', { status: 401 }),
      )
      .mockResolvedValueOnce(new Response("unavailable", { status: 503 })),
  );
  expect(await fetchMe()).toBeNull();
  await expect(fetchMe()).rejects.toMatchObject({
    code: "SERVICE_UNAVAILABLE",
  });
});

it("rejects a malformed successful login response", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response('{"user":{"role":"manager"}}')),
  );
  await expect(login("user", "private")).rejects.toMatchObject({
    code: "INVALID_RESPONSE",
  });
});

it("never accepts an unknown role or naming scheme", () => {
  expect(() => parseUser({ id: 1, role: "superuser" })).toThrow(ApiError);
  expect(() => parseUser(null)).toThrow(ApiError);
});

it("clears the authenticated view when a protected mutation loses authorization", async () => {
  const expired = vi.fn();
  window.addEventListener("solfeo:unauthorized", expired);
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response('{"error":"AUTH_REQUIRED"}', { status: 401 }),
      ),
  );
  try {
    await expect(saveSettings("csrf", "en", "letters")).rejects.toMatchObject({
      code: "AUTH_REQUIRED",
    });
    expect(expired).toHaveBeenCalledOnce();
  } finally {
    window.removeEventListener("solfeo:unauthorized", expired);
  }
});

it("aborts session lookups instead of hanging", async () => {
  const abort = new AbortController();
  abort.abort(new DOMException("Cancelled", "AbortError"));
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  await expect(fetchMe(abort.signal)).rejects.toMatchObject({
    name: "AbortError",
  });
  expect(fetch).not.toHaveBeenCalled();
});
