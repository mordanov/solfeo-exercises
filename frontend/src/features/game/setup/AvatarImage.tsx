import { Alert, Box, Typography } from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { avatarSource, type AvatarMood } from "./avatars";
import type { AvatarReviewStatus } from "../api/hooks";

interface AvatarImageProps {
  animalId: string;
  stage?: number;
  mood?: AvatarMood;
  size?: number;
  selection?: boolean;
  customAvatarId?: number | null;
  reviewStatus?: AvatarReviewStatus;
}

export default function AvatarImage({
  animalId,
  stage = 1,
  mood = "neutral",
  size = 80,
  selection = false,
  customAvatarId,
  reviewStatus,
}: AvatarImageProps) {
  const { t } = useTranslation();
  const [failedSource, setFailedSource] = useState<string | null>(null);
  const blocked = reviewStatus === "pending" || reviewStatus === "rejected";
  const caption =
    reviewStatus === "pending"
      ? t("game.avatar.awaitingReview")
      : t("game.avatar.reviewRejected");
  const src = blocked
    ? `/assets/avatars/selection/${reviewStatus === "pending" ? "under_moderation" : "custom"}.png`
    : selection
      ? `/assets/avatars/selection/${animalId}.png`
      : avatarSource(animalId, stage, mood, customAvatarId);
  const name = t(
    customAvatarId || animalId === "custom"
      ? "game.avatar.custom"
      : `game.avatar.animal.${animalId}`,
  );
  if (failedSource === src)
    return <Alert severity="error">{t("game.avatar.imageError")}</Alert>;
  const image = (
    <img
      src={src}
      width={size}
      height={size}
      alt={
        blocked
          ? caption
          : selection
            ? name
            : t("game.avatar.imageAlt", {
                name,
                level: stage,
                mood: t(`game.avatar.mood.${mood}`),
              })
      }
      style={{ objectFit: "contain", maxWidth: "100%" }}
      onError={() => setFailedSource(src)}
    />
  );
  return blocked ? (
    <Box sx={{ textAlign: "center" }}>
      {image}
      <Typography variant="caption" sx={{ display: "block" }}>
        {caption}
      </Typography>
    </Box>
  ) : (
    image
  );
}
