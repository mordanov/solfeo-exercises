import { expect, it } from "vitest";
import { browserLanguage } from "../configuration";

it.each([
  [["ru-RU", "en-US"], "ru"],
  [["es-MX", "en"], "es"],
  [["de-DE", "es-ES"], "es"],
  [["EN-gb"], "en"],
  [["fr-FR", "zh-CN"], "en"],
])("matches supported browser preferences %j", (languages, expected) => {
  expect(browserLanguage(languages, "fr")).toBe(expected);
});
it("uses the browser's primary language when its preference list is empty", () => {
  expect(browserLanguage([], "ru-RU")).toBe("ru");
  expect(browserLanguage([], "ja")).toBe("en");
});
