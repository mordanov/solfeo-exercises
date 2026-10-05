import { Box, Button, Chip, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { usePlayer, type RoundResult } from "../api/hooks";
import AvatarImage from "../setup/AvatarImage";
import { roundMood } from "../setup/avatars";
import { ErrorMessage } from "../../../components/AccountUi";
import { noteLabel } from "../notes";
import PrizeImage from "../profile/PrizeImage";
import PrizeShelf from "../profile/PrizeShelf";

interface Props {
  playerId: number;
  noteNaming?: "letters" | "solfege";
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
  noteNaming = "letters",
  result,
  onPlayAgain,
  onChangePlayer,
}: Props) {
  const { t, i18n } = useTranslation();
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
            reviewStatus={player.data.avatar_review_status}
            size={192}
          />
          <Typography>
            {t("game.profile.level", { level: player.data.avatar_level })}
          </Typography>
          {result.average_score != null && (
            <Typography>
              {t("game.result.averageScore", {
                score: new Intl.NumberFormat(i18n.resolvedLanguage, {
                  maximumFractionDigits: 1,
                }).format(result.average_score),
              })}
            </Typography>
          )}
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

      {result.new_achievements?.map((code) => (
        <Typography
          key={code}
          role="status"
          variant="h6"
          sx={{
            mb: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 1,
          }}
        >
          <PrizeImage code={code} size={64} />
          <Box component="span">
            {t("game.prizes.newPrize", {
              name: t(`game.prizes.codes.${code}`),
            })}
          </Box>
        </Typography>
      ))}

      {typeof result.practice_hint === "object" &&
        result.practice_hint !== null && (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ mb: 3, fontStyle: "italic" }}
          >
            {t("game.result.practiceHint", {
              expected: noteLabel(
                { name: result.practice_hint.expected, octave: 4 },
                noteNaming,
                t,
              ),
              given: noteLabel(
                { name: result.practice_hint.given, octave: 4 },
                noteNaming,
                t,
              ),
            })}
          </Typography>
        )}

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
      <PrizeShelf playerId={playerId} />
    </Box>
  );
}
