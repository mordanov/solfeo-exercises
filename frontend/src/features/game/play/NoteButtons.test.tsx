import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { i18n } from "../../../i18n";
import NoteButtons from "./NoteButtons";

beforeEach(async () => {
  await i18n.changeLanguage("en");
});

it.each(["treble", "bass"] as const)(
  "offers exactly seven names and plays their current question octave in %s",
  (clef) => {
    const answer = vi.fn();
    render(
      <NoteButtons
        clef={clef}
        octave={2}
        noteNaming="letters"
        onAnswer={answer}
      />,
    );
    expect(screen.getAllByRole("button")).toHaveLength(7);
    fireEvent.click(screen.getByRole("button", { name: "C" }));
    fireEvent.click(screen.getByRole("button", { name: "B" }));
    expect(answer.mock.calls).toEqual([
      [{ name: "C", octave: 2 }],
      [{ name: "B", octave: 2 }],
    ]);
  },
);
it.each([
  ["en", "Do", "Sol"],
  ["ru", "До", "Соль"],
  ["es", "Do", "Sol"],
])(
  "uses localized solfege without octave labels in %s",
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
