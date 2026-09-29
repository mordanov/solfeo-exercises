import { describe, expect, it, vi } from "vitest";
import { handleShare, isShareRequest } from "./share";
import { saveAttempt } from "./storage";

vi.mock("./storage", () => ({
  saveShare: vi.fn(),
  saveAttempt: vi.fn().mockResolvedValue(undefined),
}));

const origin = "https://solfeo.example";

function request(files: File[]): Request {
  const body = new FormData();
  for (const file of files) body.append("audio", file);
  return new Request(`${origin}/prototype-share/receive`, {
    method: "POST",
    body,
  });
}

function audio(name = "voice.opus", type = "audio/ogg"): File {
  return new File(["synthetic audio"], name, { type });
}

describe("share request boundary", () => {
  it("handles only same-origin POSTs to the exact share path", () => {
    expect(isShareRequest(request([audio()]), origin)).toBe(true);
    expect(isShareRequest(new Request(`${origin}/api/audio`), origin)).toBe(
      false,
    );
    expect(
      isShareRequest(new Request(`${origin}/prototype-share/receive`), origin),
    ).toBe(false);
    expect(isShareRequest(request([audio()]), "https://other.example")).toBe(
      false,
    );
  });
});

describe("share receipt", () => {
  it("reports text-only shares without retaining private content", async () => {
    const body = new FormData();
    body.append("text", "private message https://private.example/audio");
    body.append("title", "private title");
    body.append("url", "https://private.example/audio");
    const store = vi.fn();
    const result = await handleShare(
      new Request(`${origin}/prototype-share/receive`, {
        method: "POST",
        body,
      }),
      store,
    );
    expect(result.headers.get("Location")).toContain("error=TEXT_ONLY_SHARE");
    expect(store).not.toHaveBeenCalled();
    const attempt = vi.mocked(saveAttempt).mock.calls.at(-1)?.[0];
    expect(attempt).toMatchObject({
      outcome: "TEXT_ONLY_SHARE",
      fields: [
        { field: "text", kind: "text", nonempty: true },
        { field: "title", kind: "text", nonempty: true },
        { field: "url", kind: "text", nonempty: true },
      ],
    });
    expect(JSON.stringify(attempt)).not.toContain("private");
  });

  it("distinguishes unexpected file fields without copying their names", async () => {
    const body = new FormData();
    body.append("private-field-name", audio("private-filename.opus"));
    const result = await handleShare(
      new Request(`${origin}/prototype-share/receive`, {
        method: "POST",
        body,
      }),
      vi.fn(),
    );
    expect(result.headers.get("Location")).toContain(
      "error=UNEXPECTED_FILE_FIELD",
    );
    const attempt = vi.mocked(saveAttempt).mock.calls.at(-1)?.[0];
    expect(attempt).toMatchObject({
      fields: [{ field: "other", kind: "file", type: "audio/ogg", size: 15 }],
    });
    expect(JSON.stringify(attempt)).not.toContain("private");
  });

  it("accepts audio with accompanying text and passes sanitized diagnostics to storage", async () => {
    const body = new FormData();
    body.append("audio", audio());
    body.append("text", "private caption");
    const store = vi.fn().mockResolvedValue(undefined);
    const result = await handleShare(
      new Request(`${origin}/prototype-share/receive`, {
        method: "POST",
        body,
      }),
      store,
    );
    expect(result.headers.get("Location")).not.toContain("error");
    expect(store.mock.calls[0]?.[1]).toMatchObject({
      outcome: "RECEIVED",
      fields: [
        { field: "audio", kind: "file", type: "audio/ogg", size: 15 },
        { field: "text", kind: "text", nonempty: true },
      ],
    });
    expect(JSON.stringify(store.mock.calls[0]?.[1])).not.toContain("private");
  });

  it("does not silently ignore an extra file under another field", async () => {
    const body = new FormData();
    body.append("audio", audio());
    body.append("other", audio());
    const store = vi.fn();
    const result = await handleShare(
      new Request(`${origin}/prototype-share/receive`, {
        method: "POST",
        body,
      }),
      store,
    );
    expect(result.headers.get("Location")).toContain(
      "error=UNEXPECTED_FILE_FIELD",
    );
    expect(store).not.toHaveBeenCalled();
  });

  it("surfaces diagnostic storage failures", async () => {
    vi.mocked(saveAttempt).mockRejectedValueOnce(new Error("blocked"));
    const result = await handleShare(request([]), vi.fn());
    expect(result.headers.get("Location")).toContain("error=STORAGE_FAILED");
  });

  it("treats blank text as an empty share", async () => {
    const body = new FormData();
    body.append("text", "  ");
    const result = await handleShare(
      new Request(`${origin}/prototype-share/receive`, {
        method: "POST",
        body,
      }),
      vi.fn(),
    );
    expect(result.headers.get("Location")).toContain("error=EMPTY_SHARE");
  });

  it("waits for successful storage before redirecting", async () => {
    let finish: (() => void) | undefined;
    const store = vi.fn<(file: File) => Promise<void>>(
      () =>
        new Promise<void>((resolve) => {
          finish = resolve;
        }),
    );
    const response = handleShare(request([audio()]), store, 1024);
    let settled = false;
    void response.then(() => {
      settled = true;
    });
    await vi.waitFor(() => expect(store).toHaveBeenCalledOnce());
    expect(settled).toBe(false);
    finish?.();
    const result = await response;
    expect(result.status).toBe(303);
    expect(result.headers.get("Location")).toBe(
      `${origin}/prototype-share/share`,
    );
    expect(store.mock.calls[0]?.[0]).toMatchObject({
      name: "voice.opus",
      size: 15,
    });
  });

  it.each([
    ["voice.opus", "application/octet-stream"],
    ["VOICE.OGG", ""],
    ["voice.mp3", "audio/mpeg"],
  ])("accepts messenger audio %s", async (name, type) => {
    const store = vi.fn().mockResolvedValue(undefined);
    const result = await handleShare(request([audio(name, type)]), store, 1024);
    expect(result.headers.get("Location")).not.toContain("error");
    expect(store).toHaveBeenCalledOnce();
  });

  it.each([
    ["EMPTY_SHARE", []],
    ["MULTIPLE_FILES", [audio(), audio()]],
    ["EMPTY_FILE", [new File([], "empty.opus")]],
    ["UNSUPPORTED_FILE", [audio("photo.png", "image/png")]],
    ["FILE_TOO_LARGE", [new File(["x".repeat(1025)], "large.opus")]],
  ])("rejects %s without replacing existing storage", async (code, files) => {
    const store = vi.fn();
    const result = await handleShare(request(files), store, 1024);
    expect(result.status).toBe(303);
    expect(result.headers.get("Location")).toContain(`error=${code}`);
    expect(store).not.toHaveBeenCalled();
  });

  it("reports invalid multipart input", async () => {
    const malformed = new Request(`${origin}/prototype-share/receive`, {
      method: "POST",
      body: "not multipart",
      headers: { "Content-Type": "text/plain" },
    });
    const store = vi.fn();
    const result = await handleShare(malformed, store, 1024);
    expect(result.headers.get("Location")).toContain("error=INVALID_SHARE");
    expect(store).not.toHaveBeenCalled();
  });

  it("reports quota or storage errors instead of claiming receipt", async () => {
    const store = vi
      .fn()
      .mockRejectedValue(new DOMException("quota", "QuotaExceededError"));
    const result = await handleShare(request([audio()]), store, 1024);
    expect(result.headers.get("Location")).toContain("error=STORAGE_FAILED");
  });
});
