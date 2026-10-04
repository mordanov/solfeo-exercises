import {
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { useState } from "react";
import { alpha } from "@mui/material/styles";

import { usePlayerConfusion } from "../api/hooks";
import { NOTE_NAMES, noteLabel } from "../notes";
import type { NoteNaming } from "../../../api/auth";
import { ErrorMessage } from "../../../components/AccountUi";
import { Field, Select } from "../../../components/Ui";

interface Props {
  playerId: number;
  noteNaming: NoteNaming;
  seasonId?: number;
}

export default function AdminPlayerDetail({
  playerId,
  noteNaming,
  seasonId,
}: Props) {
  const { t, i18n } = useTranslation();
  const [clef, setClef] = useState<"treble" | "bass">();
  const query = usePlayerConfusion(playerId, seasonId, clef);
  const data = query.data;
  const numbers = new Intl.NumberFormat(i18n.resolvedLanguage);
  const label = (name: string) => noteLabel({ name, octave: 4 }, noteNaming, t);

  const maxVal = Math.max(
    1,
    ...Object.values(data?.heatmap ?? {}).flatMap((row) => Object.values(row)),
  );

  return (
    <Box sx={{ my: 3 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
        {t("game.profile.confusion")}
      </Typography>
      <Field>
        {t("game.stats.clef")}
        <Select
          value={clef ?? ""}
          onChange={(event) => {
            const value = event.target.value;
            if (value === "" || value === "treble" || value === "bass")
              setClef(value || undefined);
          }}
        >
          <option value="">{t("game.stats.allClefs")}</option>
          <option value="treble">{t("game.clef.treble")}</option>
          <option value="bass">{t("game.clef.bass")}</option>
        </Select>
      </Field>
      {query.isError ? (
        <>
          <ErrorMessage error={query.error} />
          <Button onClick={() => void query.refetch()}>
            {t("common.retry")}
          </Button>
        </>
      ) : query.isPending ? (
        <Typography role="status">{t("common.loading")}</Typography>
      ) : (
        data && (
          <>
            {!data.top_confusions.length && !data.missed_notes.length && (
              <Typography>{t("game.stats.noMistakes")}</Typography>
            )}

            {data.top_confusions.map((c) => (
              <Typography key={`${c.expected}-${c.given}`} sx={{ mb: 0.5 }}>
                {t("game.stats.confusionPair", {
                  expected: label(c.expected),
                  given: label(c.given),
                  count: numbers.format(c.count),
                })}
              </Typography>
            ))}
            {data.top_confusions[0] && (
              <Typography sx={{ my: 1 }}>
                {t("game.stats.practiceHint", {
                  expected: label(data.top_confusions[0].expected),
                  given: label(data.top_confusions[0].given),
                })}
              </Typography>
            )}
            <Typography variant="h6" sx={{ mt: 2 }}>
              {t("game.stats.latestRound")}
            </Typography>
            {data.round_top_confusions.length ? (
              data.round_top_confusions.map((item) => (
                <Typography key={`${item.expected}-${item.given}`}>
                  {t("game.stats.confusionPair", {
                    expected: label(item.expected),
                    given: label(item.given),
                    count: numbers.format(item.count),
                  })}
                </Typography>
              ))
            ) : (
              <Typography>{t("game.stats.noRoundConfusion")}</Typography>
            )}
            <Typography variant="h6" sx={{ mt: 2 }}>
              {t("game.stats.missed")}
            </Typography>
            {data.missed_notes.length ? (
              data.missed_notes.map((item) => (
                <Typography key={item.name}>
                  {t("game.stats.missedNote", {
                    note: label(item.name),
                    count: numbers.format(item.count),
                  })}
                </Typography>
              ))
            ) : (
              <Typography>{t("game.stats.noMissed")}</Typography>
            )}

            <Box sx={{ overflowX: "auto", mt: 2 }}>
              <Table size="small">
                <caption>{t("game.stats.heatmap")}</caption>
                <TableHead>
                  <TableRow>
                    <TableCell>{t("game.stats.heatmapAxes")}</TableCell>
                    {NOTE_NAMES.map((n) => (
                      <TableCell key={n} align="center">
                        {label(n)}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {NOTE_NAMES.map((expected) => (
                    <TableRow key={expected}>
                      <TableCell component="th" scope="row">
                        {label(expected)}
                      </TableCell>
                      {NOTE_NAMES.map((given) => {
                        const val = data.heatmap[expected]?.[given] ?? 0;
                        const intensity = val / maxVal;
                        return (
                          <TableCell
                            key={given}
                            align="center"
                            sx={{
                              bgcolor: (theme) =>
                                val > 0
                                  ? alpha(
                                      theme.palette.error.main,
                                      0.1 + intensity * 0.5,
                                    )
                                  : undefined,
                            }}
                          >
                            {numbers.format(val)}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </>
        )
      )}
    </Box>
  );
}
