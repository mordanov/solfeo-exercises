import { Box, Button, Chip, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { usePlayer } from "../api/hooks";
import AvatarImage from "../setup/AvatarImage";
import { roundMood } from "../setup/avatars";
import { ErrorMessage } from "../../../components/AccountUi";

interface RoundResult {
  score: number;
  score_bonus?: number;
  correct_count: number;
  is_win: boolean;
  xp_gained: number;
  level_up: boolean;
  new_trophy: number | null;
  practice_hint: string;
}

interface Props {
  playerId: number;
  result: RoundResult;
  onPlayAgain: () => void;
  onChangePlayer: () => void;
}

function Stars({ correct }: { correct: number }) {
  const filled = Math.round((correct / 7) * 3);
  return (
    <Box sx={{ display: "flex", justifyContent: "center", gap: 1, my: 1 }}>
      {[0, 1, 2].map((i) => (
        <Typography key={i} sx={{ fontSize: "2.5rem" }}>
          {i < filled ? "⭐" : "☆"}
        </Typography>
      ))}
    </Box>
  );
}

export default function ResultScreen({
  playerId,
  result,
  onPlayAgain,
  onChangePlayer,
}: Props) {
  const { t } = useTranslation();
  const player = usePlayer(playerId);

  return (
    <Box sx={{ p: 3, textAlign: "center", maxWidth: 400, mx: "auto" }}>
      {player.isError && <ErrorMessage error={player.error} />}
      {player.isPending && <Typography>{t("common.loading")}</Typography>}
      {player.data && (
        <>
          <AvatarImage
            animalId={player.data.avatar_animal ?? "unicorn"}
            stage={player.data.avatar_level}
            mood={roundMood(result.correct_count)}
            customAvatarId={player.data.custom_avatar_id}
            size={192}
          />
          <Typography>
            {t("game.profile.level", { level: player.data.avatar_level })}
          </Typography>
        </>
      )}
      <Typography variant="h3" sx={{ fontWeight: 800, mb: 1 }}>
        {result.is_win ? t("game.result.win") : t("game.result.lose")}
      </Typography>

      <Stars correct={result.correct_count} />

      <Typography variant="h5" sx={{ mb: 0.5 }}>
        {t("game.result.score", { score: result.score })}
      </Typography>
      {result.score_bonus !== undefined && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {t("game.result.assistanceBonus", { points: result.score_bonus })}
        </Typography>
      )}
      <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
        {t("game.result.correct", { count: result.correct_count })}
      </Typography>

      <Chip
        label={t("game.result.xpGained", { xp: result.xp_gained })}
        color="primary"
        sx={{ fontWeight: 700, fontSize: "1rem", mb: 1.5 }}
      />

      {result.level_up && (
        <Typography variant="h6" sx={{ color: "#FFD93D", mb: 1 }}>
          {t("game.result.levelUp")}
        </Typography>
      )}
      {result.new_trophy !== null && (
        <Typography variant="h6" sx={{ mb: 1 }}>
          {t("game.result.newTrophy")}
        </Typography>
      )}

      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ mb: 3, fontStyle: "italic" }}
      >
        {t("game.result.practiceHint_prefix")}
        {result.practice_hint}
      </Typography>

      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", sm: "row" },
          gap: 2,
          justifyContent: "center",
        }}
      >
        <Button
          variant="contained"
          size="large"
          onClick={onPlayAgain}
          sx={{ minWidth: 140 }}
        >
          {t("game.result.playAgain")}
        </Button>
        <Button
          variant="outlined"
          size="large"
          onClick={onChangePlayer}
          sx={{ minWidth: 140 }}
        >
          {t("game.result.changePlayer")}
        </Button>
      </Box>
    </Box>
  );
}
