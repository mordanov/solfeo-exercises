import { useTranslation } from "react-i18next";
import { ApiError } from "../api/auth";

export function ErrorMessage({ error }: { error: unknown }) {
  const { t, i18n } = useTranslation();
  const key =
    error instanceof ApiError ? `errors.${error.code}` : "errors.UNKNOWN";
  return <p role="alert">{t(i18n.exists(key) ? key : "errors.UNKNOWN")}</p>;
}

export function LanguageOptions() {
  const { t } = useTranslation();
  return (["en", "ru", "es"] as const).map((language) => (
    <option key={language} value={language}>
      {t(`language.${language}`)}
    </option>
  ));
}
