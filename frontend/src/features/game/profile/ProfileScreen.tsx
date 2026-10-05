import {
  Box,
  Button,
  Chip,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { useState } from "react";

import {
  usePlayer,
  usePlayerStats,
  useSeasons,
  type StatsMatrix,
} from "../api/hooks";
import AvatarImage from "../setup/AvatarImage";
import { ErrorMessage } from "../../../components/AccountUi";
import { Field, Select } from "../../../components/Ui";
import type { NoteNaming } from "../../../api/auth";
import { DIFFICULTIES } from "../notes";
import AdminPlayerDetail from "../admin/AdminPlayerDetail";
import StatisticsSummary, { statisticsTotals } from "./StatisticsSummary";
import PrizeShelf from "./PrizeShelf";

const TROPHY_ICONS: Record<number, string> = {
  20: "🥉",
  100: "🥈",
  200: "🥇",
  500: "🏆",
};
const NOTE_COUNTS = [1, 2, 3, 4];

interface Props {
  playerId: number;
  noteNaming: NoteNaming;
  showAnalysis?: boolean;
  onBack: () => void;
}

export default function ProfileScreen({
  playerId,
  noteNaming,
  showAnalysis = false,
  onBack,
}: Props) {
  const { t, i18n } = useTranslation();
  const [seasonId, setSeasonId] = useState<number>();
  const stats = usePlayerStats(playerId, seasonId);
  const player = usePlayer(playerId);
  const seasons = useSeasons(playerId);
  const numbers = new Intl.NumberFormat(i18n.resolvedLanguage, {
    maximumFractionDigits: 2,
  });
  const percent = new Intl.NumberFormat(i18n.resolvedLanguage, {
    style: "percent",
    maximumFractionDigits: 1,
  });
  const dates = new Intl.DateTimeFormat(i18n.resolvedLanguage, {
    dateStyle: "medium",
  });
  const active = seasons.data?.find((item) => item.ended_at === null);
  const selected = seasonId
    ? seasons.data?.find((item) => item.id === seasonId)
    : active;
  const failure = player.error ?? seasons.error ?? stats.error;
  const retry = () => {
    void player.refetch();
    void seasons.refetch();
    void stats.refetch();
  };
  const totalsByCount = (count: number) => {
    const matrix: StatsMatrix = {};
    for (const [difficulty, cells] of Object.entries(stats.data ?? {})) {
      if (cells[String(count)])
        matrix[difficulty] = { [count]: cells[String(count)] };
    }
    return statisticsTotals(matrix);
  };
  const groups = [
    ...DIFFICULTIES.map(({ name }) => ({
      label: t(`game.difficulty.${name}`),
      total: statisticsTotals({ [name]: stats.data?.[name] ?? {} }),
    })),
    ...NOTE_COUNTS.map((count) => ({
      label: t("game.noteCount", { count }),
      total: totalsByCount(count),
    })),
  ];
  const trophies = player.data?.trophies ?? [];

  return (
    <Box sx={{ p: { xs: 1, sm: 3 }, maxWidth: 800, mx: "auto", minWidth: 0 }}>
      <Button onClick={onBack}>
        {t(
          showAnalysis ? "game.stats.backManagement" : "game.stats.backPlayers",
        )}
      </Button>
      {failure ? (
        <>
          <ErrorMessage error={failure} />
          <Button onClick={retry}>{t("common.retry")}</Button>
        </>
      ) : player.isPending || seasons.isPending || stats.isPending ? (
        <Typography role="status">{t("common.loading")}</Typography>
      ) : (
        <>
          {player.data && (
            <Box sx={{ textAlign: "center" }}>
              <Typography variant="h5" component="h2">
                {player.data.name}
              </Typography>
              <AvatarImage
                animalId={player.data.avatar_animal ?? "unicorn"}
                stage={player.data.avatar_level}
                customAvatarId={player.data.custom_avatar_id}
                reviewStatus={player.data.avatar_review_status}
                size={144}
              />
              <Typography>
                {t("game.profile.level", { level: player.data.avatar_level })}
              </Typography>
              <Typography>
                {t("game.stats.xp", { xp: numbers.format(player.data.xp) })}
              </Typography>
            </Box>
          )}
          <PrizeShelf playerId={playerId} />
          <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>
            {t("game.profile.stats")}
          </Typography>
          <Field>
            {t("game.stats.season")}
            <Select
              value={seasonId ?? ""}
              onChange={(event) =>
                setSeasonId(
                  event.target.value ? Number(event.target.value) : undefined,
                )
              }
            >
              <option value="">
                {active
                  ? t("game.stats.currentSeason", {
                      number: numbers.format(active.number),
                    })
                  : t("game.stats.noSeason")}
              </option>
              {[...(seasons.data ?? [])]
                .reverse()
                .filter((item) => item.ended_at !== null)
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {t("game.stats.pastSeason", {
                      number: numbers.format(item.number),
                    })}
                  </option>
                ))}
            </Select>
          </Field>
          {selected && (
            <Typography variant="body2" sx={{ my: 1 }}>
              {t("game.stats.period", {
                start: dates.format(new Date(selected.started_at)),
                end: selected.ended_at
                  ? dates.format(new Date(selected.ended_at))
                  : t("game.stats.present"),
              })}
            </Typography>
          )}
          <StatisticsSummary stats={stats.data ?? {}} />
          {statisticsTotals(stats.data ?? {}).rounds === 0 && (
            <Typography role="status">{t("game.stats.empty")}</Typography>
          )}

          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <caption>{t("game.stats.matrix")}</caption>
              <TableHead>
                <TableRow>
                  <TableCell>{t("game.stats.difficulty")}</TableCell>
                  {NOTE_COUNTS.map((n) => (
                    <TableCell key={n} align="center">
                      {t("game.noteCount", { count: n })}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {DIFFICULTIES.map(({ name }) => (
                  <TableRow key={name}>
                    <TableCell component="th" scope="row">
                      {t(`game.difficulty.${name}`)}
                    </TableCell>
                    {NOTE_COUNTS.map((n) => {
                      const cell = stats.data?.[name]?.[n];
                      return (
                        <TableCell key={n} align="center">
                          {cell
                            ? t("game.stats.cell", {
                                rounds: numbers.format(cell.rounds),
                                wins: numbers.format(cell.wins),
                                rate: percent.format(cell.wins / cell.rounds),
                                score: numbers.format(cell.avg_score),
                              })
                            : t("game.stats.noData")}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
          <Box sx={{ overflowX: "auto", mt: 2 }}>
            <Table size="small">
              <caption>{t("game.stats.breakdown")}</caption>
              <TableHead>
                <TableRow>
                  <TableCell>{t("game.stats.group")}</TableCell>
                  <TableCell>{t("game.stats.roundsLabel")}</TableCell>
                  <TableCell>{t("game.stats.winsLabel")}</TableCell>
                  <TableCell>{t("game.stats.winRateLabel")}</TableCell>
                  <TableCell>{t("game.stats.averageLabel")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {groups.map(({ label, total }) => (
                  <TableRow key={label}>
                    <TableCell component="th" scope="row">
                      {label}
                    </TableCell>
                    <TableCell>{numbers.format(total.rounds)}</TableCell>
                    <TableCell>{numbers.format(total.wins)}</TableCell>
                    <TableCell>
                      {percent.format(
                        total.rounds ? total.wins / total.rounds : 0,
                      )}
                    </TableCell>
                    <TableCell>
                      {numbers.format(
                        total.rounds ? total.score / total.rounds : 0,
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
            {t("game.profile.trophies")}
          </Typography>
          {trophies.length === 0 ? (
            <Typography color="text.secondary">
              {t("game.profile.noTrophies")}
            </Typography>
          ) : (
            <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap" }}>
              {trophies.map((th) => (
                <Chip
                  key={th}
                  label={`${TROPHY_ICONS[th] ?? "🏅"} ${t("game.stats.trophy", {
                    threshold: numbers.format(th),
                  })}`}
                  variant="outlined"
                />
              ))}
            </Box>
          )}
          {showAnalysis && (
            <AdminPlayerDetail
              playerId={playerId}
              noteNaming={noteNaming}
              seasonId={seasonId}
            />
          )}
        </>
      )}
    </Box>
  );
}
