import { ApiError, record, request } from "./auth";

export type Chapter = {
  id: number;
  number: number;
  active_exercise_count: number;
  assigned_exercise_count: number;
};

function positiveInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0;
}

function count(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

function parseChapter(value: unknown): Chapter {
  if (
    !record(value) ||
    !positiveInteger(value.id) ||
    !positiveInteger(value.number) ||
    !count(value.active_exercise_count) ||
    !count(value.assigned_exercise_count)
  )
    throw new ApiError("INVALID_RESPONSE");
  return {
    id: value.id,
    number: value.number,
    active_exercise_count: value.active_exercise_count,
    assigned_exercise_count: value.assigned_exercise_count,
  };
}

async function list(path: string, signal?: AbortSignal): Promise<Chapter[]> {
  const result = await request(path, "GET", undefined, undefined, signal);
  if (!record(result) || !Array.isArray(result.chapters))
    throw new ApiError("INVALID_RESPONSE");
  return result.chapters.map(parseChapter);
}

export function listChapters(signal?: AbortSignal): Promise<Chapter[]> {
  return list("/chapters", signal);
}

export function listListeningChapters(
  signal?: AbortSignal,
): Promise<Chapter[]> {
  return list("/listening/chapters", signal);
}

export async function createChapter(csrf: string): Promise<Chapter> {
  return parseChapter(await request("/chapters", "POST", undefined, csrf));
}

export async function deleteChapter(csrf: string, id: number): Promise<void> {
  await request(`/chapters/${id}`, "DELETE", undefined, csrf);
}
