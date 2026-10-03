import { Alert, Box, Button, Typography } from "@mui/material";
import { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { useSubmitTask } from "../api/hooks";
import Staff from "../staff/Staff";
import NoteButtons from "./NoteButtons";
import Timer from "./Timer";

interface Note {
  name: string;
  octave: number;
}
interface Task {
  index: number;
  clef: string;
  notes: Note[];
}
export interface RoundResult {
  score: number;
  correct_count: number;
  is_win: boolean;
  xp_gained: number;
  level_up: boolean;
  new_trophy: number | null;
  practice_hint: string;
}

interface Props {
  roundId: number;
  csrf: string;
  initialTask: Task;
  noteNaming?: "solfege" | "letters";
  noteCount: number;
  difficulty: string;
  timeLimitMs: number;
  onResult: (result: RoundResult) => void;
}

type FeedbackState = "idle" | "correct" | "wrong" | "timeout";

export default function PlayScreen({
  roundId,
  csrf,
  initialTask,
  noteNaming = "solfege",
  noteCount,
  timeLimitMs,
  onResult,
}: Props) {
  const { t } = useTranslation();
  const [task, setTask] = useState<Task>(initialTask);
  const [answers, setAnswers] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<FeedbackState>("idle");
  const [timerKey, setTimerKey] = useState(0);
  const submittingRef = useRef(false);
  const submitTask = useSubmitTask(roundId);

  const doSubmit = useCallback(
    (givenAnswers: string[] | null, timedOut: boolean) => {
      if (submittingRef.current) return;
      submittingRef.current = true;

      const body = timedOut
        ? { csrf, task_index: task.index, timed_out: true as const }
        : {
            csrf,
            task_index: task.index,
            answers:
              givenAnswers?.map((name) => ({
                name,
                octave: task.notes[0].octave,
              })) ?? null,
          };

      submitTask.mutate(body, {
        onSuccess: (data) => {
          setFeedback(
            timedOut ? "timeout" : data.is_correct ? "correct" : "wrong",
          );
          setTimeout(() => {
            submittingRef.current = false;
            if (data.result) {
              onResult(data.result);
            } else if (data.next_task) {
              setTask(data.next_task);
              setAnswers([]);
              setFeedback("idle");
              setTimerKey((k) => k + 1);
            }
          }, 900);
        },
        onError: () => {
          submittingRef.current = false;
        },
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [csrf, task.index, submitTask, onResult],
  );

  const handleAnswer = (name: string) => {
    if (feedback !== "idle") return;
    const next = [...answers, name];
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
        totalMs={timeLimitMs}
        onExpire={handleTimeout}
        paused={isWaiting}
      />

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

      <Box sx={{ background: "#FFFDF5", borderRadius: 3, p: 2, my: 2 }}>
        <Staff notes={task.notes} clef={clef} />
      </Box>

      <Box sx={{ display: "flex", gap: 1, justifyContent: "center", mb: 1 }}>
        {Array.from({ length: noteCount }).map((_, i) => (
          <Box
            key={i}
            sx={{
              width: 48,
              height: 48,
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
            {answers[i]
              ? t(`game.noteNames.${noteNaming}.${answers[i]}` as const)
              : ""}
          </Box>
        ))}
        {answers.length > 0 && !isWaiting && (
          <Button
            onClick={handleBackspace}
            variant="outlined"
            sx={{ minWidth: 48, minHeight: 48 }}
            aria-label="Backspace"
          >
            ⌫
          </Button>
        )}
      </Box>

      <NoteButtons
        clef={clef}
        noteNaming={noteNaming}
        onAnswer={handleAnswer}
        disabled={isWaiting || answers.length >= noteCount}
      />
    </Box>
  );
}
