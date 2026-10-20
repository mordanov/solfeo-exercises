import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError, type Auth } from "../../api/auth";
import { listListeningChapters } from "../../api/chapters";
import type { Exercise } from "../../api/exercises";
import {
  cancelListeningRun,
  createListeningRun,
  getActiveListeningRun,
  navigateListeningRun,
} from "../../api/listeningRuns";
import { ErrorMessage } from "../../components/AccountUi";
import { Button, Field, Input, Panel } from "../../components/Ui";
import { finishPlayback, ListeningTracker, registerPlayback } from "./tracker";
import { Score } from "../omr/Score";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";

const runQueryKey = ["listening-run"];

function Player({
  exercise,
  auth,
  runId,
}: {
  exercise: Exercise;
  auth: Auth;
  runId: number;
}) {
  const { t } = useTranslation();
  const audio = useRef<HTMLAudioElement>(null);
  const [error, setError] = useState<unknown>(null);
  const [mediaError, setMediaError] = useState(false);
  const tracker = useMemo(
    () =>
      new ListeningTracker(
        {
          run_id: runId,
          exercise_id: exercise.id,
          audio_id: exercise.audio?.id ?? "",
          csrf_token: auth.csrf_token,
        },
        exercise.audio?.duration_seconds ?? 0,
        () => audio.current?.currentTime ?? 0,
        (failure) => {
          setError(failure);
          audio.current?.pause();
        },
        () => setError(null),
      ),
    [
      runId,
      exercise.id,
      exercise.audio?.id,
      exercise.audio?.duration_seconds,
      auth.csrf_token,
    ],
  );
  useEffect(() => {
    const leave = () => {
      audio.current?.pause();
      tracker.leave();
    };
    const unregister = registerPlayback(async () => {
      audio.current?.pause();
      await tracker.finish();
    });
    window.addEventListener("pagehide", leave);
    return () => {
      unregister();
      window.removeEventListener("pagehide", leave);
      leave();
    };
  }, [tracker]);
  return (
    <Panel component="article">
      <h3>{exercise.title}</h3>
      {exercise.category && (
        <Chip
          label={exercise.category}
          variant="outlined"
          sx={{
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
          src={`/api/exercises/${exercise.id}/files/image`}
          alt={t("exercises.imageFor", { title: exercise.title })}
          onError={() => setMediaError(true)}
        />
      )}
      {exercise.omr.status === "approved" && exercise.omr.job_id && (
        <Score
          approved
          id={exercise.id}
          version={exercise.omr.job_id}
          user={auth.user}
        />
      )}
      {exercise.audio ? (
        <audio
          ref={audio}
          controls
          preload="metadata"
          src={`/api/exercises/${exercise.id}/files/audio?version=${exercise.audio.id}`}
          aria-label={t("exercises.audioFor", { title: exercise.title })}
          onPlay={() => {
            window.dispatchEvent(new Event("solfeo:stop-spoken"));
            tracker.play();
          }}
          onPause={() => tracker.pause()}
          onTimeUpdate={() => tracker.update()}
          onSeeked={() => tracker.update()}
          onEnded={() => {
            void tracker.finish(true);
          }}
          onError={() => {
            setMediaError(true);
            void tracker.finish();
          }}
        />
      ) : exercise.omr.status === "approved" && exercise.omr.job_id ? (
        <p>{t("listening.noAudioSpoken")}</p>
      ) : (
        <p>{t("listening.noAudio")}</p>
      )}
      {error !== null && <ErrorMessage error={error} />}
      {mediaError && (
        <ErrorMessage error={new ApiError("MEDIA_PLAYBACK_ERROR")} />
      )}
    </Panel>
  );
}

export function Listening({ auth }: { auth: Auth }) {
  const { t } = useTranslation();
  const cache = useQueryClient();
  const [selectedChapterIds, setSelectedChapterIds] = useState<number[]>([]);
  const [resumed, setResumed] = useState(false);
  const runQuery = useQuery({
    queryKey: runQueryKey,
    queryFn: ({ signal }) => getActiveListeningRun(signal),
    retry: false,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
  const chaptersQuery = useQuery({
    queryKey: ["listening-chapters"],
    queryFn: ({ signal }) => listListeningChapters(signal),
    enabled: runQuery.data === null,
    retry: false,
  });
  const start = useMutation({
    mutationFn: () => createListeningRun(auth.csrf_token, selectedChapterIds),
    onSuccess: (run) => {
      cache.setQueryData(runQueryKey, run);
      setResumed(true);
    },
  });
  const navigation = useMutation({
    mutationFn: async (direction: "next" | "previous") => {
      const run = runQuery.data;
      if (!run) throw new ApiError("LISTENING_RUN_NOT_ACTIVE");
      await finishPlayback();
      return navigateListeningRun(auth.csrf_token, run.id, direction);
    },
    onSuccess: (run) => cache.setQueryData(runQueryKey, run),
  });
  const cancel = useMutation({
    mutationFn: async () => {
      const run = runQuery.data;
      if (!run) throw new ApiError("LISTENING_RUN_NOT_ACTIVE");
      await finishPlayback();
      await cancelListeningRun(auth.csrf_token, run.id);
    },
    onSuccess: () => {
      cache.setQueryData(runQueryKey, null);
      setSelectedChapterIds([]);
      setResumed(false);
    },
  });
  const run = runQuery.data;
  const currentItemIndex =
    run?.items.findIndex((item) => item.position === run.current_index) ?? -1;
  const currentItem =
    currentItemIndex >= 0 ? run?.items[currentItemIndex] : null;
  const disabled = start.isPending || navigation.isPending || cancel.isPending;

  return (
    <Panel>
      <h2>{t("student.title")}</h2>
      {runQuery.isPending && <p>{t("common.loading")}</p>}
      {runQuery.isError && (
        <>
          <ErrorMessage error={runQuery.error} />
          <Button onClick={() => void runQuery.refetch()}>
            {t("common.retry")}
          </Button>
        </>
      )}
      {chaptersQuery.isError && (
        <>
          <ErrorMessage error={chaptersQuery.error} />
          <Button onClick={() => void chaptersQuery.refetch()}>
            {t("common.retry")}
          </Button>
        </>
      )}
      {start.isError && <ErrorMessage error={start.error} />}
      {navigation.isError && <ErrorMessage error={navigation.error} />}
      {cancel.isError && <ErrorMessage error={cancel.error} />}
      {runQuery.data === null && (
        <section>
          <h3>{t("listening.selectChapters")}</h3>
          {chaptersQuery.isPending && <p>{t("common.loading")}</p>}
          {chaptersQuery.data?.length === 0 && <p>{t("listening.empty")}</p>}
          {chaptersQuery.data?.map((chapter) => (
            <Field key={chapter.id}>
              <Input
                type="checkbox"
                checked={selectedChapterIds.includes(chapter.id)}
                disabled={disabled}
                onChange={(event) => {
                  setSelectedChapterIds((selected) =>
                    event.target.checked
                      ? [...selected, chapter.id]
                      : selected.filter((id) => id !== chapter.id),
                  );
                }}
              />
              {t("chapters.numbered", { number: chapter.number })}
            </Field>
          ))}
          <Button
            disabled={
              selectedChapterIds.length === 0 ||
              disabled ||
              chaptersQuery.isPending ||
              chaptersQuery.isError
            }
            onClick={() => start.mutate()}
          >
            {t("listening.startRun")}
          </Button>
        </section>
      )}
      {run?.status === "active" && (
        <section>
          <h3>{t("listening.savedRun")}</h3>
          <p>
            {t("listening.runProgress", {
              current: currentItemIndex + 1,
              total: run.items.length,
            })}
          </p>
          <ol aria-label={t("listening.runQueue")}>
            {run.items.map((item, index) => (
              <li
                key={`${item.position}-${item.exercise.id}`}
                aria-current={index === currentItemIndex ? "step" : undefined}
              >
                {item.exercise.title} (
                {t("chapters.numbered", { number: item.chapter_number })})
              </li>
            ))}
          </ol>
          {!resumed && (
            <Button disabled={disabled} onClick={() => setResumed(true)}>
              {t("listening.resume")}
            </Button>
          )}
          {resumed && currentItem && (
            <>
              <Player
                key={`${run.id}-${currentItem.position}-${currentItem.exercise.id}`}
                exercise={currentItem.exercise}
                auth={auth}
                runId={run.id}
              />
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                <Button
                  disabled={disabled || currentItemIndex <= 0}
                  onClick={() => navigation.mutate("previous")}
                >
                  {t("common.previous")}
                </Button>
                <Button
                  disabled={disabled}
                  onClick={() => navigation.mutate("next")}
                >
                  {t("common.next")}
                </Button>
              </Box>
            </>
          )}
          <Button disabled={disabled} onClick={() => cancel.mutate()}>
            {t("listening.cancelRun")}
          </Button>
        </section>
      )}
      {run?.status === "completed" && (
        <section>
          <p>{t("listening.runComplete")}</p>
          <Button
            onClick={() => {
              cache.setQueryData(runQueryKey, null);
              setSelectedChapterIds([]);
              setResumed(false);
            }}
          >
            {t("listening.newRun")}
          </Button>
        </section>
      )}
    </Panel>
  );
}
