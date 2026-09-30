import { beforeEach, expect, it, vi } from "vitest";
import { listExercises, parseExercise, saveExercise } from "./exercises";
import { readUploadTimeout } from "../configuration";

const exercise = {
  id: 1,
  title: "Scale",
  description: "",
  category: null,
  position: 0,
  omr: {
    status: "none",
    job_id: null,
    image_id: null,
    attempts: 0,
    last_error: null,
  },
  image: {
    id: "image",
    mime_type: "image/png",
    size_bytes: 10,
    duration_seconds: null,
  },
  audio: null,
};

class Upload {
  static latest: Upload;
  status = 201;
  responseText = JSON.stringify(exercise);
  timeout = 0;
  upload = {
    onprogress: (event: {
      lengthComputable: boolean;
      loaded: number;
      total: number;
    }) => {
      void event;
    },
  };
  onload = () => {};
  onloadend = () => {};
  onerror = () => {};
  ontimeout = () => {};
  onabort = () => {};
  open = vi.fn();
  setRequestHeader = vi.fn();
  send = vi.fn();
  abort = vi.fn(() => {
    this.onabort();
    this.onloadend();
  });
  constructor() {
    Upload.latest = this;
  }
}
beforeEach(() => {
  vi.stubGlobal("XMLHttpRequest", Upload);
});

it("validates exercise and media responses", () => {
  expect(parseExercise(exercise)).toEqual(exercise);
  for (const invalid of [
    null,
    { ...exercise, id: -1 },
    { ...exercise, image: null },
    { ...exercise, image: { ...exercise.image, size_bytes: -1 } },
  ])
    expect(() => parseExercise(invalid)).toThrow("INVALID_RESPONSE");
  expect(() => readUploadTimeout("0")).toThrow();
  expect(readUploadTimeout()).toBe(600000);
});
it("uses multipart without overriding the browser boundary and reports progress", async () => {
  const progress = vi.fn(),
    data = new FormData();
  const pending = saveExercise("csrf", null, data, progress);
  const xhr = Upload.latest;
  expect(xhr.open).toHaveBeenCalledWith("POST", "/api/exercises");
  expect(xhr.setRequestHeader).toHaveBeenCalledExactlyOnceWith(
    "X-CSRF-Token",
    "csrf",
  );
  expect(xhr.send).toHaveBeenCalledWith(data);
  xhr.upload.onprogress({ lengthComputable: true, loaded: 5, total: 10 });
  expect(progress).toHaveBeenCalledWith(50);
  xhr.onload();
  xhr.onloadend();
  await expect(pending).resolves.toEqual(exercise);
});
it("surfaces conversion errors and rejects expired authentication", async () => {
  const expired = vi.fn();
  window.addEventListener("solfeo:unauthorized", expired);
  try {
    const pending = saveExercise("csrf", 1, new FormData(), vi.fn());
    Upload.latest.status = 401;
    Upload.latest.responseText = JSON.stringify({ error: "AUTH_REQUIRED" });
    Upload.latest.onload();
    Upload.latest.onloadend();
    await expect(pending).rejects.toMatchObject({ code: "AUTH_REQUIRED" });
    expect(expired).toHaveBeenCalledOnce();
  } finally {
    window.removeEventListener("solfeo:unauthorized", expired);
  }
});
it("cancels uploads on unmount and surfaces network and timeout failures", async () => {
  const controller = new AbortController();
  const pending = saveExercise(
    "csrf",
    null,
    new FormData(),
    vi.fn(),
    controller.signal,
  );
  controller.abort();
  await expect(pending).rejects.toMatchObject({ code: "UPLOAD_CANCELLED" });
  const failed = saveExercise("csrf", null, new FormData(), vi.fn());
  Upload.latest.onerror();
  Upload.latest.onloadend();
  await expect(failed).rejects.toMatchObject({ code: "NETWORK_ERROR" });
  const timedOut = saveExercise("csrf", null, new FormData(), vi.fn());
  Upload.latest.ontimeout();
  Upload.latest.onloadend();
  await expect(timedOut).rejects.toMatchObject({ code: "REQUEST_TIMEOUT" });
});
it("rejects malformed lists instead of rendering an empty success", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify({ exercises: [] }))),
  );
  await expect(listExercises()).rejects.toMatchObject({
    code: "INVALID_RESPONSE",
  });
});
