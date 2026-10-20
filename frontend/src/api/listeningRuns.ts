import type { Exercise } from "./exercises";
export type { Chapter } from "./chapters";

export type RunStatus = "active" | "completed" | "cancelled";

export type RunStartRequest = { chapter_ids: number[] };
export type ChapterExercise = Exercise & {
  chapter_id: number;
  chapter_number: number;
};

export type ListeningRun = {
  id: number;
  status: RunStatus;
  chapter_numbers: number[];
  current_index: number;
  items: Array<{
    position: number;
    chapter_number: number;
    exercise: ChapterExercise;
  }>;
};
