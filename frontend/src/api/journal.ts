import { ApiError, record, request } from "./auth";

export type JournalEntry = {
  id: number;
  session_id: string;
  user_id: number;
  username: string;
  first_name: string;
  last_name: string;
  exercise_id: number;
  exercise_title: string;
  exercise_deleted: boolean;
  started_at: string;
  last_heartbeat_at: string;
  ended_at: string | null;
  max_position_sec: number;
  audio_duration_sec: number;
  completed: boolean;
};
export type JournalFilters = {
  student_id?: string;
  exercise_id?: string;
  started_from?: string;
  started_to?: string;
};
export type JournalOption = { id: number; label: string; deleted: boolean };
function text(value: unknown): string {
  if (typeof value !== "string") throw new ApiError("INVALID_RESPONSE");
  return value;
}
function number(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0)
    throw new ApiError("INVALID_RESPONSE");
  return value;
}
function boolean(value: unknown): boolean {
  if (typeof value !== "boolean") throw new ApiError("INVALID_RESPONSE");
  return value;
}
function date(value: unknown): string {
  const result = text(value);
  if (!Number.isFinite(Date.parse(result)))
    throw new ApiError("INVALID_RESPONSE");
  return result;
}
export function parseJournal(value: unknown): JournalEntry {
  if (!record(value)) throw new ApiError("INVALID_RESPONSE");
  return {
    id: number(value.id),
    session_id: text(value.session_id),
    user_id: number(value.user_id),
    username: text(value.username),
    first_name: text(value.first_name),
    last_name: text(value.last_name),
    exercise_id: number(value.exercise_id),
    exercise_title: text(value.exercise_title),
    exercise_deleted: boolean(value.exercise_deleted),
    started_at: date(value.started_at),
    last_heartbeat_at: date(value.last_heartbeat_at),
    ended_at: value.ended_at === null ? null : date(value.ended_at),
    max_position_sec: number(value.max_position_sec),
    audio_duration_sec: number(value.audio_duration_sec),
    completed: boolean(value.completed),
  };
}
export async function listJournal(
  filters: JournalFilters,
  offset: number,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({ offset: String(offset), limit: "50" });
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const result = await request(
    `/journal?${params}`,
    "GET",
    undefined,
    undefined,
    signal,
  );
  if (!record(result) || !Array.isArray(result.sessions))
    throw new ApiError("INVALID_RESPONSE");
  return {
    sessions: result.sessions.map(parseJournal),
    total: number(result.total),
  };
}
export async function journalOptions(
  signal?: AbortSignal,
): Promise<{ students: JournalOption[]; exercises: JournalOption[] }> {
  const result = await request(
    "/journal/options",
    "GET",
    undefined,
    undefined,
    signal,
  );
  if (
    !record(result) ||
    !Array.isArray(result.students) ||
    !Array.isArray(result.exercises)
  )
    throw new ApiError("INVALID_RESPONSE");
  function option(value: unknown): JournalOption {
    if (!record(value)) throw new ApiError("INVALID_RESPONSE");
    return {
      id: number(value.id),
      label: text(value.label),
      deleted: boolean(value.deleted),
    };
  }
  return {
    students: result.students.map(option),
    exercises: result.exercises.map(option),
  };
}

export function dateBoundary(
  value: string,
  followingDay = false,
): string | undefined {
  if (!value) return undefined;
  const [year, month, day] = value.split("-").map(Number);
  const result = new Date(year, month - 1, day + (followingDay ? 1 : 0));
  if (!Number.isFinite(result.getTime()))
    throw new ApiError("VALIDATION_ERROR");
  return result.toISOString();
}
