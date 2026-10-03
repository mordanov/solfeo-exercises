const DIATONIC: Record<string, number> = {
  C: 0,
  D: 1,
  E: 2,
  F: 3,
  G: 4,
  A: 5,
  B: 6,
};
const abs = (name: string, octave: number) => octave * 7 + DIATONIC[name];
const CLEF_REF = { treble: abs("E", 4), bass: abs("G", 2) } as const; // 30, 18

export const staffPos = (
  name: string,
  octave: number,
  clef: "treble" | "bass",
): number => abs(name, octave) - CLEF_REF[clef];

// MIDI for audio synthesis: C4 = 60
const MIDI_C4 = 60;
export const toMidi = (name: string, octave: number): number =>
  MIDI_C4 + (octave - 4) * 12 + [0, 2, 4, 5, 7, 9, 11][DIATONIC[name]];
