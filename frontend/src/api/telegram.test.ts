import { describe, expect, it, vi } from "vitest";
import { applyImport, createCode, listImports, status } from "./telegram";

describe("Telegram API validation", () => {
  it("creates codes with CSRF protection and no secret in the URL", async () => {
    const fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          code: "private-code",
          expires_at: "2026-09-29T21:00:00Z",
        }),
      ),
    );
    vi.stubGlobal("fetch", fetch);
    expect((await createCode("csrf")).code).toBe("private-code");
    expect(fetch).toHaveBeenCalledWith(
      "/api/telegram/link",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-CSRF-Token": "csrf" }),
      }),
    );
  });
  it("rejects malformed lists, bot identities, and application results", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(
        async () =>
          new Response(
            JSON.stringify({
              imports: [{}],
              total: 1,
              exercise_id: -1,
              linked: true,
              available: true,
              bot_username: "bad/identity",
            }),
          ),
      ),
    );
    await expect(listImports(0)).rejects.toThrow("INVALID_RESPONSE");
    await expect(status()).rejects.toThrow("INVALID_RESPONSE");
    await expect(
      applyImport("csrf", 1, {
        title: "Title",
        description: "",
        exercise_id: null,
      }),
    ).rejects.toThrow("INVALID_RESPONSE");
  });
});
