import Button from "@mui/material/Button";
import { useColorScheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";

export function ThemeToggle() {
  const { t } = useTranslation();
  const { mode, systemMode, setMode } = useColorScheme();
  const dark = (mode === "system" ? systemMode : mode) === "dark";
  return (
    <Button
      type="button"
      variant="outlined"
      aria-pressed={dark}
      onClick={() => setMode(dark ? "light" : "dark")}
      sx={{ flexShrink: 0 }}
    >
      {t(dark ? "theme.light" : "theme.dark")}
    </Button>
  );
}
