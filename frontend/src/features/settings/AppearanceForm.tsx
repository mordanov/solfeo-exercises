import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ThemeProvider, useColorScheme } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import MuiButton from "@mui/material/Button";
import Alert from "@mui/material/Alert";
import { saveAppearance, type Auth, type User } from "../../api/auth";
import {
  defaultAppearance,
  fonts,
  isColorScheme,
  isUiFont,
  isUiFontSize,
  sameAppearance,
  schemes,
  type Appearance,
} from "../../appearance";
import { createAppearanceTheme } from "../../theme";
import { ErrorMessage } from "../../components/AccountUi";
import { Button, Field, Form, Panel, Select } from "../../components/Ui";

export function AppearanceForm({
  auth,
  onChange,
}: {
  auth: Auth;
  onChange: (user: User) => void;
}) {
  const { t, i18n } = useTranslation();
  const { mode, systemMode } = useColorScheme();
  const { light_scheme, dark_scheme, ui_font, ui_font_size } = auth.user;
  const saved: Appearance = {
    light_scheme,
    dark_scheme,
    ui_font,
    ui_font_size,
  };
  const [draft, setDraft] = useState(saved);
  const [previewMode, setPreviewMode] = useState<"light" | "dark">(
    mode === "dark" || (mode === "system" && systemMode === "dark")
      ? "dark"
      : "light",
  );
  useEffect(
    () => setDraft({ light_scheme, dark_scheme, ui_font, ui_font_size }),
    [light_scheme, dark_scheme, ui_font, ui_font_size],
  );
  const mutation = useMutation({
    mutationFn: (value: Appearance) => saveAppearance(auth.csrf_token, value),
    onSuccess: onChange,
  });
  function edit(changes: Partial<Appearance>) {
    setDraft((previous) => ({ ...previous, ...changes }));
    mutation.reset();
  }
  const preview = useMemo(
    () => createAppearanceTheme(draft, previewMode),
    [draft, previewMode],
  );
  return (
    <Panel aria-label={t("appearance.title")}>
      <h3>{t("appearance.title")}</h3>
      <p>{t("appearance.hint")}</p>
      <Form
        onSubmit={(event) => {
          event.preventDefault();
          mutation.mutate(draft);
        }}
      >
        {(["light_scheme", "dark_scheme"] as const).map((field) => (
          <Field key={field}>
            {t(`appearance.${field}`)}
            <Select
              value={draft[field]}
              disabled={mutation.isPending}
              onChange={(event) => {
                if (isColorScheme(event.target.value))
                  edit({ [field]: event.target.value });
              }}
            >
              {schemes.map((scheme) => (
                <option key={scheme} value={scheme}>
                  {t(`appearance.scheme.${scheme}`)}
                </option>
              ))}
            </Select>
          </Field>
        ))}
        <Field>
          {t("appearance.font")}
          <Select
            value={draft.ui_font}
            disabled={mutation.isPending}
            onChange={(event) => {
              if (isUiFont(event.target.value))
                edit({ ui_font: event.target.value });
            }}
          >
            {Object.keys(fonts).map((font) => (
              <option key={font} value={font}>
                {t(`appearance.font.${font}`)}
              </option>
            ))}
          </Select>
        </Field>
        <Field>
          {t("appearance.fontSize")}
          <Select
            value={draft.ui_font_size}
            disabled={mutation.isPending}
            onChange={(event) => {
              const size = Number(event.target.value);
              if (isUiFontSize(size)) edit({ ui_font_size: size });
            }}
          >
            {([16, 18, 20] as const).map((size) => (
              <option key={size} value={size}>
                {t(`appearance.size.${size}`, {
                  size: new Intl.NumberFormat(i18n.language).format(size),
                })}
              </option>
            ))}
          </Select>
        </Field>
        <Field>
          {t("appearance.preview.mode")}
          <Select
            value={previewMode}
            onChange={(event) => {
              if (
                event.target.value === "light" ||
                event.target.value === "dark"
              )
                setPreviewMode(event.target.value);
            }}
          >
            <option value="light">{t("appearance.preview.light")}</option>
            <option value="dark">{t("appearance.preview.dark")}</option>
          </Select>
        </Field>
        <ThemeProvider theme={preview}>
          <Box sx={{ bgcolor: "background.default", p: 2, borderRadius: 2 }}>
            <Panel
              aria-label={t("appearance.preview.title")}
              sx={{ m: 0, p: 2, fontFamily: fonts[draft.ui_font] }}
            >
              <Typography
                component="h4"
                variant="h4"
                sx={{ fontSize: draft.ui_font_size * 1.1 }}
              >
                {t("appearance.preview.title")}
              </Typography>
              <Typography sx={{ fontSize: draft.ui_font_size, mb: 2 }}>
                {t("appearance.preview.text")}
              </Typography>
              <TextField
                label={t("appearance.preview.field")}
                value={t("appearance.preview.value")}
                fullWidth
                slotProps={{
                  htmlInput: {
                    readOnly: true,
                    style: { fontSize: draft.ui_font_size },
                  },
                  input: { sx: { fontSize: draft.ui_font_size } },
                  inputLabel: { sx: { fontSize: draft.ui_font_size } },
                }}
              />
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 2 }}>
                <MuiButton
                  type="button"
                  sx={{ fontSize: draft.ui_font_size * 0.875 }}
                >
                  {t("appearance.preview.primary")}
                </MuiButton>
                <MuiButton
                  type="button"
                  color="secondary"
                  variant="outlined"
                  sx={{ fontSize: draft.ui_font_size * 0.875 }}
                >
                  {t("appearance.preview.secondary")}
                </MuiButton>
              </Box>
            </Panel>
          </Box>
        </ThemeProvider>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          <Button disabled={mutation.isPending || sameAppearance(draft, saved)}>
            {t("appearance.save")}
          </Button>
          <Button
            type="button"
            disabled={mutation.isPending}
            onClick={() => edit(defaultAppearance)}
          >
            {t("appearance.reset")}
          </Button>
        </Box>
        {mutation.isError && <ErrorMessage error={mutation.error} />}
        {mutation.isSuccess && (
          <Alert severity="success" role="status">
            {t("appearance.saved")}
          </Alert>
        )}
      </Form>
    </Panel>
  );
}
