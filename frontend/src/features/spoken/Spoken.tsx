import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, type User } from "../../api/auth";
import { fetchOmr, fetchScore } from "../../api/omr";
import { spokenConfig } from "../../config";
import { ErrorMessage } from "../../components/AccountUi";
import { parseSequence, type NoteEvent } from "./sequence";
import {
  SpeechPlayer,
  chooseTempo,
  tempoRange,
  type TempoRange,
} from "./player";
import timings from "../../../public/solfege/timings.json";
import { noteName } from "./vocabulary";
import { Button, Field, Panel } from "../../components/Ui";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";

export function Spoken({
  id,
  version,
  score,
  user,
  highlight,
}: {
  id: number;
  version: string;
  score: string;
  user: User;
  highlight: (index: number) => void;
}) {
  const { t, i18n } = useTranslation();
  const prepared = useMemo<
    { ready: true; range: TempoRange } | { ready: false; error: unknown }
  >(() => {
    try {
      return {
        ready: true,
        range: tempoRange(
          parseSequence(score),
          new Map(Object.entries(timings)),
          user.ui_language,
          user.note_naming,
        ),
      };
    } catch (error: unknown) {
      return { ready: false, error };
    }
  }, [score, user.ui_language, user.note_naming]);
  const [bpm, setBpm] = useState(() =>
    prepared.ready
      ? chooseTempo(spokenConfig.defaultBpm, prepared.range)
      : spokenConfig.defaultBpm,
  );
  const [state, setState] = useState<"idle" | "loading" | "playing">("idle");
  const [error, setError] = useState<unknown>(null);
  const [current, setCurrent] = useState<NoteEvent | null>(null);
  const storageKey = `solfeo-tempo:${user.id}:${id}:${version}:${user.ui_language}:${user.note_naming}`;
  useEffect(() => {
    if (!prepared.ready) return;
    try {
      const saved = localStorage.getItem(storageKey);
      setBpm(
        chooseTempo(
          saved === null ? spokenConfig.defaultBpm : Number(saved),
          prepared.range,
        ),
      );
    } catch (failure: unknown) {
      console.error("SPOKEN_TEMPO_STORAGE_FAILED");
      setError(
        failure instanceof ApiError
          ? failure
          : new ApiError("SPOKEN_TEMPO_STORAGE_FAILED"),
      );
    }
  }, [prepared, storageKey]);
  function remember(tempo: number) {
    setBpm(tempo);
    try {
      localStorage.setItem(storageKey, String(tempo));
    } catch {
      console.error("SPOKEN_TEMPO_STORAGE_FAILED");
      setError(new ApiError("SPOKEN_TEMPO_STORAGE_FAILED"));
    }
  }
  const player = useMemo(
    () =>
      new SpeechPlayer(
        (event) => {
          setCurrent(event);
          highlight(event?.noteIndices[0] ?? -1);
        },
        () => setState("idle"),
        (failure) => {
          setError(failure);
          setState("idle");
        },
      ),
    [highlight],
  );
  useEffect(() => {
    const stop = () => {
      player.stop();
      setState("idle");
    };
    const hidden = () => {
      if (document.hidden) stop();
    };
    window.addEventListener("solfeo:stop-spoken", stop);
    window.addEventListener("pagehide", stop);
    document.addEventListener("visibilitychange", hidden);
    document.addEventListener("play", stop, true);
    return () => {
      window.removeEventListener("solfeo:stop-spoken", stop);
      window.removeEventListener("pagehide", stop);
      document.removeEventListener("visibilitychange", hidden);
      document.removeEventListener("play", stop, true);
      player.stop();
    };
  }, [player, id, version, user.note_naming, user.ui_language]);
  if (!prepared.ready)
    return (
      <Panel aria-label={t("spoken.title")}>
        <h4>{t("spoken.title")}</h4>
        <ErrorMessage error={prepared.error} />
      </Panel>
    );
  return (
    <Panel aria-label={t("spoken.title")}>
      <h4>{t("spoken.title")}</h4>
      <p>{t("spoken.disclosure")}</p>
      <Field>
        {t("spoken.tempo", {
          bpm: new Intl.NumberFormat(i18n.language).format(bpm),
        })}
        <Box
          component="input"
          type="range"
          min={
            bpm < spokenConfig.minBpm
              ? prepared.range.min
              : Math.max(prepared.range.min, spokenConfig.minBpm)
          }
          max={prepared.range.max}
          step={1}
          value={bpm}
          sx={{
            width: "100%",
            minHeight: 44,
            accentColor: "var(--mui-palette-primary-main)",
            m: 0,
          }}
          onChange={(event) => {
            player.stop();
            setState("idle");
            setError(null);
            remember(chooseTempo(Number(event.target.value), prepared.range));
          }}
        />
      </Field>
      <Button
        disabled={state !== "idle"}
        onClick={() => {
          window.dispatchEvent(new Event("solfeo:stop-spoken"));
          document.querySelectorAll("audio").forEach((audio) => audio.pause());
          setError(null);
          setState("loading");
          void player.play(
            async (signal) => {
              const status = await fetchOmr(id, signal);
              if (status.status !== "approved" || status.job_id !== version)
                throw new ApiError("OMR_STALE");
              return parseSequence(await fetchScore(id, version, signal));
            },
            bpm,
            user.ui_language,
            user.note_naming,
            (tempo) => {
              remember(tempo);
              setState("playing");
            },
          );
        }}
      >
        {t("spoken.play")}
      </Button>
      <Button
        disabled={state === "idle"}
        onClick={() => {
          player.stop();
          setState("idle");
        }}
      >
        {t("spoken.stop")}
      </Button>
      {state === "loading" && (
        <Alert severity="info" role="status">
          {t("spoken.loading")}
        </Alert>
      )}
      {state === "playing" && (
        <Alert severity="info" role="status">
          {current?.pitch
            ? t("spoken.current", {
                name: noteName(
                  current.pitch.step,
                  user.ui_language,
                  user.note_naming,
                ),
              })
            : t("spoken.rest")}
        </Alert>
      )}
      {error !== null && <ErrorMessage error={error} />}
      <p>{t("spoken.journalHint")}</p>
    </Panel>
  );
}
