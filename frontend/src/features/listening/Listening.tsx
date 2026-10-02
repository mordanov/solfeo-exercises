import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError, type Auth } from "../../api/auth";
import type { Exercise } from "../../api/exercises";
import {
  currentExercise,
  selectExercise,
  type Mode,
} from "../../api/listening";
import { ErrorMessage } from "../../components/AccountUi";
import { finishPlayback, ListeningTracker, registerPlayback } from "./tracker";
import { Score } from "../omr/Score";
import { Button, Field, Panel, Select } from "../../components/Ui";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";

function Player({
  exercise,
  auth,
  mode,
}: {
  exercise: Exercise;
  auth: Auth;
  mode: Mode;
}) {
  const { t } = useTranslation();
  const audio = useRef<HTMLAudioElement>(null);
  const [error, setError] = useState<unknown>(null);
  const [mediaError, setMediaError] = useState(false);
  const tracker = useMemo(
    () =>
      new ListeningTracker(
        {
          exercise_id: exercise.id,
          audio_id: exercise.audio?.id ?? "",
          csrf_token: auth.csrf_token,
          mode,
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
      exercise.id,
      exercise.audio?.id,
      exercise.audio?.duration_seconds,
      auth.csrf_token,
      mode,
    ],
  );
  useEffect(() => {
    const player = audio.current;
    const leave = () => {
      player?.pause();
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
  const [mode, setMode] = useState<Mode>("sequential");
  const [history, setHistory] = useState<number[]>([]);
  const query = useQuery({
    queryKey: ["listening"],
    queryFn: ({ signal }) => currentExercise(signal),
    retry: false,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
  const exercise = query.data;
  const navigation = useMutation({
    mutationFn: async ({
      nextMode,
      direction,
    }: {
      nextMode: Mode;
      direction: "current" | "next" | "previous";
    }) => {
      await finishPlayback();
      return selectExercise(
        auth.csrf_token,
        nextMode,
        direction,
        nextMode !== mode && nextMode === "sequential"
          ? undefined
          : exercise?.id,
        nextMode === "random" && direction === "previous"
          ? history.at(-1)
          : undefined,
      );
    },
    onSuccess: (selected, { nextMode, direction }) => {
      if (nextMode !== mode) setHistory([]);
      else if (mode === "random" && direction === "previous")
        setHistory((values) => values.slice(0, -1));
      else if (mode === "random" && exercise)
        setHistory((values) => [...values, exercise.id]);
      setMode(nextMode);
      cache.setQueryData(["listening"], selected);
    },
  });
  return (
    <Panel>
      <h2>{t("student.title")}</h2>
      <Field>
        {t("listening.mode")}
        <Select
          value={mode}
          disabled={navigation.isPending || query.isPending}
          onChange={(event) => {
            const value = event.target.value;
            if (value === "sequential" || value === "random")
              navigation.mutate({ nextMode: value, direction: "current" });
          }}
        >
          <option value="sequential">{t("listening.sequential")}</option>
          <option value="random">{t("listening.random")}</option>
        </Select>
      </Field>
      {query.isPending && <p>{t("common.loading")}</p>}
      {query.isError && <ErrorMessage error={query.error} />}
      {navigation.isError && <ErrorMessage error={navigation.error} />}
      {(query.isError || exercise === null) && (
        <Button onClick={() => void query.refetch()}>
          {t("common.retry")}
        </Button>
      )}
      {exercise === null && <p>{t("listening.empty")}</p>}
      {exercise && (
        <>
          <Player
            key={`${exercise.id}-${exercise.audio?.id}-${mode}`}
            exercise={exercise}
            auth={auth}
            mode={mode}
          />
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
            <Button
              disabled={
                navigation.isPending ||
                (mode === "random" && history.length === 0)
              }
              onClick={() =>
                navigation.mutate({ nextMode: mode, direction: "previous" })
              }
            >
              {t("common.previous")}
            </Button>
            <Button
              disabled={navigation.isPending}
              onClick={() =>
                navigation.mutate({ nextMode: mode, direction: "next" })
              }
            >
              {t("common.next")}
            </Button>
          </Box>
          <p>{t("listening.hint")}</p>
        </>
      )}
    </Panel>
  );
}
