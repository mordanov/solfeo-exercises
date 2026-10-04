import { Box, Button } from "@mui/material";
import { useTranslation } from "react-i18next";
import { GAME_NOTES, noteLabel } from "../notes";
import type { Note } from "../api/hooks";

const NOTE_NAMES = ["C", "D", "E", "F", "G", "A", "B"] as const;
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
  noteNaming: "solfege" | "letters";
  onAnswer: (note: Note) => void;
  disabled?: boolean;
}

export default function NoteButtons({
  noteNaming,
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
      {GAME_NOTES.map((note) => {
        const i = NOTE_NAMES.findIndex((name) => name === note.name);
        return (
          <Button
            key={`${note.name}${note.octave}`}
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
