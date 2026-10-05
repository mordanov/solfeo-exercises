import {
  Alert,
  Box,
  Button,
  FormControlLabel,
  Link,
  Switch,
  Typography,
} from "@mui/material";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Task, usePlayer, useStartRound } from "../api/hooks";
import { preparePiano } from "../audio/synth";
import { DEFAULT_GAME_OPTIONS, DIFFICULTIES, type GameOptions } from "../notes";
import AvatarImage from "./AvatarImage";
import AvatarChooser from "./AvatarChooser";
import { ErrorMessage } from "../../../components/AccountUi";
import PrizeShelf from "../profile/PrizeShelf";

const NOTE_COUNTS = [1, 2, 3, 4] as const;

interface Props {
  playerId: number;
  csrf: string;
  isManager?: boolean;
  initialOptions?: GameOptions;
  onRoundStarted: (
    roundId: number,
    firstTask: Task,
    noteCount: number,
    difficulty: string,
    options: GameOptions,
  ) => void;
}

export default function GameSetup({
  playerId,
  csrf,
  isManager = false,
  initialOptions = DEFAULT_GAME_OPTIONS,
  onRoundStarted,
}: Props) {
  const { t } = useTranslation();
  const [difficulty, setDifficulty] = useState<string>("easy");
  const [noteCount, setNoteCount] = useState<number>(1);
  const startRound = useStartRound();
  const player = usePlayer(playerId);
  const [choosingAvatar, setChoosingAvatar] = useState(false);
  const [options, setOptions] = useState(initialOptions);
  const [audioBusy, setAudioBusy] = useState(false);
  const [audioError, setAudioError] = useState(false);
  const mounted = useRef(true);
  const preparing = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const handleStart = async () => {
    if (preparing.current || startRound.isPending) return;
    preparing.current = true;
    setAudioBusy(true);
    setAudioError(false);
    try {
      await preparePiano();
    } catch {
      if (mounted.current) setAudioError(true);
      return;
    } finally {
      preparing.current = false;
      if (mounted.current) setAudioBusy(false);
    }
    if (!mounted.current) return;
    startRound.mutate(
      {
        csrf,
        player_id: playerId,
        difficulty,
        note_count: noteCount,
        show_sound_hint: options.showSoundHint,
        show_correct_answer: options.showCorrectAnswer,
      },
      {
        onSuccess: (data) =>
          onRoundStarted(
            data.round_id,
            data.task,
            noteCount,
            difficulty,
            options,
          ),
      },
    );
  };

  return (
    <Box sx={{ p: 3, maxWidth: 400, mx: "auto" }}>
      {player.isError && <ErrorMessage error={player.error} />}
      {player.data && (
        <Box sx={{ textAlign: "center", mb: 2 }}>
          <AvatarImage
            animalId={player.data.avatar_animal ?? "unicorn"}
            customAvatarId={player.data.custom_avatar_id}
            reviewStatus={player.data.avatar_review_status}
            stage={player.data.avatar_level}
            size={144}
          />
          <Typography>{player.data.name}</Typography>
          <Typography>
            {t("game.profile.level", { level: player.data.avatar_level })}
          </Typography>
          <Button onClick={() => setChoosingAvatar(true)}>
            {t("game.avatar.choose")}
          </Button>
        </Box>
      )}
      {choosingAvatar && (
        <AvatarChooser
          playerId={playerId}
          csrf={csrf}
          isManager={isManager}
          onClose={() => setChoosingAvatar(false)}
        />
      )}
      <PrizeShelf playerId={playerId} />
      <Typography variant="h5" sx={{ mb: 2, fontWeight: 700 }}>
        {t("game.selectDifficulty")}
      </Typography>
      <Box sx={{ display: "flex", gap: 1, mb: 3 }}>
        {DIFFICULTIES.map(({ name: d }) => (
          <Button
            key={d}
            variant={difficulty === d ? "contained" : "outlined"}
            disabled={audioBusy || startRound.isPending}
            onClick={() => setDifficulty(d)}
            sx={{ flex: 1, minWidth: 0 }}
          >
            {t(`game.difficulty.${d}`)}
          </Button>
        ))}
      </Box>
      <Typography sx={{ mb: 2 }} role="note">
        {t("game.difficultyHint", {
          seconds:
            (DIFFICULTIES.find((item) => item.name === difficulty)?.timeMs ??
              13000) / 1000,
        })}
      </Typography>
      <FormControlLabel
        control={
          <Switch
            disabled={audioBusy || startRound.isPending}
            checked={options.showSoundHint}
            onChange={(_event, checked) =>
              setOptions((value) => ({ ...value, showSoundHint: checked }))
            }
          />
        }
        label={`${t("game.options.soundHint")} — ${t(options.showSoundHint ? "game.options.zeroPoints" : "game.options.onePoint")}`}
      />
      <FormControlLabel
        control={
          <Switch
            disabled={audioBusy || startRound.isPending}
            checked={options.showCorrectAnswer}
            onChange={(_event, checked) =>
              setOptions((value) => ({ ...value, showCorrectAnswer: checked }))
            }
          />
        }
        label={`${t("game.options.correctAnswer")} — ${t(options.showCorrectAnswer ? "game.options.zeroPoints" : "game.options.onePoint")}`}
      />
      <Typography variant="caption" sx={{ display: "block", mb: 2 }}>
        {t("game.options.roundBonus")}
      </Typography>

      <Typography variant="h5" sx={{ mb: 2, fontWeight: 700 }}>
        {t("game.selectNoteCount")}
      </Typography>
      <Box sx={{ display: "flex", gap: 1, mb: 4 }}>
        {NOTE_COUNTS.map((n) => (
          <Button
            key={n}
            variant={noteCount === n ? "contained" : "outlined"}
            disabled={audioBusy || startRound.isPending}
            onClick={() => setNoteCount(n)}
            sx={{ flex: 1, minWidth: 0, minHeight: 64, fontSize: "1.4rem" }}
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
        disabled={
          audioBusy ||
          startRound.isPending ||
          player.isPending ||
          player.isError
        }
        sx={{ minHeight: 64, fontSize: "1.2rem" }}
      >
        {t(audioBusy ? "game.piano.loading" : "game.startRound")}
      </Button>
      {audioError && <Alert severity="error">{t("game.audioError")}</Alert>}
      <Typography variant="caption" sx={{ display: "block", mt: 1 }}>
        <Link href="/assets/piano/LICENSE.txt" target="_blank" rel="noopener">
          {t("game.piano.credit")}
        </Link>
      </Typography>
      {startRound.isError && <ErrorMessage error={startRound.error} />}
    </Box>
  );
}
