import { expect, it } from "vitest";
import en from "./locales/en.json";
import ru from "./locales/ru.json";
import es from "./locales/es.json";
import { errorCodes } from "../api/health";
import { readConfiguration } from "../configuration";

it("requires identical nonempty locale keys including every API error", () => {
  for (const locale of [en, ru, es]) {
    expect(Object.keys(locale).sort()).toEqual(Object.keys(en).sort());
    expect(
      Object.values(locale).every((value) => value.trim().length > 0),
    ).toBe(true);
    for (const code of errorCodes) {
      expect(locale).toHaveProperty(`errors.${code}`);
    }
  }
});

it.each(["fr", "", "EN"])(
  "rejects unsupported configured language %s",
  (language) => {
    expect(() => readConfiguration(language, "5000")).toThrow();
  },
);

it.each(["0", "-1", "", "invalid", "1.2", "Infinity"])(
  "rejects invalid timeout %s",
  (timeout) => {
    expect(() => readConfiguration("en", timeout)).toThrow();
  },
);

it("reads valid configuration without silently changing it", () => {
  expect(readConfiguration("es", "3000")).toEqual({
    language: "es",
    healthTimeoutMs: 3000,
  });
});
