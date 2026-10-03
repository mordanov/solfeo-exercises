import { Alert } from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { avatarSource, type AvatarMood } from "./avatars";

interface AvatarImageProps {
  animalId: string;
  stage?: number;
  mood?: AvatarMood;
  size?: number;
  selection?: boolean;
  customAvatarId?: number | null;
}

export default function AvatarImage({
  animalId,
  stage = 1,
  mood = "neutral",
  size = 80,
  selection = false,
  customAvatarId,
}: AvatarImageProps) {
  const { t } = useTranslation();
  const [failedSource, setFailedSource] = useState<string | null>(null);
  const src = selection
    ? `/assets/avatars/selection/${animalId}.png`
    : avatarSource(animalId, stage, mood, customAvatarId);
  const name = t(
    customAvatarId || animalId === "custom"
      ? "game.avatar.custom"
      : `game.avatar.animal.${animalId}`,
  );
  if (failedSource === src)
    return <Alert severity="error">{t("game.avatar.imageError")}</Alert>;
  return (
    <img
      src={src}
      width={size}
      height={size}
      alt={
        selection
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
}
