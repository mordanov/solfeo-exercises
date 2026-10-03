import {
  Box,
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

import { usePlayers, useResetSeason } from "../api/hooks";
import AvatarImage from "../setup/AvatarImage";

interface Props {
  csrf: string;
  onPlayerDetail: (playerId: number) => void;
}

export default function AdminScreen({ csrf, onPlayerDetail }: Props) {
  const { t } = useTranslation();
  const { data: players = [] } = usePlayers();
  const [resetTarget, setResetTarget] = useState<number | "all" | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const resetSeason = useResetSeason();

  const handleReset = () => {
    if (confirmation !== "RESET") return;
    if (resetTarget === "all") {
      players.forEach((p) =>
        resetSeason.mutate({ csrf, playerId: p.id, confirmation: "RESET" }),
      );
    } else if (resetTarget !== null) {
      resetSeason.mutate({
        csrf,
        playerId: resetTarget,
        confirmation: "RESET",
      });
    }
    setResetTarget(null);
    setConfirmation("");
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 2,
        }}
      >
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          {t("game.admin.title")}
        </Typography>
        <Button
          variant="outlined"
          color="error"
          onClick={() => setResetTarget("all")}
        >
          {t("game.admin.resetAll")}
        </Button>
      </Box>

      {players.map((p) => (
        <Box
          key={p.id}
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 2,
            mb: 1.5,
            p: 1.5,
            borderRadius: 3,
            background: "#fff",
            boxShadow: "0 2px 0 rgba(0,0,0,0.07)",
          }}
        >
          <AvatarImage
            animalId={p.avatar_animal ?? "unicorn"}
            size={48}
            stage={p.avatar_level}
            customAvatarId={p.custom_avatar_id}
          />
          <Box sx={{ flex: 1 }}>
            <Typography sx={{ fontWeight: 600 }}>{p.name}</Typography>
            <Typography variant="caption" color="text.secondary">
              {p.xp} XP
            </Typography>
          </Box>
          <Button size="small" onClick={() => onPlayerDetail(p.id)}>
            {t("game.profile.confusion")}
          </Button>
          <Button
            size="small"
            color="warning"
            onClick={() => setResetTarget(p.id)}
          >
            {t("game.admin.resetSeason")}
          </Button>
        </Box>
      ))}

      <Dialog open={resetTarget !== null} onClose={() => setResetTarget(null)}>
        <DialogTitle>{t("game.admin.resetSeason")}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            value={confirmation}
            onChange={(e) => setConfirmation(e.target.value)}
            label={t("game.admin.confirmReset")}
            fullWidth
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetTarget(null)}>
            {t("common.cancel") || "Cancel"}
          </Button>
          <Button
            onClick={handleReset}
            color="error"
            disabled={confirmation !== "RESET"}
          >
            {t("game.admin.resetSeason")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
