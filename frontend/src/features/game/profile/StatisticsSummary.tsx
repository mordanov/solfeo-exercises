import { Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { StatsMatrix } from "../api/hooks";

export function statisticsTotals(stats: StatsMatrix) {
  return Object.values(stats)
    .flatMap(Object.values)
    .reduce(
      (total, cell) => ({
        rounds: total.rounds + cell.rounds,
        wins: total.wins + cell.wins,
        score: total.score + cell.total_score,
      }),
      { rounds: 0, wins: 0, score: 0 },
    );
}

export default function StatisticsSummary({
  stats,
  compact = false,
}: {
  stats: StatsMatrix;
  compact?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const total = statisticsTotals(stats);
  const numbers = new Intl.NumberFormat(i18n.resolvedLanguage, {
    maximumFractionDigits: 2,
  });
  const percent = new Intl.NumberFormat(i18n.resolvedLanguage, {
    style: "percent",
    maximumFractionDigits: 1,
  });
  return (
    <Stack spacing={0.5} sx={{ my: 1 }}>
      <Typography variant={compact ? "caption" : "body1"}>
        {t("game.stats.rounds", { value: numbers.format(total.rounds) })}
      </Typography>
      {!compact && (
        <Typography>
          {t("game.stats.wins", { value: numbers.format(total.wins) })}
        </Typography>
      )}
      <Typography variant={compact ? "caption" : "body1"}>
        {t("game.stats.winRate", {
          value: percent.format(total.rounds ? total.wins / total.rounds : 0),
        })}
      </Typography>
      {!compact && (
        <Typography>
          {t("game.stats.average", {
            value: numbers.format(
              total.rounds ? total.score / total.rounds : 0,
            ),
          })}
        </Typography>
      )}
    </Stack>
  );
}
