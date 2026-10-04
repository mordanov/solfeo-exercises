import {
  Box,
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import {
  usePlayers,
  useResetSeason,
  useResetAllSeasons,
  type Player,
} from "../api/hooks";
import { ErrorMessage } from "../../../components/AccountUi";
import AvatarImage from "../setup/AvatarImage";

interface Props {
  csrf: string;
  onPlayerDetail: (playerId: number) => void;
  onBack: () => void;
}

export default function AdminScreen({ csrf, onPlayerDetail, onBack }: Props) {
  const { t, i18n } = useTranslation();
  const query = usePlayers();
  const players = query.data ?? [];
  const [resetTarget, setResetTarget] = useState<Player | "all" | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const [success, setSuccess] = useState(false);
  const resetSeason = useResetSeason();
  const resetAll = useResetAllSeasons();
  const pending = resetSeason.isPending || resetAll.isPending;
  const numbers = new Intl.NumberFormat(i18n.resolvedLanguage);
  const openReset = (target: Player | "all") => {
    resetSeason.reset();
    resetAll.reset();
    setSuccess(false);
    setConfirmation("");
    setResetTarget(target);
  };
  const closeReset = () => {
    if (!pending) {
      setResetTarget(null);
      setConfirmation("");
    }
  };
  const onReset = () => {
    setSuccess(true);
    setResetTarget(null);
    setConfirmation("");
  };

  const handleReset = () => {
    if (confirmation !== "RESET" || pending) return;
    if (resetTarget === "all") {
      resetAll.mutate({ csrf, confirmation: "RESET" }, { onSuccess: onReset });
    } else if (resetTarget !== null) {
      resetSeason.mutate(
        {
          csrf,
          playerId: resetTarget.id,
          confirmation: "RESET",
        },
        { onSuccess: onReset },
      );
    }
  };

  return (
    <Box sx={{ p: { xs: 1, sm: 3 } }}>
      <Button onClick={onBack}>{t("game.stats.backPlayers")}</Button>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 2,
          gap: 1,
          flexWrap: "wrap",
        }}
      >
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          {t("game.admin.title")}
        </Typography>
        <Button
          variant="outlined"
          color="error"
          onClick={() => openReset("all")}
          disabled={
            query.isPending || query.isError || !players.length || pending
          }
        >
          {t("game.admin.resetAll")}
        </Button>
      </Box>
      {success && (
        <Alert severity="success" role="status">
          {t("game.admin.seasonReset")}
        </Alert>
      )}
      {query.isPending ? (
        <Typography role="status">{t("common.loading")}</Typography>
      ) : query.isError ? (
        <>
          <ErrorMessage error={query.error} />
          <Button onClick={() => void query.refetch()}>
            {t("common.retry")}
          </Button>
        </>
      ) : (
        !players.length && <Typography>{t("game.stats.noPlayers")}</Typography>
      )}

      {!query.isError &&
        players.map((p) => (
          <Box
            key={p.id}
            sx={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: 2,
              mb: 1.5,
              p: 1.5,
              borderRadius: 3,
              bgcolor: "background.paper",
              boxShadow: "0 2px 0 rgba(0,0,0,0.07)",
            }}
          >
            <AvatarImage
              animalId={p.avatar_animal ?? "unicorn"}
              size={48}
              stage={p.avatar_level}
              customAvatarId={p.custom_avatar_id}
            />
            <Box
              sx={{ flex: "1 1 140px", minWidth: 0, overflowWrap: "anywhere" }}
            >
              <Typography sx={{ fontWeight: 600 }}>{p.name}</Typography>
              <Typography variant="caption" color="text.secondary">
                {t("game.stats.xp", { xp: numbers.format(p.xp) })}
              </Typography>
            </Box>
            <Button size="small" onClick={() => onPlayerDetail(p.id)}>
              {t("game.profile.stats")}
            </Button>
            <Button
              size="small"
              color="warning"
              onClick={() => openReset(p)}
              disabled={pending}
            >
              {t("game.admin.resetSeason")}
            </Button>
          </Box>
        ))}

      <Dialog open={resetTarget !== null} onClose={closeReset}>
        <DialogTitle>
          {t(
            resetTarget === "all"
              ? "game.admin.resetAll"
              : "game.admin.resetSeason",
          )}
        </DialogTitle>
        <DialogContent>
          <Typography>
            {resetTarget === "all"
              ? t("game.admin.resetAllDescription")
              : t("game.admin.resetDescription", {
                  name: resetTarget?.name,
                })}
          </Typography>
          <Typography sx={{ my: 1 }}>
            {t("game.admin.resetPreserves")}
          </Typography>
          {(resetSeason.error || resetAll.error) && (
            <ErrorMessage error={resetSeason.error ?? resetAll.error} />
          )}
          <TextField
            autoFocus
            value={confirmation}
            onChange={(e) => setConfirmation(e.target.value)}
            label={t("game.admin.confirmReset")}
            fullWidth
            disabled={pending}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={closeReset} disabled={pending}>
            {t("common.cancel")}
          </Button>
          <Button
            onClick={handleReset}
            color="error"
            disabled={confirmation !== "RESET" || pending}
          >
            {t(
              pending
                ? "common.loading"
                : resetTarget === "all"
                  ? "game.admin.resetAll"
                  : "game.admin.resetSeason",
            )}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
