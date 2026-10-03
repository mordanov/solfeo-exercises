import { Box, Button } from "@mui/material";
import { useTranslation } from "react-i18next";
import { playNote } from "../audio/synth";

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
const CLEF_OCTAVE: Record<string, number> = { treble: 5, bass: 3 };

interface Props {
  clef: "treble" | "bass";
  noteNaming: "solfege" | "letters";
  onAnswer: (name: string) => void;
  disabled?: boolean;
}

export default function NoteButtons({
  clef,
  noteNaming,
  onAnswer,
  disabled = false,
}: Props) {
  const { t } = useTranslation();

  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: 1.5,
        justifyContent: "center",
        mt: 3,
      }}
    >
      {NOTE_NAMES.map((name, i) => (
        <Button
          key={name}
          variant="contained"
          disabled={disabled}
          onClick={() => {
            playNote(name, CLEF_OCTAVE[clef] ?? 5);
            onAnswer(name);
          }}
          sx={{
            minWidth: 64,
            minHeight: 64,
            fontSize: "1.1rem",
            fontWeight: 700,
            background: RAINBOW[i],
            "&:hover": { background: RAINBOW[i], filter: "brightness(1.1)" },
            "&.Mui-disabled": { opacity: 0.4, background: RAINBOW[i] },
          }}
          aria-label={t(`game.noteNames.${noteNaming}.${name}` as const)}
        >
          {t(`game.noteNames.${noteNaming}.${name}` as const)}
        </Button>
      ))}
    </Box>
  );
}
