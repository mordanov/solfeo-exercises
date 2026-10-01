import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError, type Auth } from "../../api/auth";
import { listExercises, type Exercise } from "../../api/exercises";
import * as api from "../../api/telegram";
import { ErrorMessage } from "../../components/AccountUi";
import {
  Button,
  Field,
  Form,
  Input,
  Panel,
  Select,
  Textarea,
} from "../../components/Ui";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Chip from "@mui/material/Chip";

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
    <Panel component="article">
      <h3>{item.title || t("telegram.untitled")}</h3>
      <p>
        {new Intl.DateTimeFormat(i18n.language, {
          dateStyle: "medium",
          timeStyle: "short",
        }).format(new Date(item.received_at))}
      </p>
      <Chip label={t(`telegram.status.${item.status}`)} sx={{ mb: 2 }} />
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
        <Form onSubmit={submit}>
          <Field>
            {t("telegram.destination")}
            <Select
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
            </Select>
          </Field>
          <Field>
            {t("exercises.name")}
            <Input
              required
              maxLength={200}
              value={title}
              disabled={save.isPending}
              onChange={(event) => setTitle(event.target.value)}
            />
          </Field>
          <Field>
            {t("exercises.description")}
            <Textarea
              maxLength={10000}
              value={description}
              disabled={save.isPending}
              onChange={(event) => setDescription(event.target.value)}
            />
          </Field>
          {selected?.audio && (
            <Field>
              <Input
                type="checkbox"
                required
                checked={confirm}
                onChange={(event) => setConfirm(event.target.checked)}
              />
              {t("telegram.replaceConfirm")}
            </Field>
          )}
          <Button
            disabled={
              save.isPending || !title.trim() || (!!selected?.audio && !confirm)
            }
          >
            {t("telegram.save")}
          </Button>
        </Form>
      )}
      {(save.isSuccess || item.status === "applied") && (
        <Alert severity="success" role="status">
          {t("telegram.saved")}
        </Alert>
      )}
      {save.isError && <ErrorMessage error={save.error} />}
      {item.status === "failed" && (
        <Button disabled={retry.isPending} onClick={() => retry.mutate()}>
          {t("common.retry")}
        </Button>
      )}
      {retry.isError && <ErrorMessage error={retry.error} />}
    </Panel>
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
    <Panel>
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
            <Alert severity="warning">{t("telegram.unavailable")}</Alert>
          )}
          <Link
            href={`https://t.me/${connection.data.bot_username}`}
            target="_blank"
            rel="noreferrer"
          >
            {t("telegram.openBot")}
          </Link>
          <Button
            disabled={code.isPending || disconnect.isPending}
            onClick={() => code.mutate()}
          >
            {t("telegram.code")}
          </Button>
          <Button
            disabled={disconnect.isPending || code.isPending}
            onClick={() => disconnect.mutate()}
          >
            {t("telegram.unlink")}
          </Button>
        </>
      )}
      {code.data && (
        <Box sx={{ p: 2, my: 2, bgcolor: "action.hover", borderRadius: 2 }}>
          <p>{t("telegram.codeHint")}</p>
          <Box
            component="code"
            sx={{ userSelect: "all", overflowWrap: "anywhere" }}
          >{`/start ${code.data.code}`}</Box>
          <p>
            {t("telegram.expires", {
              time: new Intl.DateTimeFormat(i18n.language, {
                timeStyle: "short",
              }).format(new Date(code.data.expires_at)),
            })}
          </p>
        </Box>
      )}
      {code.isError && <ErrorMessage error={code.error} />}
      {disconnect.isError && <ErrorMessage error={disconnect.error} />}
      <Button
        disabled={imports.isFetching || connection.isFetching}
        onClick={() => void refresh()}
      >
        {t("telegram.refresh")}
      </Button>
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
          <Button
            disabled={offset === 0 || imports.isFetching}
            onClick={() => setOffset(Math.max(0, offset - 50))}
          >
            {t("common.previous")}
          </Button>
          <Button
            disabled={offset + 50 >= imports.data.total || imports.isFetching}
            onClick={() => setOffset(offset + 50)}
          >
            {t("common.next")}
          </Button>
        </>
      )}
    </Panel>
  );
}
