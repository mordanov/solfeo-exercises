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
import { Button, Field, Form, Panel, Select } from "../../components/Ui";
import Alert from "@mui/material/Alert";
import { AppearanceForm } from "./AppearanceForm";

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
    <Panel>
      <h2>{t("settings.title")}</h2>
      <Form
        onSubmit={(event) => {
          event.preventDefault();
          mutation.mutate({ language, naming });
        }}
      >
        <Field>
          {t("language.label")}
          <Select
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
          </Select>
        </Field>
        <Field>
          {t("settings.noteNaming")}
          <Select
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
          </Select>
        </Field>
        <Button disabled={mutation.isPending}>{t("settings.save")}</Button>
        {mutation.isError && <ErrorMessage error={mutation.error} />}
        {mutation.isSuccess && (
          <Alert severity="success" role="status">
            {t("settings.saved")}
          </Alert>
        )}
      </Form>
      <AppearanceForm auth={auth} onChange={onChange} />
    </Panel>
  );
}
