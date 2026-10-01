import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError, type Auth } from "../../api/auth";
import {
  deleteExercise,
  listExercises,
  reorderExercises,
  saveExercise,
  type Exercise,
} from "../../api/exercises";
import { ErrorMessage } from "../../components/AccountUi";
import { Review } from "../omr/Review";
import {
  Button,
  Field,
  Form,
  Input,
  Panel,
  Textarea,
} from "../../components/Ui";
import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";

function ExerciseForm({
  auth,
  exercise,
  close,
}: {
  auth: Auth;
  exercise: Exercise | null;
  close: () => void;
}) {
  const { t, i18n } = useTranslation();
  const cache = useQueryClient();
  const [title, setTitle] = useState(exercise?.title ?? "");
  const [description, setDescription] = useState(exercise?.description ?? "");
  const [category, setCategory] = useState(exercise?.category ?? "");
  const [image, setImage] = useState<File>();
  const [audio, setAudio] = useState<File>();
  const [removeImage, setRemoveImage] = useState(false);
  const [removeAudio, setRemoveAudio] = useState(false);
  const [progress, setProgress] = useState(0);
  const [validation, setValidation] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const mutation = useMutation({
    mutationFn: () => {
      const data = new FormData();
      data.set("title", title);
      data.set("description", description);
      data.set("category", category);
      data.set("remove_image", String(removeImage));
      data.set("remove_audio", String(removeAudio));
      if (image) data.set("image", image);
      if (audio) data.set("audio", audio);
      controller.current = new AbortController();
      return saveExercise(
        auth.csrf_token,
        exercise?.id ?? null,
        data,
        setProgress,
        controller.current.signal,
      );
    },
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ["exercises"] });
      close();
    },
  });
  return (
    <Form
      onSubmit={(event) => {
        event.preventDefault();
        const missing = !(
          image ||
          (!removeImage && exercise?.image) ||
          audio ||
          (!removeAudio && exercise?.audio)
        );
        setValidation(missing);
        if (!missing) {
          setProgress(0);
          mutation.mutate();
        }
      }}
    >
      <h3>{t(exercise ? "exercises.edit" : "exercises.create")}</h3>
      <Box
        component="fieldset"
        disabled={mutation.isPending}
        sx={{ border: 0, p: 0, m: 0, minWidth: 0, display: "grid", gap: 2 }}
      >
        <Field>
          {t("exercises.name")}
          <Input
            required
            maxLength={200}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </Field>
        <Field>
          {t("exercises.description")}
          <Textarea
            maxLength={10000}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Field>
        <Field>
          {t("exercises.category")}
          <Input
            maxLength={100}
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          />
        </Field>
        <Field>
          {t("exercises.image")}
          <Input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            disabled={removeImage}
            onChange={(e) => setImage(e.target.files?.[0])}
          />
        </Field>
        {exercise?.image && (
          <Field>
            <Input
              type="checkbox"
              checked={removeImage}
              disabled={!!image}
              onChange={(e) => setRemoveImage(e.target.checked)}
            />
            {t("exercises.removeImage")}
          </Field>
        )}
        <Field>
          {t("exercises.audio")}
          <Input
            type="file"
            disabled={removeAudio}
            onChange={(e) => setAudio(e.target.files?.[0])}
          />
        </Field>
        {exercise?.audio && (
          <Field>
            <Input
              type="checkbox"
              checked={removeAudio}
              disabled={!!audio}
              onChange={(e) => setRemoveAudio(e.target.checked)}
            />
            {t("exercises.removeAudio")}
          </Field>
        )}
        <p>{t("exercises.fileHint")}</p>
        <Button>{t("exercises.save")}</Button>{" "}
        <Button type="button" onClick={close}>
          {t("common.close")}
        </Button>
      </Box>
      {mutation.isPending && (
        <div role="status">
          <p>{t("exercises.uploading")}</p>
          <LinearProgress
            aria-label={t("exercises.uploading")}
            variant="determinate"
            value={progress}
            sx={{ height: 8, borderRadius: 1, mb: 1 }}
          />
          {new Intl.NumberFormat(i18n.language, { style: "percent" }).format(
            progress / 100,
          )}
          {progress === 100 && <p>{t("exercises.processing")}</p>}
        </div>
      )}
      {validation && (
        <ErrorMessage error={new ApiError("EXERCISE_MEDIA_REQUIRED")} />
      )}
      {mutation.isError && <ErrorMessage error={mutation.error} />}
    </Form>
  );
}

