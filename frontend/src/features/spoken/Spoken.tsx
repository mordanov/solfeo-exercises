import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, type User } from "../../api/auth";
import { fetchOmr, fetchScore } from "../../api/omr";
import { spokenConfig } from "../../config";
import { ErrorMessage } from "../../components/AccountUi";
import { parseSequence, type NoteEvent } from "./sequence";
import { SpeechPlayer } from "./player";
import { noteName } from "./vocabulary";

export function Spoken({
  id,
  version,
  user,
  highlight,
}: {
  id: number;
  version: string;
  user: User;
  highlight: (index: number) => void;
}) {
  const { t, i18n } = useTranslation();
  const [bpm, setBpm] = useState(spokenConfig.defaultBpm);
  const [state, setState] = useState<"idle" | "loading" | "playing">("idle");
  const [error, setError] = useState<unknown>(null);
  const [current, setCurrent] = useState<NoteEvent | null>(null);
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
    return () => {
      window.removeEventListener("solfeo:stop-spoken", stop);
      window.removeEventListener("pagehide", stop);
      document.removeEventListener("visibilitychange", hidden);
      player.stop();
    };
  }, [player, id, version, user.note_naming, user.ui_language]);
  return (
    <section aria-label={t("spoken.title")}>
      <h4>{t("spoken.title")}</h4>
      <p>{t("spoken.disclosure")}</p>
      <label>
        {t("spoken.tempo", {
          bpm: new Intl.NumberFormat(i18n.language).format(bpm),
        })}
        <input
          type="range"
          min={spokenConfig.minBpm}
          max={spokenConfig.maxBpm}
          step={1}
          value={bpm}
          onChange={(event) => {
            player.stop();
            setState("idle");
            setBpm(Number(event.target.value));
          }}
        />
      </label>
      <button
        disabled={state !== "idle"}
        onClick={() => {
          window.dispatchEvent(new Event("solfeo:stop-spoken"));
          window.dispatchEvent(new Event("solfeo:pause-audio"));
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
            () => setState("playing"),
          );
        }}
      >
        {t("spoken.play")}
      </button>
      <button
        disabled={state === "idle"}
        onClick={() => {
          player.stop();
          setState("idle");
        }}
      >
        {t("spoken.stop")}
      </button>
      {state === "loading" && <p role="status">{t("spoken.loading")}</p>}
      {state === "playing" && (
        <p role="status">
          {current?.pitch
            ? t("spoken.current", {
                name: noteName(
                  current.pitch.step,
                  user.ui_language,
                  user.note_naming,
                ),
              })
            : t("spoken.rest")}
        </p>
      )}
      {error !== null && <ErrorMessage error={error} />}
      <p>{t("spoken.journalHint")}</p>
    </section>
  );
}
