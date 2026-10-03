import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { animals, avatarSource, roundMood } from "./avatars";
import AvatarImage from "./AvatarImage";
import { i18n } from "../../../i18n";

it.each([0, 1, 2, 3, 4, 5, 6, 7])(
  "maps %i correct answers to the bonus-aligned emotion",
  (correct) => {
    expect(roundMood(correct)).toBe(
      correct >= 5 ? "happy" : correct >= 3 ? "neutral" : "sad",
    );
  },
);
it("includes all eleven characters and their packaged images", () => {
  expect(animals).toHaveLength(11);
  for (const animal of animals) {
    for (let level = 1; level <= 10; level++)
      for (const mood of ["neutral", "happy", "sad"] as const) {
        const path = avatarSource(animal, level, mood);
        const bytes = readFileSync(`${process.cwd()}/public${path}`);
        expect(bytes.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a");
      }
  }
});
it("renders the selected stage and emotion without clipping the character", async () => {
  await i18n.changeLanguage("en");
  render(<AvatarImage animalId="lion" stage={4} mood="happy" />);
  expect(screen.getByRole("img")).toHaveAttribute(
    "src",
    "/assets/avatars/lion/lion_04_happy.png",
  );
  expect(screen.getByRole("img").style.objectFit).toBe("contain");
  fireEvent.error(screen.getByRole("img"));
  expect(screen.getByRole("alert")).toBeInTheDocument();
});
it("uses authorized URLs for generated avatars", () => {
  expect(avatarSource("dragon", 10, "sad", 42)).toBe(
    "/api/game/avatars/42/files/sad",
  );
});
