import { useEffect, useState } from "react";
import { I18nextProvider, useTranslation } from "react-i18next";
import { i18n } from "./i18n";
import { isLanguage, languages, maxShareBytes } from "./config";
import {
  clearShare,
  readShare,
  readAttempt,
  clearAttempt,
  type StoredShare,
  type ShareAttempt,
} from "./storage";
import { registerWorker } from "./register";
import { parseError, type ErrorCode } from "./share";

function Receipt() {
  const { t, i18n: translator } = useTranslation();
  const [ready, setReady] = useState(false);
  const [workerFailed, setWorkerFailed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);
  const [share, setShare] = useState<StoredShare | null>(null);
  const [attempt, setAttempt] = useState<ShareAttempt | null>(null);
  const [attemptLoading, setAttemptLoading] = useState(true);
  const [attemptReadFailed, setAttemptReadFailed] = useState(false);
  const [clearingAttempt, setClearingAttempt] = useState(false);
  const [error, setError] = useState<ErrorCode | null>(() =>
    parseError(new URLSearchParams(window.location.search).get("error")),
  );

  useEffect(() => {
    let active = true;
    void readAttempt()
      .then((value) => {
        if (active) {
          setAttempt(value);
          setAttemptLoading(false);
        }
      })
      .catch(() => {
        if (active) {
          setError("STORAGE_FAILED");
          setAttemptReadFailed(true);
          setAttemptLoading(false);
        }
      });
    void readShare()
      .then((value) => {
        if (active) {
          setShare(value);
          setLoading(false);
        }
      })
      .catch(() => {
        if (active) {
          setError("STORAGE_FAILED");
          setLoading(false);
        }
      });
    void registerWorker()
      .then(() => {
        if (active) setReady(true);
      })
      .catch(() => {
        if (active) setWorkerFailed(true);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    document.documentElement.lang = translator.language;
    document.title = t("appTitle");
  }, [t, translator.language]);

  async function clear() {
    setClearing(true);
    try {
      await clearShare();
      setShare(null);
      setError(null);
      window.history.replaceState({}, "", window.location.pathname);
    } catch {
      setError("STORAGE_FAILED");
    } finally {
      setClearing(false);
    }
  }

  const numbers = new Intl.NumberFormat(translator.language);
  async function clearDiagnostics() {
    setClearingAttempt(true);
    try {
      await clearAttempt();
      setAttempt(null);
    } catch {
      setError("STORAGE_FAILED");
    } finally {
      setClearingAttempt(false);
    }
  }

  return (
    <main>
      <h1>{t("appTitle")}</h1>
      <label htmlFor="language">{t("language")}</label>{" "}
      <select
        id="language"
        value={translator.language}
        onChange={(event) => {
          if (isLanguage(event.target.value))
            void translator.changeLanguage(event.target.value);
        }}
      >
        {languages.map((language) => (
          <option key={language} value={language}>
            {t(`language.${language}`)}
          </option>
        ))}
      </select>
      <p>{t("privacy")}</p>
      <p>{t("instructions")}</p>
      <p>{t("limit", { bytes: numbers.format(maxShareBytes) })}</p>
      {workerFailed ? (
        <p role="alert">{t("errors.WORKER_FAILED")}</p>
      ) : (
        <p role="status">{t(ready ? "ready" : "starting")}</p>
      )}
      {error && <p role="alert">{t(`errors.${error}`)}</p>}
      {loading ? (
        <p>{t("loading")}</p>
      ) : share ? (
        <section>
          <h2>{t("stored")}</h2>
          <dl>
            <dt>{t("name")}</dt>
            <dd>{share.name}</dd>
            <dt>{t("type")}</dt>
            <dd>{share.type || t("unknownType")}</dd>
            <dt>{t("size")}</dt>
            <dd>{numbers.format(share.size)}</dd>
            <dt>{t("received")}</dt>
            <dd>
              {new Intl.DateTimeFormat(translator.language, {
                dateStyle: "medium",
                timeStyle: "medium",
              }).format(share.receivedAt)}
            </dd>
          </dl>
          <button
            disabled={clearing}
            onClick={() => {
              void clear();
            }}
          >
            {t(clearing ? "clearing" : "clear")}
          </button>
        </section>
      ) : (
        <p>{t("empty")}</p>
      )}
      <section aria-labelledby="diagnostics-heading">
        <h2 id="diagnostics-heading">{t("diagnostics.heading")}</h2>
        <p>{t("diagnostics.privacy")}</p>
        {attemptLoading ? (
          <p>{t("loading")}</p>
        ) : attemptReadFailed ? null : attempt ? (
          <>
            <dl>
              <dt>{t("received")}</dt>
              <dd>
                {new Intl.DateTimeFormat(translator.language, {
                  dateStyle: "medium",
                  timeStyle: "medium",
                }).format(attempt.receivedAt)}
              </dd>
              <dt>{t("diagnostics.outcome")}</dt>
              <dd>
                {t(
                  attempt.outcome === "RECEIVED"
                    ? "diagnostics.received"
                    : `errors.${attempt.outcome}`,
                )}
              </dd>
              <dt>{t("diagnostics.fileCount")}</dt>
              <dd>
                {numbers.format(
                  attempt.fields.filter((field) => field.kind === "file")
                    .length,
                )}
              </dd>
            </dl>
            {attempt.fields.length === 0 ? (
              <p>{t("diagnostics.noFields")}</p>
            ) : (
              <ol>
                {attempt.fields.map((field, index) => (
                  <li key={index}>
                    <p>
                      {t("diagnostics.field", {
                        label: t(`diagnostics.fields.${field.field}`),
                      })}
                    </p>
                    <p>
                      {field.kind === "file"
                        ? t("diagnostics.file", {
                            type: field.type || t("unknownType"),
                            bytes: numbers.format(field.size),
                          })
                        : t(
                            field.nonempty
                              ? "diagnostics.textPresent"
                              : "diagnostics.textEmpty",
                          )}
                    </p>
                  </li>
                ))}
              </ol>
            )}
            <button
              disabled={clearingAttempt}
              onClick={() => {
                void clearDiagnostics();
              }}
            >
              {t(clearingAttempt ? "clearing" : "diagnostics.clear")}
            </button>
          </>
        ) : (
          <p>{t("diagnostics.empty")}</p>
        )}
      </section>
    </main>
  );
}

export function App() {
  return (
    <I18nextProvider i18n={i18n}>
      <Receipt />
    </I18nextProvider>
  );
}
