import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { isLanguage } from "./configuration";
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
      <label htmlFor="language">{t("language.label")}</label>{" "}
      <select
        id="language"
        value={i18n.resolvedLanguage}
        onChange={(event) => {
          const language = event.target.value;
          if (isLanguage(language)) {
            void i18n.changeLanguage(language);
          }
        }}
      >
        {(["en", "ru", "es"] as const).map((language) => (
          <option key={language} value={language}>
            {t(`language.${language}`)}
          </option>
        ))}
      </select>
      <HealthStatus />
    </main>
  );
}
