// @vitest-environment node
import { afterEach, expect, it, vi } from "vitest";
import configuration from "./vite.config";

afterEach(() => {
  vi.unstubAllEnvs();
});

async function resolveConfiguration() {
  if (typeof configuration !== "function") {
    throw new Error("Expected a Vite configuration factory");
  }
  return configuration({ command: "serve", mode: "test" });
}

it.each([
  "ftp://localhost",
  "http://localhost/path",
  "http://localhost/?query=yes",
  "http://localhost/#fragment",
  "http://name:password@localhost",
])(
  "rejects a proxy target that is not a plain HTTP origin: %s",
  async (target) => {
    vi.stubEnv("API_PROXY_TARGET", target);
    await expect(resolveConfiguration()).rejects.toThrow("API_PROXY_TARGET");
  },
);

it("uses the configured development origin and port", async () => {
  vi.stubEnv("API_PROXY_TARGET", "http://localhost:18099");
  vi.stubEnv("FRONTEND_PORT", "18098");
  const configuration = await resolveConfiguration();
  expect(configuration.server?.port).toBe(18098);
  expect(configuration.server?.proxy?.["/api"]).toEqual({
    target: "http://localhost:18099",
  });
});

it.each(["0", "65536", "invalid"])(
  "rejects invalid development ports",
  async (port) => {
    vi.stubEnv("FRONTEND_PORT", port);
    await expect(resolveConfiguration()).rejects.toThrow("FRONTEND_PORT");
  },
);
