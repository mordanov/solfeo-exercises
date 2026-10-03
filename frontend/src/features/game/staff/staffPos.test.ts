import { describe, expect, it } from "vitest";
import { staffPos } from "./staffPos";

describe("staffPos treble", () => {
  // Bottom line = E4 (pos 0), top line = F5 (pos 8)
  it("E4 = 0 (bottom line)", () => expect(staffPos("E", 4, "treble")).toBe(0));
  it("F4 = 1 (first space)", () => expect(staffPos("F", 4, "treble")).toBe(1));
  it("G4 = 2 (second line)", () => expect(staffPos("G", 4, "treble")).toBe(2));
  it("A4 = 3 (second space)", () => expect(staffPos("A", 4, "treble")).toBe(3));
  it("B4 = 4 (middle line)", () => expect(staffPos("B", 4, "treble")).toBe(4));
  it("C5 = 5 (third space)", () => expect(staffPos("C", 5, "treble")).toBe(5));
  it("D5 = 6 (fourth line)", () => expect(staffPos("D", 5, "treble")).toBe(6));
  it("E5 = 7 (fourth space)", () => expect(staffPos("E", 5, "treble")).toBe(7));
  it("F5 = 8 (top line)", () => expect(staffPos("F", 5, "treble")).toBe(8));
  it("G5 = 9 (above top line)", () =>
    expect(staffPos("G", 5, "treble")).toBe(9));
  // Ledger lines below
  it("D4 = -1 (below bottom, space)", () =>
    expect(staffPos("D", 4, "treble")).toBe(-1));
  it("C4 = -2 (ledger line below)", () =>
    expect(staffPos("C", 4, "treble")).toBe(-2));
});

describe("staffPos bass", () => {
  // Bottom line = G2 (pos 0), top line = A3 (pos 8)
  it("G2 = 0 (bottom line)", () => expect(staffPos("G", 2, "bass")).toBe(0));
  it("A2 = 1 (first space)", () => expect(staffPos("A", 2, "bass")).toBe(1));
  it("B2 = 2 (second line)", () => expect(staffPos("B", 2, "bass")).toBe(2));
  it("C3 = 3 (second space)", () => expect(staffPos("C", 3, "bass")).toBe(3));
  it("D3 = 4 (middle line)", () => expect(staffPos("D", 3, "bass")).toBe(4));
  it("E3 = 5 (third space)", () => expect(staffPos("E", 3, "bass")).toBe(5));
  it("F3 = 6 (fourth line)", () => expect(staffPos("F", 3, "bass")).toBe(6));
  it("G3 = 7 (fourth space)", () => expect(staffPos("G", 3, "bass")).toBe(7));
  it("A3 = 8 (top line)", () => expect(staffPos("A", 3, "bass")).toBe(8));
  it("B3 = 9 (above top line)", () => expect(staffPos("B", 3, "bass")).toBe(9));
  it("C4 = 10 (two above top)", () =>
    expect(staffPos("C", 4, "bass")).toBe(10));
  // Ledger lines below
  it("F2 = -1 (below bottom, space)", () =>
    expect(staffPos("F", 2, "bass")).toBe(-1));
  it("E2 = -2 (ledger line below)", () =>
    expect(staffPos("E", 2, "bass")).toBe(-2));
});
