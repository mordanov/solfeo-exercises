import { Box, Button, Typography } from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { type Task, useStartRound } from "../api/hooks";
import { unlockAudio } from "../audio/synth";

const DIFFICULTIES = ["easy", "medium", "hard"] as const;
const NOTE_COUNTS = [1, 2, 3, 4] as const;

interface Props {
  playerId: number;
  csrf: string;
  onRoundStarted: (
    roundId: number,
    firstTask: Task,
    noteCount: number,
    difficulty: string,
  ) => void;
}

export default function GameSetup({ playerId, csrf, onRoundStarted }: Props) {
  const { t } = useTranslation();
  const [difficulty, setDifficulty] = useState<string>("easy");
  const [noteCount, setNoteCount] = useState<number>(1);
  const startRound = useStartRound();

  const handleStart = () => {
    unlockAudio();
    startRound.mutate(
      { csrf, player_id: playerId, difficulty, note_count: noteCount },
      {
        onSuccess: (data) =>
          onRoundStarted(data.round_id, data.task, noteCount, difficulty),
      },
    );
  };

  return (
    <Box sx={{ p: 3, maxWidth: 400, mx: "auto" }}>
      <Typography variant="h5" sx={{ mb: 2, fontWeight: 700 }}>
        {t("game.selectDifficulty")}
      </Typography>
      <Box sx={{ display: "flex", gap: 1, mb: 3 }}>
        {DIFFICULTIES.map((d) => (
          <Button
            key={d}
            variant={difficulty === d ? "contained" : "outlined"}
            onClick={() => setDifficulty(d)}
            sx={{ flex: 1 }}
          >
            {t(`game.difficulty.${d}`)}
          </Button>
        ))}
      </Box>

      <Typography variant="h5" sx={{ mb: 2, fontWeight: 700 }}>
        {t("game.selectNoteCount")}
      </Typography>
      <Box sx={{ display: "flex", gap: 1, mb: 4 }}>
        {NOTE_COUNTS.map((n) => (
          <Button
            key={n}
            variant={noteCount === n ? "contained" : "outlined"}
            onClick={() => setNoteCount(n)}
            sx={{ flex: 1, minHeight: 64, fontSize: "1.4rem" }}
          >
            {n}
          </Button>
        ))}
      </Box>

      <Button
        variant="contained"
        size="large"
        fullWidth
        onClick={handleStart}
        disabled={startRound.isPending}
        sx={{ minHeight: 64, fontSize: "1.2rem" }}
      >
        {t("game.startRound")}
      </Button>
    </Box>
  );
}
