import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError, type Auth } from "../../api/auth";
import { listExercises, type Exercise } from "../../api/exercises";
import * as api from "../../api/telegram";
import { ErrorMessage } from "../../components/AccountUi";

function ImportRow({
  item,
  auth,
  exercises,
  refresh,
}: {
  item: api.Import;
  auth: Auth;
  exercises: Exercise[];
  refresh: () => Promise<void>;
}) {
  const { t, i18n } = useTranslation();
  const [target, setTarget] = useState("");
  const [title, setTitle] = useState(item.title);
  const [description, setDescription] = useState(item.description);
  const [confirm, setConfirm] = useState(false);
  const selected = exercises.find((exercise) => String(exercise.id) === target);
  const save = useMutation({
    mutationFn: () =>
      api.applyImport(auth.csrf_token, item.id, {
        exercise_id: target ? Number(target) : null,
        title,
        description,
      }),
    onSuccess: refresh,
  });
  const retry = useMutation({
    mutationFn: () => api.retryImport(auth.csrf_token, item.id),
    onSuccess: refresh,
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }
  return (
    <article>
      <h3>{item.title || t("telegram.untitled")}</h3>
      <p>
        {new Intl.DateTimeFormat(i18n.language, {
          dateStyle: "medium",
          timeStyle: "short",
        }).format(new Date(item.received_at))}
      </p>
      <p>{t(`telegram.status.${item.status}`)}</p>
      {item.last_error && (
        <ErrorMessage error={new ApiError(item.last_error)} />
      )}
      {(item.status === "ready" || item.status === "applied") && (
        <audio
          controls
          preload="metadata"
          src={`/api/telegram/imports/${item.id}/audio`}
          aria-label={t("telegram.preview")}
        />
      )}
      {item.status === "ready" && !save.isSuccess && (
        <form onSubmit={submit}>
          <label>
            {t("telegram.destination")}
            <select
              value={target}
              disabled={save.isPending}
              onChange={(event) => {
                const value = event.target.value;
                const exercise = exercises.find(
                  (row) => String(row.id) === value,
                );
                setTarget(value);
                setConfirm(false);
                setTitle(exercise?.title ?? item.title);
                setDescription(exercise?.description ?? item.description);
              }}
            >
              <option value="">{t("telegram.create")}</option>
              {exercises.map((exercise) => (
                <option key={exercise.id} value={exercise.id}>
                  {exercise.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("exercises.name")}
            <input
              required
              maxLength={200}
              value={title}
              disabled={save.isPending}
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>
          <label>
            {t("exercises.description")}
            <textarea
              maxLength={10000}
              value={description}
              disabled={save.isPending}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
          {selected?.audio && (
            <label>
              <input
                type="checkbox"
                required
                checked={confirm}
                onChange={(event) => setConfirm(event.target.checked)}
              />
              {t("telegram.replaceConfirm")}
            </label>
          )}
          <button
            disabled={
              save.isPending || !title.trim() || (!!selected?.audio && !confirm)
            }
          >
            {t("telegram.save")}
          </button>
        </form>
      )}
      {(save.isSuccess || item.status === "applied") && (
        <p role="status">{t("telegram.saved")}</p>
      )}
      {save.isError && <ErrorMessage error={save.error} />}
      {item.status === "failed" && (
        <button disabled={retry.isPending} onClick={() => retry.mutate()}>
          {t("common.retry")}
        </button>
      )}
      {retry.isError && <ErrorMessage error={retry.error} />}
    </article>
  );
}

export function Telegram({ auth }: { auth: Auth }) {
  const { t, i18n } = useTranslation();
  const cache = useQueryClient();
  const [offset, setOffset] = useState(0);
  const connection = useQuery({
    queryKey: ["telegram", "status"],
    queryFn: ({ signal }) => api.status(signal),
  });
  const imports = useQuery({
    queryKey: ["telegram", "imports", offset],
    queryFn: ({ signal }) => api.listImports(offset, signal),
  });
  const exercises = useQuery({
    queryKey: ["exercises"],
    queryFn: ({ signal }) => listExercises(signal),
  });
  const refresh = async () => {
    await cache.invalidateQueries({ queryKey: ["telegram"] });
    await cache.invalidateQueries({ queryKey: ["exercises"] });
  };
  const code = useMutation({
    mutationFn: () => api.createCode(auth.csrf_token),
  });
  const disconnect = useMutation({
    mutationFn: () => api.unlink(auth.csrf_token),
    onSuccess: async () => {
      code.reset();
      await refresh();
    },
  });
  return (
    <section>
      <h2>{t("telegram.title")}</h2>
      <p>{t("telegram.help")}</p>
      {connection.isError && <ErrorMessage error={connection.error} />}
      {connection.data && (
        <>
          <p>
            {t(
              connection.data.linked ? "telegram.linked" : "telegram.unlinked",
            )}
          </p>
          {!connection.data.available && (
            <p role="alert">{t("telegram.unavailable")}</p>
          )}
          <a
            href={`https://t.me/${connection.data.bot_username}`}
            target="_blank"
            rel="noreferrer"
          >
            {t("telegram.openBot")}
          </a>
          <button
            disabled={code.isPending || disconnect.isPending}
            onClick={() => code.mutate()}
          >
            {t("telegram.code")}
          </button>
          <button
            disabled={disconnect.isPending || code.isPending}
            onClick={() => disconnect.mutate()}
          >
            {t("telegram.unlink")}
          </button>
        </>
      )}
      {code.data && (
        <div>
          <p>{t("telegram.codeHint")}</p>
          <code>{`/start ${code.data.code}`}</code>
          <p>
            {t("telegram.expires", {
              time: new Intl.DateTimeFormat(i18n.language, {
                timeStyle: "short",
              }).format(new Date(code.data.expires_at)),
            })}
          </p>
        </div>
      )}
      {code.isError && <ErrorMessage error={code.error} />}
      {disconnect.isError && <ErrorMessage error={disconnect.error} />}
      <button
        disabled={imports.isFetching || connection.isFetching}
        onClick={() => void refresh()}
      >
        {t("telegram.refresh")}
      </button>
      {imports.isError && <ErrorMessage error={imports.error} />}
      {exercises.isError && <ErrorMessage error={exercises.error} />}
      {imports.data && (
        <>
          <p>{t("telegram.total", { count: imports.data.total })}</p>
          {imports.data.imports.map((item) => (
            <ImportRow
              key={item.id}
              item={item}
              auth={auth}
              exercises={exercises.data?.exercises ?? []}
              refresh={refresh}
            />
          ))}
          <button
            disabled={offset === 0 || imports.isFetching}
            onClick={() => setOffset(Math.max(0, offset - 50))}
          >
            {t("common.previous")}
          </button>
          <button
            disabled={offset + 50 >= imports.data.total || imports.isFetching}
            onClick={() => setOffset(offset + 50)}
          >
            {t("common.next")}
          </button>
        </>
      )}
    </section>
  );
}
