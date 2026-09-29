import { expect, it } from "vitest";
import { manifest, prefix } from "../manifest";
import en from "./i18n/locales/en.json";
import ru from "./i18n/locales/ru.json";
import es from "./i18n/locales/es.json";
import { basePath } from "./config";
import { errorCodes } from "./share";

it("has identical nonempty translation keys in every language", () => {
  for (const locale of [en, ru, es]) {
    expect(Object.keys(locale).sort()).toEqual(Object.keys(en).sort());
    expect(
      Object.values(locale).every((value) => value.trim().length > 0),
    ).toBe(true);
    for (const code of errorCodes)
      expect(locale).toHaveProperty(`errors.${code}`);
  }
});

it("uses one scope and a multipart file share target", () => {
  const result = manifest();
  expect(basePath).toBe(prefix);
  expect(result.scope).toBe(prefix);
  expect(result.start_url).toBe(prefix);
  expect(result.share_target).toMatchObject({
    action: `${prefix}receive`,
    method: "POST",
    enctype: "multipart/form-data",
    params: {
      files: [
        {
          name: "audio",
          accept: ["audio/*", ".opus", ".ogg", "application/octet-stream"],
        },
      ],
    },
  });
  expect(result.icons.map((icon) => icon.sizes)).toEqual([
    "192x192",
    "512x512",
  ]);
});
