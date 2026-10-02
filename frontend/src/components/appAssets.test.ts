// @vitest-environment node
import { readFileSync } from "node:fs";
import { expect, it } from "vitest";
import en from "../i18n/locales/en.json";
import ru from "../i18n/locales/ru.json";
import es from "../i18n/locales/es.json";

it("ships localized, installable manifests without protected files or offline caching", () => {
  for (const [language, locale] of Object.entries({ en, ru, es })) {
    const manifest: {
      name: string;
      short_name: string;
      lang: string;
      start_url: string;
      scope: string;
      display: string;
      icons: { src: string; sizes: string; type: string; purpose: string }[];
    } = JSON.parse(
      readFileSync(
        new URL(
          `../../public/manifest-${language}.webmanifest`,
          import.meta.url,
        ),
        "utf8",
      ),
    );
    expect(manifest.name).toBe(locale["app.title"]);
    expect(manifest.short_name).toBe(locale["install.shortName"]);
    expect(manifest.lang).toBe(language);
    expect(manifest.start_url).toBe("/");
    expect(manifest.scope).toBe("/");
    expect(manifest.display).toBe("standalone");
    expect(manifest.icons).toHaveLength(2);
    for (const icon of manifest.icons) {
      const bytes = readFileSync(
        new URL("../../public" + icon.src, import.meta.url),
      );
      const size = Number(icon.sizes.split("x")[0]);
      expect(bytes.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a");
      expect([bytes.readUInt32BE(16), bytes.readUInt32BE(20)]).toEqual([
        size,
        size,
      ]);
      expect(icon.type).toBe("image/png");
      expect(icon.purpose).toBe("any maskable");
    }
    expect(JSON.stringify(manifest)).not.toMatch(
      /share_target|\/api\/|service_worker/,
    );
  }
});
it("links a real favicon and distinct iPad icon dimensions", () => {
  const html = readFileSync(
    new URL("../../index.html", import.meta.url),
    "utf8",
  );
  for (const [name, size] of [
    ["apple-touch-icon.png", 180],
    ["apple-touch-icon-ipad.png", 167],
    ["apple-touch-icon-ipad-152.png", 152],
  ] as const) {
    expect(html).toContain(`href="/${name}"`);
    const bytes = readFileSync(
      new URL(`../../public/${name}`, import.meta.url),
    );
    expect([bytes.readUInt32BE(16), bytes.readUInt32BE(20)]).toEqual([
      size,
      size,
    ]);
  }
  expect(html).toContain('href="/favicon.svg"');
  expect(
    readFileSync(new URL("../../public/favicon.ico", import.meta.url))
      .subarray(0, 4)
      .toString("hex"),
  ).toBe("00000100");
});
it("includes installation assets in the restricted Docker context and serves manifest JSON", () => {
  const ignored = readFileSync(
    new URL("../../../.dockerignore", import.meta.url),
    "utf8",
  );
  for (const file of [
    "favicon.svg",
    "favicon.ico",
    "apple-touch-icon.png",
    "apple-touch-icon-ipad.png",
    "apple-touch-icon-ipad-152.png",
    "app-icon-192.png",
    "app-icon-512.png",
    "manifest-en.webmanifest",
    "manifest-ru.webmanifest",
    "manifest-es.webmanifest",
  ])
    expect(ignored.split("\n")).toContain(`!frontend/public/${file}`);
  const nginx = readFileSync(
    new URL("../../../deploy/nginx.conf", import.meta.url),
    "utf8",
  );
  expect(nginx).toContain("default_type application/manifest+json;");
});
