import { createHash } from "node:crypto";
import { render, screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";
import { i18n } from "../../../i18n";
import Staff from "./Staff";

beforeEach(async () => {
  await i18n.changeLanguage("en");
});

it.each(["treble", "bass"] as const)(
  "uses one fixed frame for every note count and range edge in %s",
  (clef) => {
    const lower =
      clef === "treble" ? { name: "C", octave: 4 } : { name: "E", octave: 2 };
    const upper =
      clef === "treble" ? { name: "A", octave: 5 } : { name: "C", octave: 4 };
    const { rerender } = render(<Staff clef={clef} notes={[lower]} />);
    for (const notes of [
      [lower],
      [upper],
      [lower, upper],
      [lower, upper, lower, upper],
    ]) {
      rerender(<Staff clef={clef} notes={notes} />);
      expect(screen.getByRole("img")).toHaveAttribute("viewBox", "0 0 234 140");
    }
  },
);
it.each([
  {
    clef: "treble" as const,
    name: "G",
    octave: 4,
    anchor: 76,
    hash: "30b28707df86ad4c082fe9aefbb52c711f5caa26d214a2ced1eca81b17abd17e",
  },
  {
    clef: "bass" as const,
    name: "F",
    octave: 3,
    anchor: 52,
    hash: "8a3f176a3f974dfab4b2f77a8cd01b52dc071caed07750f392443ecb72a82e96",
  },
])(
  "renders the original filled $clef glyph on its reference line",
  ({ clef, name, octave, anchor, hash }) => {
    render(<Staff clef={clef} notes={[{ name, octave }]} />);
    const staff = screen.getByRole("img");
    const glyph = staff.querySelector("path");
    expect(glyph).toHaveAttribute("fill", "#333");
    expect(glyph).not.toHaveAttribute("stroke");
    expect(glyph).toHaveAttribute(
      "transform",
      `translate(10, ${anchor}) scale(0.048, -0.048)`,
    );
    expect(
      createHash("sha256")
        .update(glyph?.getAttribute("d") ?? "")
        .digest("hex"),
    ).toBe(hash);
    expect(staff.querySelector("ellipse")).toHaveAttribute(
      "cy",
      String(anchor),
    );
    expect(staff).toHaveAttribute("viewBox", "0 0 234 140");
  },
);

it.each([
  {
    clef: "treble" as const,
    notes: [
      { name: "C", octave: 4 },
      { name: "G", octave: 4 },
      { name: "F", octave: 5 },
      { name: "A", octave: 5 },
    ],
    ys: [100, 76, 40, 28],
  },
  {
    clef: "bass" as const,
    notes: [
      { name: "E", octave: 2 },
      { name: "F", octave: 3 },
      { name: "A", octave: 3 },
      { name: "C", octave: 4 },
    ],
    ys: [100, 52, 40, 28],
  },
])(
  "preserves note positions, ledger lines, and layout in $clef",
  ({ clef, notes, ys }) => {
    render(<Staff clef={clef} notes={notes} />);
    const staff = screen.getByRole("img");
    const heads = [...staff.querySelectorAll("ellipse")];
    expect(heads.map((head) => Number(head.getAttribute("cx")))).toEqual([
      70, 106, 142, 178,
    ]);
    expect(heads.map((head) => Number(head.getAttribute("cy")))).toEqual(ys);
    expect(staff.querySelectorAll("line")).toHaveLength(11);
    expect(staff).toHaveAttribute("viewBox", "0 0 234 140");
  },
);

it.each([
  ["en", "treble clef staff, note count: 1", "bass clef staff, note count: 1"],
  [
    "ru",
    "Нотный стан, скрипичный ключ, количество нот: 1",
    "Нотный стан, басовый ключ, количество нот: 1",
  ],
  [
    "es",
    "Pentagrama, clave de sol, cantidad de notas: 1",
    "Pentagrama, clave de fa, cantidad de notas: 1",
  ],
])("describes each clef accessibly in %s", async (language, treble, bass) => {
  await i18n.changeLanguage(language);
  const { rerender } = render(
    <Staff clef="treble" notes={[{ name: "G", octave: 4 }]} />,
  );
  expect(screen.getByRole("img")).toHaveAccessibleName(treble);
  rerender(<Staff clef="bass" notes={[{ name: "F", octave: 3 }]} />);
  expect(screen.getByRole("img")).toHaveAccessibleName(bass);
});
