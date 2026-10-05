import { expect, it, vi } from "vitest";
import {
  ApiError,
  fetchMe,
  login,
  parseUser,
  saveSettings,
  saveAppearance,
} from "./auth";
import { defaultAppearance } from "../appearance";

const validUser = {
  id: 1,
  username: "student",
  first_name: "First",
  last_name: "Last",
  role: "student",
  is_active: true,
  is_emergency: false,
  must_change_password: false,
  ui_language: "en",
  note_naming: "letters",
  ...defaultAppearance,
};
it("parses only complete supported appearance preferences", () => {
  expect(parseUser(validUser)).toMatchObject(defaultAppearance);
  for (const changes of [
    { light_scheme: "#fff" },
    { dark_scheme: "unknown" },
    { ui_font: "external" },
    { ui_font_size: 17 },
    { ui_font_size: "20" },
    { ui_font: undefined },
  ])
    expect(() => parseUser({ ...validUser, ...changes })).toThrow(
      "INVALID_RESPONSE",
    );
});
it("accepts the game-only account role", () => {
  expect(parseUser({ ...validUser, role: "player" }).role).toBe("player");
});
it("saves appearance alone without overwriting language or naming", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify(validUser)));
  vi.stubGlobal("fetch", fetch);
  await saveAppearance("csrf", defaultAppearance);
  expect(fetch).toHaveBeenCalledWith(
    "/api/settings",
    expect.objectContaining({
      method: "PATCH",
      body: JSON.stringify(defaultAppearance),
      headers: expect.objectContaining({ "X-CSRF-Token": "csrf" }),
    }),
  );
});

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
