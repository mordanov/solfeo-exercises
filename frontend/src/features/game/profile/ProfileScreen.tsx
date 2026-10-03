import {
  Box,
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

import { usePlayer, usePlayerStats } from "../api/hooks";
import AvatarImage from "../setup/AvatarImage";
import { ErrorMessage } from "../../../components/AccountUi";

const TROPHY_ICONS: Record<number, string> = {
  20: "🥉",
  100: "🥈",
  200: "🥇",
  500: "🏆",
};
const DIFFICULTIES = ["easy", "medium", "hard"];
const NOTE_COUNTS = ["1", "2", "3", "4"];

interface Props {
  playerId: number;
  trophies?: number[];
  xp?: number;
}

export default function ProfileScreen({
  playerId,
  trophies = [],
  xp = 0,
}: Props) {
  const { t } = useTranslation();
  const { data: stats = {} } = usePlayerStats(playerId);
  const player = usePlayer(playerId);

  return (
    <Box sx={{ p: 3, maxWidth: 600, mx: "auto" }}>
      {player.isError && <ErrorMessage error={player.error} />}
      {player.data && (
        <Box sx={{ textAlign: "center" }}>
          <AvatarImage
            animalId={player.data.avatar_animal ?? "unicorn"}
            stage={player.data.avatar_level}
            customAvatarId={player.data.custom_avatar_id}
            size={144}
          />
          <Typography>
            {t("game.profile.level", { level: player.data.avatar_level })}
          </Typography>
        </Box>
      )}
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>
        {t("game.profile.stats")}
      </Typography>
      {xp > 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {xp} XP
        </Typography>
      )}

      <Box sx={{ overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell />
              {NOTE_COUNTS.map((n) => (
                <TableCell key={n} align="center">
                  {n}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {DIFFICULTIES.map((d) => (
              <TableRow key={d}>
                <TableCell>{t(`game.difficulty.${d}`)}</TableCell>
                {NOTE_COUNTS.map((n) => {
                  const cell = stats[d]?.[n];
                  return (
                    <TableCell key={n} align="center">
                      {cell
                        ? `${cell.rounds} / ${cell.avg_score.toFixed(1)}`
                        : "—"}
                    </TableCell>
                  );
                })}
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
              label={`${TROPHY_ICONS[th] ?? "🏅"} ${th}`}
              variant="outlined"
            />
          ))}
        </Box>
      )}
    </Box>
  );
}
