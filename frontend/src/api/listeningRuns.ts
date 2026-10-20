import { ApiError, record, request } from "./auth";
import { parseExercise, type Exercise } from "./exercises";

export type { Chapter } from "./chapters";

export type RunStatus = "active" | "completed" | "cancelled";

export type RunStartRequest = { chapter_ids: number[] };
export type ChapterExercise = Exercise;

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

function positiveInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0;
}

function nonNegativeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

function isRunStatus(value: unknown): value is RunStatus {
  return value === "active" || value === "completed" || value === "cancelled";
}

export function parseListeningRun(value: unknown): ListeningRun {
  if (
    !record(value) ||
    !positiveInteger(value.id) ||
    !isRunStatus(value.status) ||
    !Array.isArray(value.chapter_numbers) ||
    !value.chapter_numbers.every(positiveInteger) ||
    new Set(value.chapter_numbers).size !== value.chapter_numbers.length ||
    !nonNegativeInteger(value.current_index) ||
    !Array.isArray(value.items)
  )
    throw new ApiError("INVALID_RESPONSE");

  const chapterNumbers: unknown[] = value.chapter_numbers;
  const rawItems: unknown[] = value.items;
  if (chapterNumbers.length === 0 || !chapterNumbers.every(positiveInteger))
    throw new ApiError("INVALID_RESPONSE");

  const items: ListeningRun["items"] = [];
  for (const item of rawItems) {
    const previousPosition = items.at(-1)?.position;
    if (
      !record(item) ||
      !nonNegativeInteger(item.position) ||
      (previousPosition !== undefined && item.position <= previousPosition) ||
      !positiveInteger(item.chapter_number) ||
      !record(item.exercise)
    )
      throw new ApiError("INVALID_RESPONSE");
    const exercise: Exercise = parseExercise(item.exercise);
    if (
      item.chapter_number !== exercise.chapter_number ||
      !chapterNumbers.includes(item.chapter_number)
    )
      throw new ApiError("INVALID_RESPONSE");
    items.push({
      position: item.position,
      chapter_number: item.chapter_number,
      exercise,
    });
  }

  const lastPosition = items.at(-1)?.position;
  if (
    (items.length === 0 && value.status === "active") ||
    (lastPosition !== undefined &&
      value.status === "active" &&
      !items.some((item) => item.position === value.current_index))
  )
    throw new ApiError("INVALID_RESPONSE");

  return {
    id: value.id,
    status: value.status,
    chapter_numbers: chapterNumbers,
    current_index: value.current_index,
    items,
  };
}

export async function getActiveListeningRun(
  signal?: AbortSignal,
): Promise<ListeningRun | null> {
  const result = await request(
    "/listening/run",
    "GET",
    undefined,
    undefined,
    signal,
  );
  return result === null ? null : parseListeningRun(result);
}

export async function createListeningRun(
  csrf: string,
  chapter_ids: number[],
): Promise<ListeningRun> {
  return parseListeningRun(
    await request("/listening/run", "POST", { chapter_ids }, csrf),
  );
}

export async function navigateListeningRun(
  csrf: string,
  run_id: number,
  direction: "next" | "previous",
): Promise<ListeningRun> {
  return parseListeningRun(
    await request(
      `/listening/run/${run_id}/navigate`,
      "POST",
      { direction },
      csrf,
    ),
  );
}

export async function cancelListeningRun(
  csrf: string,
  run_id: number,
): Promise<ListeningRun> {
  return parseListeningRun(
    await request(`/listening/run/${run_id}/cancel`, "POST", {}, csrf),
  );
}
