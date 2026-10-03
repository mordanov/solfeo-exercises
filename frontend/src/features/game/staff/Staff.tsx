import { staffPos } from "./staffPos";
import {
  BASS_CLEF_PATH,
  CLEF_UNITS_PER_SPACE,
  TREBLE_CLEF_PATH,
} from "./clefPaths";
import { useTranslation } from "react-i18next";

interface Note {
  name: string;
  octave: number;
}

interface StaffProps {
  notes: Note[];
  clef: "treble" | "bass";
}

// Layout constants (viewBox units)
const LINE_SPACING = 12; // px between staff lines
const STAFF_TOP = 40; // y of top (5th) line
const NOTE_R = 7; // note head radius
const CLEF_X = 10;
const FIRST_NOTE_X = 70;
const NOTE_X_GAP = 36;

function lineY(lineIndex: number): number {
  // lineIndex 0 = bottom, 4 = top
  return STAFF_TOP + (4 - lineIndex) * LINE_SPACING;
}

function posY(pos: number): number {
  // pos 0 = bottom line; each unit = half LINE_SPACING
  return lineY(0) - (pos * LINE_SPACING) / 2;
}

export default function Staff({ notes, clef }: StaffProps) {
  const { t } = useTranslation();
  const staffWidth = FIRST_NOTE_X + notes.length * NOTE_X_GAP + 20;
  const viewHeight = 140;
  const clefScale = LINE_SPACING / CLEF_UNITS_PER_SPACE;
  // SMuFL glyph origins sit on G4 for treble and F3 for bass.
  const clefY = lineY(clef === "treble" ? 1 : 3);

  const positions = notes.map((n) => staffPos(n.name, n.octave, clef));

  function ledgerLines(pos: number, x: number) {
    const lines: React.ReactElement[] = [];
    if (pos <= -2) {
      for (let p = -2; p >= pos; p -= 2) {
        const y = posY(p);
        lines.push(
          <line
            key={`ld-${p}`}
            x1={x - NOTE_R - 3}
            y1={y}
            x2={x + NOTE_R + 3}
            y2={y}
            stroke="#222"
            strokeWidth={1.5}
          />,
        );
      }
    }
    if (pos >= 10) {
      for (let p = 10; p <= pos; p += 2) {
        const y = posY(p);
        lines.push(
          <line
            key={`lu-${p}`}
            x1={x - NOTE_R - 3}
            y1={y}
            x2={x + NOTE_R + 3}
            y2={y}
            stroke="#222"
            strokeWidth={1.5}
          />,
        );
      }
    }
    return lines;
  }

  return (
    <svg
      viewBox={`0 0 ${staffWidth} ${viewHeight}`}
      style={{
        width: "100%",
        maxWidth: 480,
        display: "block",
        margin: "0 auto",
      }}
      aria-label={t("game.staffLabel", {
        clef: t(`game.clef.${clef}`),
        count: notes.length,
      })}
      role="img"
    >
      {/* Staff paper background */}
      <rect
        x={0}
        y={0}
        width={staffWidth}
        height={viewHeight}
        fill="#FFFDF5"
        rx={8}
      />

      {/* 5 staff lines */}
      {[0, 1, 2, 3, 4].map((i) => (
        <line
          key={i}
          x1={6}
          y1={lineY(i)}
          x2={staffWidth - 6}
          y2={lineY(i)}
          stroke="#555"
          strokeWidth={1.2}
        />
      ))}

      {/* Clef glyph */}
      <path
        d={clef === "treble" ? TREBLE_CLEF_PATH : BASS_CLEF_PATH}
        fill="#333"
        transform={`translate(${CLEF_X}, ${clefY}) scale(${clefScale}, ${-clefScale})`}
      />

      {/* Notes */}
      {notes.map((_note, idx) => {
        const pos = positions[idx];
        const x = FIRST_NOTE_X + idx * NOTE_X_GAP;
        const y = posY(pos);
        const stemUp = pos < 4; // below middle line → stem up
        return (
          <g key={idx}>
            {ledgerLines(pos, x)}
            <ellipse
              cx={x}
              cy={y}
              rx={NOTE_R}
              ry={NOTE_R * 0.72}
              fill="#1a1a1a"
              transform={`rotate(-15, ${x}, ${y})`}
            />
            {stemUp ? (
              <line
                x1={x + NOTE_R - 1}
                y1={y}
                x2={x + NOTE_R - 1}
                y2={y - 36}
                stroke="#1a1a1a"
                strokeWidth={1.5}
              />
            ) : (
              <line
                x1={x - NOTE_R + 1}
                y1={y}
                x2={x - NOTE_R + 1}
                y2={y + 36}
                stroke="#1a1a1a"
                strokeWidth={1.5}
              />
            )}
          </g>
        );
      })}
    </svg>
  );
}
