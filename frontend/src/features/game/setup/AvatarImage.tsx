import { Alert, Box, Typography } from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { avatarPortraitSource, avatarSource, type AvatarMood } from "./avatars";
import type { AvatarReviewStatus } from "../api/hooks";

interface AvatarImageProps {
  animalId: string;
  stage?: number;
  mood?: AvatarMood;
  size?: number;
  selection?: boolean;
  portrait?: boolean;
  customAvatarId?: number | null;
  reviewStatus?: AvatarReviewStatus;
}

export default function AvatarImage({
  animalId,
  stage = 1,
  mood = "neutral",
  size = 80,
  selection = false,
  portrait = false,
  customAvatarId,
  reviewStatus,
}: AvatarImageProps) {
  const { t } = useTranslation();
  const [failedSources, setFailedSources] = useState<string[]>([]);
  const blocked = reviewStatus === "pending" || reviewStatus === "rejected";
  const caption =
    reviewStatus === "pending"
      ? t("game.avatar.awaitingReview")
      : t("game.avatar.reviewRejected");
  const portraitSource =
    portrait && customAvatarId ? avatarPortraitSource(customAvatarId) : null;
  const portraitFailed =
    portraitSource !== null && failedSources.includes(portraitSource);
  const src = blocked
    ? `/assets/avatars/selection/${reviewStatus === "pending" ? "under_moderation" : "custom"}.png`
    : selection
      ? `/assets/avatars/selection/${animalId}.png`
      : portraitSource && !portraitFailed
        ? portraitSource
        : avatarSource(
            animalId,
            portraitSource ? 1 : stage,
            mood,
            customAvatarId,
          );
  const name = t(
    customAvatarId || animalId === "custom"
      ? "game.avatar.custom"
      : `game.avatar.animal.${animalId}`,
  );
  if (failedSources.includes(src))
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
      style={{
        objectFit: "contain",
        maxWidth: "100%",
        ...(src === portraitSource ? { borderRadius: "50%" } : {}),
      }}
      onError={() => setFailedSources((failed) => [...failed, src])}
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
