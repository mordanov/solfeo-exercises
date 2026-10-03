import { Box, Card, CardActionArea, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

import { usePlayers } from "../api/hooks";
import AvatarImage from "./AvatarImage";

interface Props {
  onSelect: (playerId: number) => void;
}

export default function PlayerSelect({ onSelect }: Props) {
  const { t } = useTranslation();
  const { data: players = [], isLoading } = usePlayers();

  if (isLoading)
    return (
      <Box sx={{ p: 4, textAlign: "center" }}>
        <Typography>…</Typography>
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
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 2,
          justifyContent: "center",
        }}
      >
        {players.map((p) => (
          <Card key={p.id} sx={{ width: 140 }}>
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
              />
              <Typography
                variant="body1"
                sx={{ fontWeight: 600, textAlign: "center" }}
              >
                {p.name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("game.profile.level", { level: p.avatar_level })} · {p.xp} XP
              </Typography>
            </CardActionArea>
          </Card>
        ))}
      </Box>
    </Box>
  );
}
