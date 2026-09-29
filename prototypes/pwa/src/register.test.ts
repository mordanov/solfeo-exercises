// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { basePath, workerTimeout } from "./config";
import { registerWorker } from "./register";

class Workers extends EventTarget {
  controller: { scriptURL: string } | null = null;
  register = vi.fn().mockResolvedValue({});
}

let workers: Workers;
const scriptURL = `${window.location.origin}${basePath}src/sw.ts`;

beforeEach(() => {
  workers = new Workers();
  vi.stubGlobal("navigator", { serviceWorker: workers });
  vi.stubGlobal("isSecureContext", true);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it("rejects an insecure origin", async () => {
  vi.stubGlobal("isSecureContext", false);
  await expect(registerWorker()).rejects.toThrow("secure context");
  expect(workers.register).not.toHaveBeenCalled();
});

it("propagates registration errors", async () => {
  workers.register.mockRejectedValue(new Error("registration failed"));
  await expect(registerWorker()).rejects.toThrow("registration failed");
});

it("registers the exact module worker scope without caching its update", async () => {
  workers.controller = { scriptURL };
  await registerWorker();
  expect(workers.register).toHaveBeenCalledWith(scriptURL, {
    type: "module",
    scope: basePath,
    updateViaCache: "none",
  });
});

it("waits until this worker controls the page", async () => {
  const ready = registerWorker();
  await Promise.resolve();
  workers.controller = { scriptURL };
  workers.dispatchEvent(new Event("controllerchange"));
  await expect(ready).resolves.toBeUndefined();
});

it("does not treat an unrelated controller as readiness", async () => {
  vi.useFakeTimers();
  workers.controller = { scriptURL: `${window.location.origin}/other/sw.js` };
  const ready = registerWorker();
  const assertion = expect(ready).rejects.toThrow("did not take control");
  await vi.advanceTimersByTimeAsync(workerTimeout);
  await assertion;
});
