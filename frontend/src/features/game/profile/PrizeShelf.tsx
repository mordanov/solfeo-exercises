import { Box, Button, Chip, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { ErrorMessage } from "../../../components/AccountUi";
import { useAchievements } from "../api/hooks";
import PrizeImage from "./PrizeImage";

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
                avatar={<PrizeImage code={code} earned={earned.has(code)} />}
                label={t(`game.prizes.codes.${code}`)}
                title={`${t(
                  earned.has(code)
                    ? "game.prizes.earned"
                    : "game.prizes.locked",
                )} — ${t(`game.prizes.descriptions.${code}`)}`}
                sx={{
                  maxWidth: "100%",
                  height: "auto",
                  "& .MuiChip-avatar": {
                    width: 48,
                    height: 48,
                    borderRadius: 0,
                    backgroundColor: "transparent",
                    ml: 0.75,
                    my: 0.75,
                  },
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
