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
import { Field, Panel, Select } from "./components/Ui";
import Button from "@mui/material/Button";

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
  const knownPath =
    window.location.pathname === "/" ||
    /^\/(login|settings|manager\/users|manager\/exercises|manager\/journal|manager\/telegram|student)\/?$/.test(
      window.location.pathname,
    );

  useEffect(() => {
    document.documentElement.lang = i18n.resolvedLanguage ?? i18n.language;
    document.title = t("app.title");
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
          justifyContent: "space-between",
          alignItems: { xs: "flex-start", sm: "center" },
          gap: 2,
        }}
      >
        <div>
          <Typography component="h1" variant="h1">
            {t("app.title")}
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            {t("app.description")}
          </Typography>
        </div>
        <ThemeToggle />
      </Stack>
      {knownPath ? (
        <>
          <AuthArea />
          <HealthStatus />
        </>
      ) : (
        <NotFound />
      )}
    </Container>
  );
}
