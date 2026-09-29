import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  saveSettings,
  type Auth,
  type NoteNaming,
  type User,
} from "../../api/auth";
import { isLanguage, type Language } from "../../configuration";
import { ErrorMessage, LanguageOptions } from "../../components/AccountUi";

export function SettingsForm({
  auth,
  onChange,
}: {
  auth: Auth;
  onChange: (user: User) => void;
}) {
  const { t } = useTranslation();
  const [language, setLanguage] = useState(auth.user.ui_language);
  const [naming, setNaming] = useState<NoteNaming>(auth.user.note_naming);
  const mutation = useMutation({
    mutationFn: (values: { language: Language; naming: NoteNaming }) =>
      saveSettings(auth.csrf_token, values.language, values.naming),
    onSuccess: onChange,
  });
  return (
    <section>
      <h2>{t("settings.title")}</h2>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          mutation.mutate({ language, naming });
        }}
      >
        <label>
          {t("language.label")}
          <select
            value={language}
            disabled={mutation.isPending}
            onChange={(event) => {
              if (isLanguage(event.target.value)) {
                setLanguage(event.target.value);
                mutation.mutate({ language: event.target.value, naming });
              }
            }}
          >
            <LanguageOptions />
          </select>
        </label>
        <label>
          {t("settings.noteNaming")}
          <select
            value={naming}
            disabled={mutation.isPending}
            onChange={(event) => {
              if (
                event.target.value === "letters" ||
                event.target.value === "solfege"
              ) {
                setNaming(event.target.value);
                mutation.mutate({ language, naming: event.target.value });
              }
            }}
          >
            <option value="letters">{t("settings.letters")}</option>
            <option value="solfege">{t("settings.solfege")}</option>
          </select>
        </label>
        <button disabled={mutation.isPending}>{t("settings.save")}</button>
        {mutation.isError && <ErrorMessage error={mutation.error} />}
        {mutation.isSuccess && <p role="status">{t("settings.saved")}</p>}
      </form>
    </section>
  );
}
