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
      <h2>{t("auth.login")}</h2>
      <form onSubmit={submit}>
        <label>
          {t("auth.username")}
          <input
            required
            autoComplete="username"
            maxLength={64}
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>
        <label>
          {t("auth.password")}
          <input
            required
            type="password"
            autoComplete="current-password"
            maxLength={256}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <button disabled={mutation.isPending}>
          {t(mutation.isPending ? "common.saving" : "auth.login")}
        </button>
        {mutation.isError && <ErrorMessage error={mutation.error} />}
      </form>
    </section>
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
    <section>
      <h2>{t("auth.changePassword")}</h2>
      {auth.user.must_change_password && <p>{t("auth.changeRequired")}</p>}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setMismatch(replacement !== confirmation);
          if (replacement === confirmation) mutation.mutate();
        }}
      >
        <label>
          {t("auth.currentPassword")}
          <input
            required
            type="password"
            autoComplete="current-password"
            maxLength={256}
            value={current}
            onChange={(event) => setCurrent(event.target.value)}
          />
        </label>
        <label>
          {t("auth.newPassword")}
          <input
            required
            type="password"
            autoComplete="new-password"
            maxLength={256}
            value={replacement}
            onChange={(event) => setReplacement(event.target.value)}
          />
        </label>
        <label>
          {t("auth.confirmPassword")}
          <input
            required
            type="password"
            autoComplete="new-password"
            maxLength={256}
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
          />
        </label>
        <p>{t("auth.passwordHint")}</p>
        <button disabled={mutation.isPending}>
          {t("auth.changePassword")}
        </button>
        {mismatch && <ErrorMessage error={new ApiError("PASSWORD_MISMATCH")} />}
        {mutation.isError && <ErrorMessage error={mutation.error} />}
        {mutation.isSuccess && <p role="status">{t("auth.passwordChanged")}</p>}
      </form>
    </section>
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
      <section>
        <ErrorMessage error={query.error} />
        <button onClick={() => void query.refetch()}>
          {t("common.retry")}
        </button>
      </section>
    );
  if (!auth) return <LoginForm onLogin={onAuth} />;
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  const managerPath =
    path === "/manager/users" ||
    ((path === "/" || path === "/login") && auth.user.role === "manager");
  return (
    <section>
      <p>
        {t("auth.signedIn", {
          name: `${auth.user.first_name} ${auth.user.last_name}`,
        })}
      </p>
      <nav aria-label={t("nav.label")}>
        {!auth.user.must_change_password && (
          <>
            {auth.user.role === "manager" && (
              <>
                <a href="/manager/exercises">{t("exercises.title")}</a>
                <a href="/manager/journal">{t("journal.title")}</a>
                <a href="/manager/telegram">{t("telegram.title")}</a>
              </>
            )}
            <a
              href={
                auth.user.role === "manager" ? "/manager/users" : "/student"
              }
            >
              {t(
                auth.user.role === "manager" ? "users.title" : "student.title",
              )}
            </a>{" "}
            <a href="/settings">{t("settings.title")}</a>{" "}
          </>
        )}
        <button disabled={signOut.isPending} onClick={() => signOut.mutate()}>
          {t("auth.logout")}
        </button>
      </nav>
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
    </section>
  );
}
