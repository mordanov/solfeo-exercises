import { Box } from "@mui/material";
import { useTranslation } from "react-i18next";

interface Props {
  code: string;
  earned?: boolean;
  size?: number;
  className?: string;
}

export default function PrizeImage({
  code,
  earned = true,
  size = 48,
  className,
}: Props) {
  const { t } = useTranslation();
  return (
    <Box
      component="img"
      src={`/assets/prizes/${code}.png`}
      alt={t(`game.prizes.codes.${code}`)}
      className={className}
      sx={{
        width: size,
        height: size,
        objectFit: "contain",
        flexShrink: 0,
        filter: earned ? "none" : "grayscale(1)",
        opacity: earned ? 1 : 0.45,
      }}
    />
  );
}
