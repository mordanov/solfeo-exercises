import { Box, Button } from "@mui/material";
import { useTranslation } from "react-i18next";
import { NOTE_NAMES, noteLabel } from "../notes";
import type { Note } from "../api/hooks";

const RAINBOW = [
  "#FF6B6B",
  "#FF8E53",
  "#FFD93D",
  "#6BCB77",
  "#4EC9B0",
  "#4D96FF",
  "#9B59B6",
];

interface Props {
  clef: "treble" | "bass";
  octave?: number;
  noteNaming: "solfege" | "letters";
  onAnswer: (note: Note) => void;
  disabled?: boolean;
}

export default function NoteButtons({
  noteNaming,
  octave = 4,
  onAnswer,
  disabled = false,
}: Props) {
  const { t } = useTranslation();

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(52px, 1fr))",
        gap: 1,
        mt: 3,
      }}
    >
      {NOTE_NAMES.map((name, i) => {
        const note = { name, octave };
        return (
          <Button
            key={name}
            variant="contained"
            disabled={disabled}
            onClick={() => onAnswer(note)}
            sx={{
              minWidth: 0,
              minHeight: 56,
              px: 0.5,
              fontSize: "1rem",
              fontWeight: 700,
              background: RAINBOW[i],
              "&:hover": { background: RAINBOW[i], filter: "brightness(1.1)" },
              "&.Mui-disabled": { opacity: 0.4, background: RAINBOW[i] },
            }}
            aria-label={noteLabel(note, noteNaming, t)}
          >
            {noteLabel(note, noteNaming, t)}
          </Button>
        );
      })}
    </Box>
  );
}
