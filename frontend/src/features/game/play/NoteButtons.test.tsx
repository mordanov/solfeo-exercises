import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { i18n } from "../../../i18n";
import NoteButtons from "./NoteButtons";

beforeEach(async () => {
  await i18n.changeLanguage("en");
});

it.each(["treble", "bass"] as const)(
  "offers exactly fourteen octave-specific letter buttons in %s",
  (clef) => {
    const answer = vi.fn();
    render(<NoteButtons clef={clef} noteNaming="letters" onAnswer={answer} />);
    expect(screen.getAllByRole("button")).toHaveLength(14);
    fireEvent.click(screen.getByRole("button", { name: "C4" }));
    fireEvent.click(screen.getByRole("button", { name: "B5" }));
    expect(answer.mock.calls).toEqual([
      [{ name: "C", octave: 4 }],
      [{ name: "B", octave: 5 }],
    ]);
  },
);
it.each([
  ["en", "Do4", "Sol5"],
  ["ru", "До4", "Соль5"],
  ["es", "Do4", "Sol5"],
])(
  "uses localized solfege and octaves in %s",
  async (language, first, last) => {
    await i18n.changeLanguage(language);
    render(
      <NoteButtons clef="treble" noteNaming="solfege" onAnswer={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: first })).toBeEnabled();
    expect(screen.getByRole("button", { name: last })).toBeEnabled();
    expect(
      screen.queryByRole("button", { name: "C4" }),
    ).not.toBeInTheDocument();
  },
);
