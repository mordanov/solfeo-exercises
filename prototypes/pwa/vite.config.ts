import { resolve } from "node:path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { manifest, prefix } from "./manifest";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const language = env.VITE_DEFAULT_LANGUAGE ?? "en";
  if (language !== "en" && language !== "ru" && language !== "es") {
    throw new Error("VITE_DEFAULT_LANGUAGE must be en, ru, or es");
  }
  return {
    base: prefix,
    plugins: [
      react(),
      {
        name: "prototype-manifest",
        generateBundle() {
          this.emitFile({
            type: "asset",
            fileName: "manifest.webmanifest",
            source: JSON.stringify(manifest(language), null, 2),
          });
        },
      },
    ],
    build: {
      rollupOptions: {
        input: { app: resolve("index.html"), sw: resolve("src/sw.ts") },
        output: {
          entryFileNames: (chunk) =>
            chunk.name === "sw" ? "sw.js" : "assets/[name]-[hash].js",
        },
      },
    },
  };
});
