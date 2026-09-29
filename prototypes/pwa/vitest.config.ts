import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/prototype-share/",
  plugins: [react()],
  test: {
    environment: "node",
    restoreMocks: true,
    env: { BASE_URL: "/prototype-share/" },
  },
});
