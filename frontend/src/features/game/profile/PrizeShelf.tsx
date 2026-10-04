import { Box, Button, Chip, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { ErrorMessage } from "../../../components/AccountUi";
import { useAchievements } from "../api/hooks";

export const PRIZE_ICONS: Record<string, string> = {
  first_round: "🌱",
  first_win: "🎉",
  perfect_round: "💎",
  correct_streak_10: "🔥",
  notes_100: "🎵",
  note_rainbow: "🌈",
  treble_25: "🐦",
  bass_25: "🐻",
  both_clefs: "🦋",
  duet: "👯",
  trio: "☘️",
  quartet: "🍀",
  all_difficulties: "🧭",
  independent_win: "🚀",
  days_streak_3: "🌻",
  days_7: "📅",
  level_2: "🌿",
  level_5: "🌟",
  wins_10: "👑",
  welcome_back: "🏡",
};

export default function PrizeShelf({ playerId }: { playerId: number }) {
  const { t } = useTranslation();
  const query = useAchievements(playerId);
  const earned = new Set(query.data?.earned.map((item) => item.code));
  return (
    <Box component="section" aria-label={t("game.prizes.title")} sx={{ my: 2 }}>
      <Typography variant="h6">{t("game.prizes.title")}</Typography>
      {query.isPending && (
        <Typography role="status">{t("common.loading")}</Typography>
      )}
      {query.isError && (
        <>
          <ErrorMessage error={query.error} />
          <Button onClick={() => void query.refetch()}>
            {t("common.retry")}
          </Button>
        </>
      )}
      {query.data && (
        <>
          {earned.size === 0 && (
            <Typography>{t("game.prizes.empty")}</Typography>
          )}
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1 }}>
            {query.data.catalog.map(({ code }) => (
              <Chip
                key={code}
                variant={earned.has(code) ? "filled" : "outlined"}
                color={earned.has(code) ? "primary" : "default"}
                label={`${PRIZE_ICONS[code] ?? "🏅"} ${t(`game.prizes.codes.${code}`)}`}
                title={`${t(
                  earned.has(code)
                    ? "game.prizes.earned"
                    : "game.prizes.locked",
                )} — ${t(`game.prizes.descriptions.${code}`)}`}
                sx={{
                  maxWidth: "100%",
                  height: "auto",
                  "& .MuiChip-label": { whiteSpace: "normal", py: 0.5 },
                }}
              />
            ))}
          </Box>
        </>
      )}
    </Box>
  );
}
