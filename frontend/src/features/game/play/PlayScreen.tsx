import {
  Alert,
  Box,
  Button,
  IconButton,
  Tooltip,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { useSubmitTask, usePlayer, type Note, type Task } from "../api/hooks";
import { playNotes } from "../audio/synth";
import { noteLabel } from "../notes";
import { ErrorMessage } from "../../../components/AccountUi";
import Staff from "../staff/Staff";
import NoteButtons from "./NoteButtons";
import Timer from "./Timer";
import AvatarImage from "../setup/AvatarImage";

export type { RoundResult } from "../api/hooks";
import type { RoundResult } from "../api/hooks";

interface Props {
  roundId: number;
  playerId?: number;
  csrf: string;
  initialTask: Task;
  noteNaming?: "solfege" | "letters";
  noteCount: number;
  difficulty: string;
  timeLimitMs: number;
  showSoundHint?: boolean;
  showCorrectAnswer?: boolean;
  onResult: (result: RoundResult) => void;
}

type FeedbackState = "idle" | "correct" | "wrong" | "timeout";

function Mascot({
  playerId,
  feedback,
}: {
  playerId: number;
  feedback: FeedbackState;
}) {
  const player = usePlayer(playerId);
  if (!player.data) return null;
  return (
    <Box sx={{ textAlign: "center" }}>
      <AvatarImage
        animalId={player.data.avatar_animal ?? "unicorn"}
        customAvatarId={player.data.custom_avatar_id}
        reviewStatus={player.data.avatar_review_status}
        stage={player.data.avatar_level}
        mood={
          feedback === "correct"
            ? "happy"
            : feedback === "wrong" || feedback === "timeout"
              ? "sad"
              : "neutral"
        }
        size={96}
      />
    </Box>
  );
}

export default function PlayScreen({
  roundId,
  playerId,
  csrf,
  initialTask,
  noteNaming = "solfege",
  noteCount,
  timeLimitMs,
  showSoundHint = true,
  showCorrectAnswer = false,
  onResult,
}: Props) {
  const { t } = useTranslation();
  const [task, setTask] = useState<Task>(initialTask);
  const [clockSkew] = useState(() =>
    initialTask.server_time
      ? Date.parse(initialTask.server_time) - Date.now()
      : 0,
  );
  const [answers, setAnswers] = useState<Note[]>([]);
  const [correctAnswers, setCorrectAnswers] = useState<Note[]>([]);
  const [feedback, setFeedback] = useState<FeedbackState>("idle");
  const [timerKey, setTimerKey] = useState(0);
  const [listening, setListening] = useState(false);
  const [audioError, setAudioError] = useState(false);
  const playbackRef = useRef<AbortController | null>(null);
  const submittingRef = useRef(false);
  const transitionRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const timedOutRef = useRef(false);
  const submitTask = useSubmitTask(roundId);

  const stopListening = useCallback(() => {
    const playback = playbackRef.current;
    playbackRef.current = null;
    playback?.abort();
    setListening(false);
  }, []);

  useEffect(() => {
    window.addEventListener("pagehide", stopListening);
    return () => {
      window.removeEventListener("pagehide", stopListening);
      if (transitionRef.current !== null) clearTimeout(transitionRef.current);
      const playback = playbackRef.current;
      playbackRef.current = null;
      playback?.abort();
    };
  }, [stopListening]);

  const startPlayback = (notes: Note[], hint: boolean) => {
    stopListening();
    const playback = new AbortController();
    playbackRef.current = playback;
    setAudioError(false);
    setListening(hint);
    void playNotes(notes, playback.signal)
      .catch(() => {
        if (playbackRef.current === playback && !playback.signal.aborted) {
          setAudioError(true);
        }
      })
      .finally(() => {
        if (playbackRef.current === playback) {
          playbackRef.current = null;
          setListening(false);
        }
      });
  };
  const handleListen = () => {
    if (submittingRef.current || feedback !== "idle") return;
    if (listening) stopListening();
    else startPlayback(task.notes, true);
  };

  const doSubmit = useCallback(
    (givenAnswers: Note[] | null, timedOut: boolean) => {
      if (submittingRef.current) return;
      submittingRef.current = true;
      if (timedOut) stopListening();
      timedOutRef.current = timedOut;
      setAudioError(false);

      const body = timedOut
        ? { csrf, task_index: task.index, timed_out: true as const }
        : {
            csrf,
            task_index: task.index,
            answers: givenAnswers,
          };

      submitTask.mutate(body, {
        onSuccess: (data) => {
          setCorrectAnswers(data.correct_answers);
          setFeedback(
            (data.timed_out ?? timedOut)
              ? "timeout"
              : data.is_correct
                ? "correct"
                : "wrong",
          );
          // Cached replies preserve server_time, so recalibration would extend deadlines.
          const feedbackMs = data.next_task?.issued_at
            ? Math.max(
                0,
                Date.parse(data.next_task.issued_at) - clockSkew - Date.now(),
              )
            : 900;
          transitionRef.current = setTimeout(() => {
            stopListening();
            submittingRef.current = false;
            if (data.result) {
              onResult(data.result);
            } else if (data.next_task) {
              setTask(data.next_task);
              setAnswers([]);
              setCorrectAnswers([]);
              setFeedback("idle");
              setTimerKey((k) => k + 1);
            }
          }, feedbackMs);
        },
        onError: () => {
          submittingRef.current = false;
        },
      });
    },
    [csrf, task.index, submitTask, onResult, stopListening, clockSkew],
  );

  const handleAnswer = (note: Note) => {
    if (feedback !== "idle" || submittingRef.current) return;
    startPlayback([note], false);
    const next = [...answers, note];
    setAnswers(next);
    if (next.length === noteCount) {
      doSubmit(next, false);
    }
  };

  const handleBackspace = () => {
    if (feedback !== "idle" || answers.length === 0) return;
    setAnswers((a) => a.slice(0, -1));
  };

  const handleTimeout = useCallback(() => doSubmit(null, true), [doSubmit]);

  const isWaiting = feedback !== "idle";
  const clef = task.clef as "treble" | "bass";

  return (
    <Box sx={{ p: 2, maxWidth: 480, mx: "auto" }}>
      <Typography
        variant="caption"
        sx={{ display: "block", textAlign: "center", mb: 1, color: "#888" }}
      >
        {task.index + 1} / 7
      </Typography>

      <Timer
        key={timerKey}
        totalMs={task.time_limit_ms ?? timeLimitMs}
        deadlineMs={
          task.deadline_at
            ? Date.parse(task.deadline_at) - clockSkew
            : undefined
        }
        onExpire={handleTimeout}
        paused={isWaiting}
      />
      {playerId !== undefined && (
        <Mascot playerId={playerId} feedback={feedback} />
      )}

      <Box sx={{ minHeight: 56 }}>
        {feedback !== "idle" && (
          <Alert
            severity={feedback === "correct" ? "success" : "error"}
            sx={{ mb: 1 }}
          >
            {feedback === "correct"
              ? t("game.correct")
              : feedback === "timeout"
                ? t("game.timeout")
                : t("game.wrong")}
          </Alert>
        )}
      </Box>

      <Box sx={{ display: "flex", alignItems: "center", gap: 1, my: 2 }}>
        <Box
          sx={{
            background: "#FFFDF5",
            borderRadius: 3,
            p: 2,
            flex: 1,
            minWidth: 0,
          }}
        >
          <Staff notes={task.notes} clef={clef} />
        </Box>
      </Box>

      <Box
        sx={{
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: 128,
          mb: 2,
        }}
      >
        {showSoundHint && (
          <Tooltip title={t(listening ? "game.stopListening" : "game.listen")}>
            <span>
              <IconButton
                onClick={handleListen}
                disabled={
                  isWaiting ||
                  submitTask.isPending ||
                  answers.length >= noteCount
                }
                aria-label={t(listening ? "game.stopListening" : "game.listen")}
                sx={{
                  width: 56,
                  height: 56,
                  background: "#fff",
                  color: "#333",
                  border: "2px solid #ccc",
                  "&:hover": { background: "#f5f5f5" },
                  "&.Mui-focusVisible": {
                    outline: "3px solid",
                    outlineColor: "primary.main",
                    outlineOffset: 3,
                  },
                }}
              >
                <svg
                  width="28"
                  height="28"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                  focusable="false"
                >
                  {listening ? (
                    <rect
                      x="6"
                      y="6"
                      width="12"
                      height="12"
                      rx="1"
                      fill="currentColor"
                    />
                  ) : (
                    <>
                      <path d="M3 9H7L12 5V19L7 15H3Z" fill="currentColor" />
                      <path
                        d="M15 8Q19 12 15 16M18 5Q25 12 18 19"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                    </>
                  )}
                </svg>
              </IconButton>
            </span>
          </Tooltip>
        )}
        {showCorrectAnswer && feedback !== "idle" && (
          <Box
            role="region"
            aria-label={t("game.correctAnswer")}
            sx={{
              position: "absolute",
              left: "calc(50% + 36px)",
              right: 0,
              top: "50%",
              transform: "translateY(-50%)",
              textAlign: "center",
              overflowWrap: "anywhere",
            }}
          >
            <Typography variant="caption">{t("game.correctAnswer")}</Typography>
            <Typography sx={{ fontWeight: 700 }}>
              {correctAnswers
                .map((note) => noteLabel(note, noteNaming, t))
                .join(" · ")}
            </Typography>
          </Box>
        )}
      </Box>
      {audioError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {t("game.audioError")}
        </Alert>
      )}
      {submitTask.isError && (
        <>
          <ErrorMessage error={submitTask.error} />
          <Button onClick={() => doSubmit(answers, timedOutRef.current)}>
            {t("common.retry")}
          </Button>
        </>
      )}

      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 1,
          justifyContent: "center",
          mb: 1,
        }}
      >
        {Array.from({ length: noteCount }).map((_, i) => (
          <Box
            key={i}
            sx={{
              minWidth: 48,
              height: 48,
              px: 1,
              flexShrink: 0,
              whiteSpace: "nowrap",
              color: "#1a1a1a",
              borderRadius: 2,
              border: "2px solid #ccc",
              background: answers[i] ? "#FFD93D" : "#fff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: "1rem",
            }}
          >
            {answers[i] ? noteLabel(answers[i], noteNaming, t) : ""}
          </Box>
        ))}
        {answers.length > 0 && !isWaiting && (
          <Button
            onClick={handleBackspace}
            variant="outlined"
            disabled={submitTask.isPending}
            sx={{ minWidth: 48, minHeight: 48 }}
            aria-label={t("game.removeNote")}
          >
            ⌫
          </Button>
        )}
      </Box>

      <NoteButtons
        clef={clef}
        octave={task.notes[Math.min(answers.length, noteCount - 1)].octave}
        noteNaming={noteNaming}
        onAnswer={handleAnswer}
        disabled={
          isWaiting || submitTask.isPending || answers.length >= noteCount
        }
      />
    </Box>
  );
}
