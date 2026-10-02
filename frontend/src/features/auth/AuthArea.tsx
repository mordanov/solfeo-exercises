import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  ApiError,
  fetchMe,
  login,
  logout,
  changePassword,
  type Auth,
} from "../../api/auth";
import { isLanguage } from "../../configuration";
import { SettingsForm } from "../settings/SettingsForm";
import { Users } from "../users/Users";
import { Exercises } from "../exercises/Exercises";
import { Listening } from "../listening/Listening";
import { Journal } from "../journal/Journal";
import { Telegram } from "../telegram/Telegram";
import { finishPlayback } from "../listening/tracker";
import { ErrorMessage, LanguageOptions } from "../../components/AccountUi";
import { Button, Field, Form, Input, Panel, Select } from "../../components/Ui";
import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Alert from "@mui/material/Alert";
import { useAppearance } from "../../theme";
import { defaultAppearance } from "../../appearance";

function LoginForm({ onLogin }: { onLogin: (value: Auth) => void }) {
  const { t, i18n } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const mutation = useMutation({
    mutationFn: () => login(username, password),
    onSuccess: onLogin,
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }
  return (
    <Panel sx={{ maxWidth: 640, mx: "auto" }}>
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
      <Box component="h2" sx={{ mt: 3 }}>
        {t("auth.login")}
      </Box>
      <Form onSubmit={submit}>
        <Field>
          {t("auth.username")}
          <Input
            required
            autoComplete="username"
            maxLength={64}
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </Field>
        <Field>
          {t("auth.password")}
          <Input
            required
            type="password"
            autoComplete="current-password"
            maxLength={256}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>
        <Button disabled={mutation.isPending}>
          {t(mutation.isPending ? "common.saving" : "auth.login")}
        </Button>
        {mutation.isError && <ErrorMessage error={mutation.error} />}
      </Form>
    </Panel>
  );
}

export function PasswordForm({
  auth,
  onChange,
}: {
  auth: Auth;
  onChange: (value: Auth) => void;
}) {
  const { t } = useTranslation();
  const [current, setCurrent] = useState("");
  const [replacement, setReplacement] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [mismatch, setMismatch] = useState(false);
  const mutation = useMutation({
    mutationFn: () => changePassword(auth.csrf_token, current, replacement),
    onSuccess: (value) => {
      setCurrent("");
      setReplacement("");
      setConfirmation("");
      onChange(value);
    },
  });
  return (
    <Panel>
      <h2>{t("auth.changePassword")}</h2>
      {auth.user.must_change_password && (
        <Alert severity="info" role="status">
          {t("auth.changeRequired")}
        </Alert>
      )}
      <Form
        onSubmit={(event) => {
          event.preventDefault();
          setMismatch(replacement !== confirmation);
          if (replacement === confirmation) mutation.mutate();
        }}
      >
        <Field>
          {t("auth.currentPassword")}
          <Input
            required
            type="password"
            autoComplete="current-password"
            maxLength={256}
            value={current}
            onChange={(event) => setCurrent(event.target.value)}
          />
        </Field>
        <Field>
          {t("auth.newPassword")}
          <Input
            required
            type="password"
            autoComplete="new-password"
            maxLength={256}
            value={replacement}
            onChange={(event) => setReplacement(event.target.value)}
          />
        </Field>
        <Field>
          {t("auth.confirmPassword")}
          <Input
            required
            type="password"
            autoComplete="new-password"
            maxLength={256}
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
          />
        </Field>
        <p>{t("auth.passwordHint")}</p>
        <Button disabled={mutation.isPending}>
          {t("auth.changePassword")}
        </Button>
        {mismatch && <ErrorMessage error={new ApiError("PASSWORD_MISMATCH")} />}
        {mutation.isError && <ErrorMessage error={mutation.error} />}
        {mutation.isSuccess && (
          <Alert severity="success" role="status">
            {t("auth.passwordChanged")}
          </Alert>
        )}
      </Form>
    </Panel>
  );
}

export function AuthArea() {
  const { t, i18n } = useTranslation();
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: ["auth"],
    queryFn: ({ signal }) => fetchMe(signal),
    retry: false,
  });
  const auth = query.data;
  const { setAppearance } = useAppearance();
  const lightScheme = auth?.user.light_scheme ?? defaultAppearance.light_scheme;
  const darkScheme = auth?.user.dark_scheme ?? defaultAppearance.dark_scheme;
  const font = auth?.user.ui_font ?? defaultAppearance.ui_font;
  const fontSize = auth?.user.ui_font_size ?? defaultAppearance.ui_font_size;
  useEffect(() => {
    setAppearance({
      light_scheme: lightScheme,
      dark_scheme: darkScheme,
      ui_font: font,
      ui_font_size: fontSize,
    });
  }, [setAppearance, lightScheme, darkScheme, font, fontSize]);
  const language = auth?.user.ui_language;
  useEffect(() => {
    if (language) void i18n.changeLanguage(language);
  }, [language, i18n]);
  useEffect(() => {
    const expired = async () => {
      await cache.cancelQueries({ queryKey: ["auth"] });
      await cache.cancelQueries({ queryKey: ["users"] });
      await cache.cancelQueries({ queryKey: ["exercises"] });
      await cache.cancelQueries({ queryKey: ["listening"] });
      await cache.cancelQueries({ queryKey: ["journal"] });
      await cache.cancelQueries({ queryKey: ["journal-options"] });
      await cache.cancelQueries({ queryKey: ["telegram"] });
      await cache.cancelQueries({ queryKey: ["omr"] });
      cache.setQueryData(["auth"], null);
      cache.removeQueries({ queryKey: ["users"] });
      cache.removeQueries({ queryKey: ["exercises"] });
      cache.removeQueries({ queryKey: ["listening"] });
      cache.removeQueries({ queryKey: ["journal"] });
      cache.removeQueries({ queryKey: ["journal-options"] });
      cache.removeQueries({ queryKey: ["telegram"] });
      cache.removeQueries({ queryKey: ["omr"] });
    };
    const listener = () => void expired();
    window.addEventListener("solfeo:unauthorized", listener);
    return () => window.removeEventListener("solfeo:unauthorized", listener);
  }, [cache]);
  const onAuth = async (value: Auth) => {
    await cache.cancelQueries({ queryKey: ["auth"] });
    await cache.cancelQueries({ queryKey: ["users"] });
    await cache.cancelQueries({ queryKey: ["exercises"] });
    await cache.cancelQueries({ queryKey: ["listening"] });
    await cache.cancelQueries({ queryKey: ["journal"] });
    await cache.cancelQueries({ queryKey: ["journal-options"] });
    await cache.cancelQueries({ queryKey: ["telegram"] });
    await cache.cancelQueries({ queryKey: ["omr"] });
    cache.removeQueries({ queryKey: ["users"] });
    cache.removeQueries({ queryKey: ["exercises"] });
    cache.removeQueries({ queryKey: ["listening"] });
    cache.removeQueries({ queryKey: ["journal"] });
    cache.removeQueries({ queryKey: ["journal-options"] });
    cache.removeQueries({ queryKey: ["telegram"] });
    cache.removeQueries({ queryKey: ["omr"] });
    cache.setQueryData(["auth"], value);
  };
  const signOut = useMutation({
    mutationFn: async () => {
      await finishPlayback();
      await logout(auth?.csrf_token ?? "");
    },
    onSuccess: async () => {
      await cache.cancelQueries({ queryKey: ["auth"] });
      await cache.cancelQueries({ queryKey: ["users"] });
      await cache.cancelQueries({ queryKey: ["exercises"] });
      await cache.cancelQueries({ queryKey: ["listening"] });
      await cache.cancelQueries({ queryKey: ["journal"] });
      await cache.cancelQueries({ queryKey: ["journal-options"] });
      await cache.cancelQueries({ queryKey: ["telegram"] });
      await cache.cancelQueries({ queryKey: ["omr"] });
      cache.setQueryData(["auth"], null);
      cache.removeQueries({ queryKey: ["users"] });
      cache.removeQueries({ queryKey: ["exercises"] });
      cache.removeQueries({ queryKey: ["listening"] });
      cache.removeQueries({ queryKey: ["journal"] });
      cache.removeQueries({ queryKey: ["journal-options"] });
      cache.removeQueries({ queryKey: ["telegram"] });
      cache.removeQueries({ queryKey: ["omr"] });
    },
  });
  if (query.isPending) return <p aria-live="polite">{t("auth.loading")}</p>;
  if (query.isError)
    return (
      <Panel>
        <ErrorMessage error={query.error} />
        <Button onClick={() => void query.refetch()}>
          {t("common.retry")}
        </Button>
      </Panel>
    );
  if (!auth) return <LoginForm onLogin={onAuth} />;
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  const managerPath =
    path === "/manager/users" ||
    ((path === "/" || path === "/login") && auth.user.role === "manager");
  return (
    <Box component="section">
      <p>
        {t("auth.signedIn", {
          name: `${auth.user.first_name} ${auth.user.last_name}`,
        })}
      </p>
      <Box
        component="nav"
        aria-label={t("nav.label")}
        sx={{
          display: { xs: "grid", sm: "flex" },
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          flexWrap: "wrap",
          alignItems: "center",
          gap: { xs: 1, sm: 2 },
          my: 2,
          p: { xs: 1.5, sm: 2 },
          bgcolor: "background.paper",
          borderRadius: 1,
          boxShadow: 1,
          "& a": {
            py: 1,
            fontWeight: 500,
            minWidth: 0,
            display: { xs: "flex", sm: "inline" },
            alignItems: "center",
            minHeight: { xs: 44, sm: "auto" },
            px: { xs: 1, sm: 0 },
          },
          "& > button": { gridColumn: "1 / -1" },
        }}
      >
        {!auth.user.must_change_password && (
          <>
            {auth.user.role === "manager" && (
              <>
                <Link href="/manager/exercises">{t("exercises.title")}</Link>
                <Link href="/manager/journal">{t("journal.title")}</Link>
                <Link href="/manager/telegram">{t("telegram.title")}</Link>
              </>
            )}
            <Link
              href={
                auth.user.role === "manager" ? "/manager/users" : "/student"
              }
            >
              {t(
                auth.user.role === "manager" ? "users.title" : "student.title",
              )}
            </Link>{" "}
            <Link href="/settings">{t("settings.title")}</Link>{" "}
          </>
        )}
        <Button disabled={signOut.isPending} onClick={() => signOut.mutate()}>
          {t("auth.logout")}
        </Button>
      </Box>
      {signOut.isError && <ErrorMessage error={signOut.error} />}
      {auth.user.must_change_password ? (
        <PasswordForm auth={auth} onChange={onAuth} />
      ) : path === "/settings" ? (
        <>
          <SettingsForm
            auth={auth}
            onChange={(user) => onAuth({ ...auth, user })}
          />
          {auth.user.is_emergency ? (
            <p>{t("auth.emergencyHint")}</p>
          ) : (
            <PasswordForm auth={auth} onChange={onAuth} />
          )}
        </>
      ) : path === "/manager/telegram" ? (
        auth.user.role === "manager" ? (
          <Telegram auth={auth} />
        ) : (
          <ErrorMessage error={new ApiError("FORBIDDEN")} />
        )
      ) : path === "/manager/journal" ? (
        auth.user.role === "manager" ? (
          <Journal />
        ) : (
          <ErrorMessage error={new ApiError("FORBIDDEN")} />
        )
      ) : path === "/manager/exercises" ? (
        auth.user.role === "manager" ? (
          <Exercises auth={auth} />
        ) : (
          <ErrorMessage error={new ApiError("FORBIDDEN")} />
        )
      ) : managerPath ? (
        auth.user.role === "manager" ? (
          <Users auth={auth} />
        ) : (
          <ErrorMessage error={new ApiError("FORBIDDEN")} />
        )
      ) : path === "/" || path === "/student" || path === "/login" ? (
        auth.user.role === "student" ? (
          <Listening auth={auth} />
        ) : (
          <ErrorMessage error={new ApiError("FORBIDDEN")} />
        )
      ) : (
        <ErrorMessage error={new ApiError("NOT_FOUND")} />
      )}
    </Box>
  );
}