function Preview({ exercise }: { exercise: Exercise }) {
  const { t, i18n } = useTranslation();
  const [failed, setFailed] = useState(false);
  return (
    <>
      {exercise.image && (
        <Box
          component="img"
          sx={{
            display: "block",
            maxWidth: "100%",
            maxHeight: 400,
            objectFit: "contain",
            my: 2,
            bgcolor: "#fff",
            borderRadius: 2,
          }}
          loading="lazy"
          alt={t("exercises.imageFor", { title: exercise.title })}
          src={`/api/exercises/${exercise.id}/files/image`}
          onError={() => setFailed(true)}
        />
      )}
      {exercise.audio && (
        <>
          <audio
            controls
            preload="none"
            aria-label={t("exercises.audioFor", { title: exercise.title })}
            src={`/api/exercises/${exercise.id}/files/audio`}
            onError={() => setFailed(true)}
          />
          <p>
            {t("exercises.duration", {
              seconds: new Intl.NumberFormat(i18n.language, {
                maximumFractionDigits: 1,
              }).format(exercise.audio.duration_seconds ?? 0),
            })}
          </p>
        </>
      )}
      {failed && <ErrorMessage error={new ApiError("MEDIA_PLAYBACK_ERROR")} />}
    </>
  );
}

export function Exercises({ auth }: { auth: Auth }) {
  const { t, i18n } = useTranslation();
  const cache = useQueryClient();
  const [editing, setEditing] = useState<Exercise | null | undefined>();
  const [deleting, setDeleting] = useState<number | null>(null);
  const [reviewing, setReviewing] = useState<number | null>(null);
  const query = useQuery({
    queryKey: ["exercises"],
    queryFn: ({ signal }) => listExercises(signal),
    retry: false,
  });
  const refreshed = async () => {
    setDeleting(null);
    await cache.invalidateQueries({ queryKey: ["exercises"] });
  };
  const deletion = useMutation({
    mutationFn: (id: number) => deleteExercise(auth.csrf_token, id),
    onSuccess: refreshed,
  });
  const order = useMutation({
    mutationFn: (ids: number[]) => reorderExercises(auth.csrf_token, ids),
    onSuccess: refreshed,
    onError: () => {
      void cache.invalidateQueries({ queryKey: ["exercises"] });
    },
  });
  const rows = query.data?.exercises ?? [];
  const busy = deletion.isPending || order.isPending || editing !== undefined;
  function move(from: number, to: number) {
    if (busy || from === to || from < 0 || to < 0 || to >= rows.length) return;
    const ids = rows.map((row) => row.id);
    const [id] = ids.splice(from, 1);
    ids.splice(to, 0, id);
    order.mutate(ids);
  }
  return (
    <Panel>
      <h2>{t("exercises.title")}</h2>
      <p>{t("exercises.reorderHint")}</p>
      <Button disabled={busy} onClick={() => setEditing(null)}>
        {t("exercises.create")}
      </Button>
      {editing !== undefined && (
        <ExerciseForm
          key={editing?.id ?? "new"}
          auth={auth}
          exercise={editing}
          close={() => setEditing(undefined)}
        />
      )}
      {query.isPending && <p>{t("common.loading")}</p>}
      {query.isError && (
        <>
          <ErrorMessage error={query.error} />
          <Button onClick={() => void query.refetch()}>
            {t("common.retry")}
          </Button>
        </>
      )}
      {deletion.isError && <ErrorMessage error={deletion.error} />}
      {order.isError && <ErrorMessage error={order.error} />}
      {query.data && (
        <p>
          {t("exercises.total", {
            total: new Intl.NumberFormat(i18n.language).format(
              query.data.total,
            ),
          })}
        </p>
      )}
      {query.data && query.data.total !== rows.length && (
        <ErrorMessage error={new ApiError("EXERCISE_ORDER_CONFLICT")} />
      )}
      <Box component="ol" sx={{ pl: 3 }}>
        {rows.map((exercise, index) => (
          <Panel
            component="li"
            key={exercise.id}
            aria-label={exercise.title}
            draggable={!busy}
            onDragStart={(event) => {
              event.dataTransfer.setData("text/plain", String(exercise.id));
              event.dataTransfer.effectAllowed = "move";
            }}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              move(
                rows.findIndex(
                  (row) =>
                    row.id === Number(event.dataTransfer.getData("text/plain")),
                ),
                index,
              );
            }}
          >
            <h3>{exercise.title}</h3>
            {exercise.category && (
              <Chip
                label={exercise.category}
                variant="outlined"
                sx={{
                  mb: 1,
                  maxWidth: "100%",
                  height: "auto",
                  "& .MuiChip-label": { whiteSpace: "normal", py: 0.5 },
                }}
              />
            )}
            <Box
              component="p"
              sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}
            >
              {exercise.description}
            </Box>
            <Preview
              key={`${exercise.id}-${exercise.image?.id}-${exercise.audio?.id}`}
              exercise={exercise}
            />
            {reviewing === exercise.id && exercise.image && (
              <Review
                exercise={exercise}
                auth={auth}
                close={() => setReviewing(null)}
              />
            )}
            <Box
              sx={{
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                gap: 1,
              }}
            >
              {exercise.image && (
                <>
                  <Chip
                    label={t(`omr.status.${exercise.omr.status}`)}
                    sx={{
                      maxWidth: "100%",
                      height: "auto",
                      "& .MuiChip-label": { whiteSpace: "normal", py: 0.5 },
                    }}
                  />
                  <Button
                    disabled={busy}
                    onClick={() => setReviewing(exercise.id)}
                  >
                    {t("omr.review")}
                  </Button>
                </>
              )}
              <Button
                disabled={busy}
                aria-label={t("exercises.editNamed", { title: exercise.title })}
                onClick={() => setEditing(exercise)}
              >
                {t("exercises.edit")}
              </Button>
              <Button
                disabled={busy}
                aria-label={t("exercises.deleteNamed", {
                  title: exercise.title,
                })}
                onClick={() => setDeleting(exercise.id)}
              >
                {t("exercises.delete")}
              </Button>
              <Button
                disabled={busy || index === 0}
                aria-label={t("exercises.moveUp", { title: exercise.title })}
                onClick={() => move(index, index - 1)}
              >
                {t("exercises.up")}
              </Button>
              <Button
                disabled={busy || index === rows.length - 1}
                aria-label={t("exercises.moveDown", { title: exercise.title })}
                onClick={() => move(index, index + 1)}
              >
                {t("exercises.down")}
              </Button>
            </Box>
            {deleting === exercise.id && (
              <Box sx={{ mt: 2 }}>
                <Alert severity="warning" role="status">
                  {t("exercises.deleteWarning", { title: exercise.title })}
                </Alert>
                <Button
                  disabled={busy}
                  onClick={() => deletion.mutate(exercise.id)}
                >
                  {t("exercises.confirmDelete")}
                </Button>{" "}
                <Button disabled={busy} onClick={() => setDeleting(null)}>
                  {t("common.close")}
                </Button>
              </Box>
            )}
          </Panel>
        ))}
      </Box>
    </Panel>
  );
}
