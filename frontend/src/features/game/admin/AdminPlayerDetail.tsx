import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";

import { usePlayerConfusion } from "../api/hooks";

const NOTE_NAMES = ["C", "D", "E", "F", "G", "A", "B"];

interface Props {
  playerId: number;
}

export default function AdminPlayerDetail({ playerId }: Props) {
  const { t } = useTranslation();
  const { data } = usePlayerConfusion(playerId);

  if (!data) return null;
  const maxVal = Math.max(
    1,
    ...Object.values(data.heatmap).flatMap((row) => Object.values(row)),
  );

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
        {t("game.profile.confusion")}
      </Typography>

      {data.top_confusions.map((c) => (
        <Typography key={`${c.expected}-${c.given}`} sx={{ mb: 0.5 }}>
          {t(`game.noteNames.letters.${c.expected}` as const)} →{" "}
          {t(`game.noteNames.letters.${c.given}` as const)} ×{c.count}
        </Typography>
      ))}

      <Box sx={{ overflowX: "auto", mt: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>↓ expect / given →</TableCell>
              {NOTE_NAMES.map((n) => (
                <TableCell key={n} align="center">
                  {n}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {NOTE_NAMES.map((expected) => (
              <TableRow key={expected}>
                <TableCell>{expected}</TableCell>
                {NOTE_NAMES.map((given) => {
                  const val = data.heatmap[expected]?.[given] ?? 0;
                  const intensity = val / maxVal;
                  return (
                    <TableCell
                      key={given}
                      align="center"
                      sx={{
                        background:
                          val > 0
                            ? `rgba(255,107,107,${0.1 + intensity * 0.7})`
                            : undefined,
                      }}
                    >
                      {val > 0 ? val : ""}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Box>
  );
}
