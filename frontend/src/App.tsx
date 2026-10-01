import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { AuthArea } from "./features/auth/AuthArea";
import { HealthStatus } from "./features/health/HealthStatus";
import { LanguageOptions } from "./components/AccountUi";
import { isLanguage } from "./configuration";

function NotFound() {
  const { t, i18n } = useTranslation();
  return (
    <section>
      <label>
        {t("language.label")}
        <select
          value={i18n.resolvedLanguage}
          onChange={(event) => {
            if (isLanguage(event.target.value))
              void i18n.changeLanguage(event.target.value);
          }}
        >
          <LanguageOptions />
        </select>
      </label>
      <h2>{t("notFound.title")}</h2>
      <p>{t("notFound.description")}</p>
      <a href="/">{t("notFound.home")}</a>
    </section>
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
    <main>
      <h1>{t("app.title")}</h1>
      <p>{t("app.description")}</p>
      {knownPath ? (
        <>
          <AuthArea />
          <HealthStatus />
        </>
      ) : (
        <NotFound />
      )}
    </main>
  );
}
