import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { AuthArea } from "./features/auth/AuthArea";
import { HealthStatus } from "./features/health/HealthStatus";

export function App() {
  const { t, i18n } = useTranslation();

  useEffect(() => {
    document.documentElement.lang = i18n.resolvedLanguage ?? i18n.language;
    document.title = t("app.title");
  }, [i18n, i18n.resolvedLanguage, t]);

  return (
    <main>
      <h1>{t("app.title")}</h1>
      <p>{t("app.description")}</p>
      <AuthArea />
      <HealthStatus />
    </main>
  );
}
