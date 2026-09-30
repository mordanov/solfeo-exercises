import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import {
  readConfiguration,
  readSpokenConfiguration,
} from "./src/configuration";

export default defineConfig(({ mode }) => {
  const envDir = fileURLToPath(new URL("..", import.meta.url));
  const env = loadEnv(mode, envDir, "");
  readConfiguration(env.VITE_DEFAULT_LANGUAGE, env.VITE_HEALTH_TIMEOUT_MS);
  readSpokenConfiguration(env.VITE_SPOKEN_CONFIG);
  const port = Number(env.FRONTEND_PORT ?? "18080");
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error("FRONTEND_PORT must be an integer from 1 to 65535");
  }
  const target = new URL(env.API_PROXY_TARGET ?? "http://127.0.0.1:18081");
  if (!["http:", "https:"].includes(target.protocol)) {
    throw new Error("API_PROXY_TARGET must use http or https");
  }
  if (
    target.pathname !== "/" ||
    target.search ||
    target.hash ||
    target.username ||
    target.password
  ) {
    throw new Error(
      "API_PROXY_TARGET must be an origin without credentials, a path, a query, or a fragment",
    );
  }
  return {
    envDir,
    plugins: [react()],
    server: {
      host: env.FRONTEND_HOST ?? "127.0.0.1",
      port,
      strictPort: true,
      proxy: { "/api": { target: target.origin } },
    },
  };
});
