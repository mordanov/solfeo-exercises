import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    restoreMocks: true,
    clearMocks: true,
    env: {
      VITE_DEFAULT_LANGUAGE: "en",
      VITE_HEALTH_TIMEOUT_MS: "5000",
    },
  },
});
