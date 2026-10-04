import {
  Box,
  Button,
  Card,
  CardActionArea,
  CardActions,
  Typography,
} from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { usePlayers, usePlayerStats } from "../api/hooks";
import StatisticsSummary from "../profile/StatisticsSummary";
import AvatarImage from "./AvatarImage";
import CreatePlayerDialog from "./CreatePlayerDialog";
import { type Auth } from "../../../api/auth";
import { ErrorMessage } from "../../../components/AccountUi";

interface Props {
  auth: Auth;
  onSelect: (playerId: number) => void;
  onProfile?: (playerId: number) => void;
  onManage?: () => void;
}

function PlayerSummary({ playerId }: { playerId: number }) {
  const { t } = useTranslation();
  const query = usePlayerStats(playerId);
  if (query.isPending)
    return <Typography role="status">{t("common.loading")}</Typography>;
  if (query.isError)
    return (
      <>
        <ErrorMessage error={query.error} />
        <Button size="small" onClick={() => void query.refetch()}>
          {t("common.retry")}
        </Button>
      </>
    );
  return <StatisticsSummary stats={query.data} compact />;
}

export default function PlayerSelect({
  auth,
  onSelect,
  onProfile,
  onManage,
}: Props) {
  const { t } = useTranslation();
  const query = usePlayers();
  const players = query.data ?? [];
  const [creating, setCreating] = useState(false);

  if (query.isPending)
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography role="status">{t("common.loading")}</Typography>
      </Box>
    );

  return (
    <Box sx={{ p: 3 }}>
      <Typography
        variant="h4"
        sx={{ mb: 3, textAlign: "center", fontWeight: 700 }}
      >
        {t("game.selectPlayer")}
      </Typography>
      {auth.user.role === "manager" && (
        <Box sx={{ textAlign: "center", mb: 2 }}>
          <Button variant="contained" onClick={() => setCreating(true)}>
            {t("game.players.create")}
          </Button>
          {onManage && (
            <Button onClick={onManage}>{t("game.admin.manage")}</Button>
          )}
        </Box>
      )}
      {creating && (
        <CreatePlayerDialog auth={auth} onClose={() => setCreating(false)} />
      )}
      {query.isError ? (
        <Box>
          <ErrorMessage error={query.error} />
          <Button onClick={() => void query.refetch()}>
            {t("common.retry")}
          </Button>
        </Box>
      ) : (
        players.length === 0 && (
          <Typography role="status" sx={{ textAlign: "center" }}>
            {t(
              auth.user.role === "manager"
                ? "game.players.emptyManager"
                : "game.players.emptyStudent",
            )}
          </Typography>
        )
      )}
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 2,
          justifyContent: "center",
        }}
      >
        {players.map((p) => (
          <Card key={p.id} sx={{ width: 160, maxWidth: "100%" }}>
            <CardActionArea
              onClick={() => onSelect(p.id)}
              sx={{
                p: 2,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 1,
              }}
            >
              <AvatarImage
                animalId={p.avatar_animal ?? "unicorn"}
                size={80}
                stage={p.avatar_level}
                customAvatarId={p.custom_avatar_id}
                reviewStatus={p.avatar_review_status}
              />
              <Typography
                variant="body1"
                sx={{
                  fontWeight: 600,
                  textAlign: "center",
                  overflowWrap: "anywhere",
                }}
              >
                {p.name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("game.profile.level", { level: p.avatar_level })} · {p.xp} XP
              </Typography>
            </CardActionArea>
            {onProfile && (
              <>
                <Box sx={{ px: 2 }}>
                  <PlayerSummary playerId={p.id} />
                </Box>
                <CardActions sx={{ justifyContent: "center" }}>
                  <Button onClick={() => onProfile(p.id)}>
                    {t("game.profile.stats")}
                  </Button>
                </CardActions>
              </>
            )}
          </Card>
        ))}
      </Box>
    </Box>
  );
}
