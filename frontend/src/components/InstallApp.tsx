import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import useMediaQuery from "@mui/material/useMediaQuery";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import { Button, Panel } from "./Ui";

interface InstallPrompt extends Event {
  prompt: () => Promise<unknown>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

function isInstallPrompt(event: Event): event is InstallPrompt {
  return (
    "prompt" in event &&
    typeof event.prompt === "function" &&
    "userChoice" in event &&
    event.userChoice instanceof Promise
  );
}

export function InstallApp() {
  const { t } = useTranslation();
  const coarse = useMediaQuery("(pointer: coarse)");
  const standalone = useMediaQuery("(display-mode: standalone)");
  const mobile = coarse || navigator.maxTouchPoints > 0;
  const apple =
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const [prompt, setPrompt] = useState<InstallPrompt | null>(null);
  const [closed, setClosed] = useState(false);
  const [help, setHelp] = useState(false);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const available = (event: Event) => {
      if (!mobile || !isInstallPrompt(event)) return;
      event.preventDefault();
      setPrompt(event);
    };
    const installed = () => setClosed(true);
    window.addEventListener("beforeinstallprompt", available);
    window.addEventListener("appinstalled", installed);
    return () => {
      window.removeEventListener("beforeinstallprompt", available);
      window.removeEventListener("appinstalled", installed);
    };
  }, [mobile]);
  if (
    !mobile ||
    standalone ||
    Reflect.get(navigator, "standalone") === true ||
    closed
  )
    return null;
  async function install() {
    if (!prompt) {
      setHelp(true);
      return;
    }
    setBusy(true);
    setError(false);
    try {
      await prompt.prompt();
      const choice = await prompt.userChoice;
      if (choice.outcome !== "accepted" && choice.outcome !== "dismissed")
        throw new Error("APP_INSTALL_FAILED");
      setPrompt(null);
      if (choice.outcome === "accepted") setClosed(true);
      else setHelp(true);
    } catch {
      console.error("APP_INSTALL_FAILED");
      setError(true);
      setPrompt(null);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Panel aria-label={t("install.title")}>
      <h3>{t("install.title")}</h3>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
        <Button type="button" disabled={busy} onClick={() => void install()}>
          {t("install.action")}
        </Button>
        <Button type="button" disabled={busy} onClick={() => setClosed(true)}>
          {t("install.close")}
        </Button>
      </Box>
      {help && (
        <Alert severity="info" role="status">
          {t(apple ? "install.safari" : "install.browser")}
        </Alert>
      )}
      {error && <Alert severity="error">{t("install.error")}</Alert>}
    </Panel>
  );
}
