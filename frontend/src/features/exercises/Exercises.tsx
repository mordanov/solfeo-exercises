import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError, type Auth } from "../../api/auth";
import { listChapters } from "../../api/chapters";
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
  Select,
  Textarea,
} from "../../components/Ui";
import {
  ReadOnlyGrid,
  type ReadOnlyColumn,
} from "../../components/ReadOnlyGrid";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import LinearProgress from "@mui/material/LinearProgress";
import Alert from "@mui/material/Alert";
import { ChapterManager } from "./ChapterManager";

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
  const [chapterId, setChapterId] = useState(
    String(exercise?.chapter_id ?? ""),
  );
  const [image, setImage] = useState<File>();
  const [pastedImageName, setPastedImageName] = useState<string>();
  const [audio, setAudio] = useState<File>();
  const [removeImage, setRemoveImage] = useState(false);
  const [removeAudio, setRemoveAudio] = useState(false);
  const [progress, setProgress] = useState(0);
  const [validation, setValidation] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const chapters = useQuery({
    queryKey: ["chapters"],
    queryFn: ({ signal }) => listChapters(signal),
    retry: false,
  });
  const mutation = useMutation({
    mutationFn: () => {
      const data = new FormData();
      data.set("title", title);
      data.set("description", description);
      data.set("category", category);
      data.set("chapter_id", chapterId);
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
      onPaste={(e) => {
        const item = Array.from(e.clipboardData.items).find((i) =>
          i.type.startsWith("image/"),
        );
        if (!item) return;
        const file = item.getAsFile();
        if (file) {
          setImage(file);
          setRemoveImage(false);
          setPastedImageName(file.name);
        }
      }}
      onSubmit={(event) => {
        event.preventDefault();
        const missing = !(
          image ||
          (!removeImage && exercise?.image) ||
          audio ||
          (!removeAudio && exercise?.audio)
        );
        if (!chapterId) return;
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
          {t("exercises.chapter")}
          <Select
            required
            value={chapterId}
            disabled={mutation.isPending || chapters.isPending}
            onChange={(event) => setChapterId(event.target.value)}
          >
            <option value="">{t("exercises.selectChapter")}</option>
            {chapters.data?.map((chapter) => (
              <option key={chapter.id} value={chapter.id}>
                {t("chapters.numbered", { number: chapter.number })}
              </option>
            ))}
          </Select>
        </Field>
        {chapters.isError && (
          <>
            <ErrorMessage error={chapters.error} />
            <Button type="button" onClick={() => void chapters.refetch()}>
              {t("common.retry")}
            </Button>
          </>
        )}
        <Field>
          {t("exercises.image")}
          <Input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            disabled={removeImage}
            onChange={(e) => {
              setImage(e.target.files?.[0]);
              setPastedImageName(undefined);
            }}
          />
        </Field>
        <Button
          type="button"
          disabled={removeImage || mutation.isPending}
          onClick={async () => {
            try {
              const items = await navigator.clipboard.read();
              for (const item of items) {
                const imageType = item.types.find((t) =>
                  t.startsWith("image/"),
                );
                if (imageType) {
                  const blob = await item.getType(imageType);
                  const ext = imageType.split("/")[1] ?? "png";
                  const file = new File([blob], `pasted.${ext}`, {
                    type: imageType,
                  });
                  setImage(file);
                  setRemoveImage(false);
                  setPastedImageName(file.name);
                  return;
                }
              }
            } catch {
              /* API недоступна или нет разрешения */
            }
          }}
        >
          {t("exercises.pasteImage")}
        </Button>
        {pastedImageName && (
          <p>{t("exercises.pasteSelected", { name: pastedImageName })}</p>
        )}
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
        <Button disabled={!chapterId || mutation.isPending}>
          {t("exercises.save")}
        </Button>{" "}
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
      {exercise?.image && (
        <Box sx={{ mt: 2 }}>
          <Button type="button" onClick={() => setShowReview((v) => !v)}>
            {t("omr.review")}
          </Button>
          {showReview && (
            <Review
              exercise={exercise}
              auth={auth}
              close={() => setShowReview(false)}
            />
          )}
        </Box>
      )}
    </Form>
  );
}

export function Exercises({ auth }: { auth: Auth }) {
  const { t, i18n } = useTranslation();
  const cache = useQueryClient();
  const [editing, setEditing] = useState<Exercise | null | undefined>();
  const [deleting, setDeleting] = useState<Exercise | null>(null);
  const [filterChapter, setFilterChapter] = useState("");
  const [filterImage, setFilterImage] = useState("");
  const [filterAudio, setFilterAudio] = useState("");

  const chapters = useQuery({
    queryKey: ["chapters"],
    queryFn: ({ signal }) => listChapters(signal),
    retry: false,
  });
  const query = useQuery({
    queryKey: ["exercises"],
    queryFn: ({ signal }) => listExercises(signal),
    retry: false,
  });
  const deletion = useMutation({
    mutationFn: (id: number) => deleteExercise(auth.csrf_token, id),
    onSuccess: async () => {
      setDeleting(null);
      await cache.invalidateQueries({ queryKey: ["exercises"] });
    },
  });
  const order = useMutation({
    mutationFn: (ids: number[]) => reorderExercises(auth.csrf_token, ids),
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ["exercises"] });
    },
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

  const filteredRows = rows.filter((row) => {
    if (filterChapter && row.chapter_id !== Number(filterChapter)) return false;
    if (filterImage === "yes" && !row.image) return false;
    if (filterImage === "no" && row.image) return false;
    if (filterAudio === "yes" && !row.audio) return false;
    if (filterAudio === "no" && row.audio) return false;
    return true;
  });

  const columns: ReadOnlyColumn<Exercise>[] = [
    {
      field: "title",
      headerName: t("exercises.name"),
      flex: 2,
      minWidth: 120,
      render: (row) => row.title,
    },
    {
      field: "chapter_id",
      headerName: t("exercises.chapter"),
      flex: 1,
      minWidth: 80,
      render: (row) => {
        const chapter = chapters.data?.find((c) => c.id === row.chapter_id);
        return chapter
          ? t("chapters.numbered", { number: chapter.number })
          : String(row.chapter_id);
      },
    },
    {
      field: "image",
      headerName: t("exercises.image"),
      minWidth: 80,
      render: (row) => (row.image ? "✓" : ""),
    },
    {
      field: "audio",
      headerName: t("exercises.audio"),
      minWidth: 80,
      render: (row) => (row.audio ? "✓" : ""),
    },
    {
      field: "omr",
      headerName: t("exercises.omrStatus"),
      flex: 1,
      minWidth: 120,
      render: (row) => (row.image ? t(`omr.status.${row.omr.status}`) : ""),
    },
    {
      field: "actions",
      headerName: t("exercises.actions"),
      minWidth: 260,
      render: (row) => {
        const index = rows.findIndex((r) => r.id === row.id);
        return (
          <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
            <Button
              disabled={busy}
              aria-label={t("exercises.editNamed", { title: row.title })}
              onClick={() => setEditing(row)}
            >
              {t("exercises.edit")}
            </Button>
            <Button
              disabled={busy}
              aria-label={t("exercises.deleteNamed", { title: row.title })}
              onClick={() => setDeleting(row)}
            >
              {t("exercises.delete")}
            </Button>
            <Button
              disabled={busy || index === 0}
              aria-label={t("exercises.moveUp", { title: row.title })}
              onClick={() => move(index, index - 1)}
            >
              {t("exercises.up")}
            </Button>
            <Button
              disabled={busy || index === rows.length - 1}
              aria-label={t("exercises.moveDown", { title: row.title })}
              onClick={() => move(index, index + 1)}
            >
              {t("exercises.down")}
            </Button>
          </Box>
        );
      },
    },
  ];

  return (
    <Panel>
      <h2>{t("exercises.title")}</h2>
      <p>{t("exercises.reorderHint")}</p>
      <ChapterManager csrf={auth.csrf_token} />
      <Button disabled={busy} onClick={() => setEditing(null)}>
        {t("exercises.create")}
      </Button>

      <Dialog
        open={editing !== undefined}
        onClose={() => setEditing(undefined)}
        fullWidth
        maxWidth="sm"
      >
        <DialogContent>
          {editing !== undefined && (
            <ExerciseForm
              key={editing?.id ?? "new"}
              auth={auth}
              exercise={editing}
              close={() => setEditing(undefined)}
            />
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={deleting !== null} onClose={() => setDeleting(null)}>
        <DialogContent>
          {deleting && (
            <Box>
              <Alert severity="warning" role="status">
                {t("exercises.deleteWarning", { title: deleting.title })}
              </Alert>
              <Box sx={{ mt: 2 }}>
                <Button
                  disabled={deletion.isPending}
                  onClick={() => deletion.mutate(deleting.id)}
                >
                  {t("exercises.confirmDelete")}
                </Button>{" "}
                <Button
                  disabled={deletion.isPending}
                  onClick={() => setDeleting(null)}
                >
                  {t("common.close")}
                </Button>
              </Box>
              {deletion.isError && <ErrorMessage error={deletion.error} />}
            </Box>
          )}
        </DialogContent>
      </Dialog>

      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mt: 2 }}>
        <Field>
          {t("exercises.chapter")}
          <Select
            value={filterChapter}
            onChange={(e) => setFilterChapter(e.target.value)}
          >
            <option value="">{t("exercises.filterAll")}</option>
            {chapters.data?.map((chapter) => (
              <option key={chapter.id} value={chapter.id}>
                {t("chapters.numbered", { number: chapter.number })}
              </option>
            ))}
          </Select>
        </Field>
        <Field>
          {t("exercises.image")}
          <Select
            value={filterImage}
            onChange={(e) => setFilterImage(e.target.value)}
          >
            <option value="">{t("exercises.filterAll")}</option>
            <option value="yes">{t("exercises.filterHas")}</option>
            <option value="no">{t("exercises.filterWithout")}</option>
          </Select>
        </Field>
        <Field>
          {t("exercises.audio")}
          <Select
            value={filterAudio}
            onChange={(e) => setFilterAudio(e.target.value)}
          >
            <option value="">{t("exercises.filterAll")}</option>
            <option value="yes">{t("exercises.filterHas")}</option>
            <option value="no">{t("exercises.filterWithout")}</option>
          </Select>
        </Field>
      </Box>

      {query.isPending && <p>{t("common.loading")}</p>}
      {query.isError && (
        <>
          <ErrorMessage error={query.error} />
          <Button onClick={() => void query.refetch()}>
            {t("common.retry")}
          </Button>
        </>
      )}
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
      <ReadOnlyGrid
        rows={filteredRows}
        columns={columns}
        label={t("exercises.title")}
      />
    </Panel>
  );
}
