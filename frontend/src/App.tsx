import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { AuthArea } from "./features/auth/AuthArea";
import { HealthStatus } from "./features/health/HealthStatus";
import { LanguageOptions } from "./components/AccountUi";
import { isLanguage } from "./configuration";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { ThemeToggle } from "./components/ThemeToggle";
import { InstallApp } from "./components/InstallApp";
import { Field, Panel, Select } from "./components/Ui";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Tooltip from "@mui/material/Tooltip";

function NotFound() {
  const { t, i18n } = useTranslation();
  return (
    <Panel>
      <Field>
        {t("language.label")}
        <Select
          value={i18n.resolvedLanguage}
          onChange={(event) => {
            if (isLanguage(event.target.value))
              void i18n.changeLanguage(event.target.value);
          }}
        >
          <LanguageOptions />
        </Select>
      </Field>
      <h2>{t("notFound.title")}</h2>
      <p>{t("notFound.description")}</p>
      <Button href="/">{t("notFound.home")}</Button>
    </Panel>
  );
}

export function App() {
  const { t, i18n } = useTranslation();
  const branding = (
    <>
      <Typography component="h1" variant="h1">
        {t("app.title")}
      </Typography>
      <Typography color="text.secondary" sx={{ mt: 1 }}>
        {t("app.description")}
      </Typography>
    </>
  );
  const knownPath =
    window.location.pathname === "/" ||
    /^\/(login|settings|manager\/users|manager\/exercises|manager\/journal|manager\/telegram|student|game(\/.*)?)\/?$/.test(
      window.location.pathname,
    );

  useEffect(() => {
    document.documentElement.lang = i18n.resolvedLanguage ?? i18n.language;
    document.title = t("app.title");
    const manifest = document.querySelector<HTMLLinkElement>(
      'link[rel="manifest"]',
    );
    const language = i18n.resolvedLanguage;
    if (manifest && language && isLanguage(language))
      manifest.href = `/manifest-${language}.webmanifest`;
  }, [i18n, i18n.resolvedLanguage, t]);

  return (
    <Container
      component="main"
      maxWidth="lg"
      sx={{ py: { xs: 2, sm: 4 }, bgcolor: "transparent" }}
    >
      <Stack
        component="header"
        direction={{ xs: "column", sm: "row" }}
        sx={{
          position: "relative",
          justifyContent: "space-between",
          alignItems: { xs: "flex-start", sm: "center" },
          gap: 2,
        }}
      >
        <Tooltip title={t("game.playHint")} describeChild>
          <ButtonBase
            component="a"
            href="/game"
            aria-label={t("game.playHint")}
            sx={{
              position: "absolute",
              zIndex: 1,
              top: 0,
              left: 0,
              width: 44,
              height: 44,
              borderRadius: "50%",
              overflow: "hidden",
              "&.Mui-focusVisible": {
                outline: "3px solid",
                outlineColor: "primary.main",
                outlineOffset: 3,
              },
            }}
          >
            <Box
              component="img"
              src="/assets/game-badge.png"
              alt=""
              width={44}
              height={44}
              sx={{ display: "block" }}
            />
          </ButtonBase>
        </Tooltip>
        <Box sx={{ position: "relative", minWidth: 0, maxWidth: "100%" }}>
          {/* Preserve the original header dimensions without moving page content. */}
          <Box aria-hidden sx={{ visibility: "hidden" }}>
            {branding}
          </Box>
          <Box
            sx={{
              position: "absolute",
              top: 0,
              left: 52,
              right: { xs: 0, md: -52 },
              "& h1": {
                fontSize: { xs: "1.4rem", sm: "1.8rem", md: "2.25rem" },
              },
              "& p": { fontSize: { xs: "0.8rem", md: "1rem" } },
            }}
          >
            {branding}
          </Box>
        </Box>
        <ThemeToggle />
      </Stack>
      <InstallApp />
      {knownPath ? (
        <>
          <AuthArea />
          {window.location.pathname.replace(/\/+$/, "") === "/settings" && (
            <HealthStatus />
          )}
        </>
      ) : (
        <NotFound />
      )}
    </Container>
  );
}
