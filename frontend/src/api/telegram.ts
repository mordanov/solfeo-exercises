import { ApiError, record, request } from "./auth";

export type LinkStatus = {
  linked: boolean;
  available: boolean;
  bot_username: string;
};
export type Code = { code: string; expires_at: string };
export type Import = {
  id: number;
  title: string;
  description: string;
  status: "pending" | "ready" | "failed" | "applied" | "discarded";
  last_error: string | null;
  exercise_id: number | null;
  received_at: string;
};
export type Apply = {
  exercise_id: number | null;
  title: string;
  description: string;
};

function positive(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0;
}
function date(value: unknown): value is string {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}
function importStatus(value: unknown): value is Import["status"] {
  return (
    value === "pending" ||
    value === "ready" ||
    value === "failed" ||
    value === "applied" ||
    value === "discarded"
  );
}
function parseImport(value: unknown): Import {
  if (
    !record(value) ||
    !positive(value.id) ||
    typeof value.title !== "string" ||
    typeof value.description !== "string" ||
    !importStatus(value.status) ||
    (value.last_error !== null && typeof value.last_error !== "string") ||
    (value.exercise_id !== null && !positive(value.exercise_id)) ||
    !date(value.received_at)
  )
    throw new ApiError("INVALID_RESPONSE");
  return {
    id: value.id,
    title: value.title,
    description: value.description,
    status: value.status,
    last_error: value.last_error,
    exercise_id: value.exercise_id,
    received_at: value.received_at,
  };
}
export async function status(signal?: AbortSignal): Promise<LinkStatus> {
  const data = await request("/telegram", "GET", undefined, undefined, signal);
  if (
    !record(data) ||
    typeof data.linked !== "boolean" ||
    typeof data.available !== "boolean" ||
    typeof data.bot_username !== "string" ||
    !/^[A-Za-z0-9_]{5,32}$/.test(data.bot_username)
  )
    throw new ApiError("INVALID_RESPONSE");
  return {
    linked: data.linked,
    available: data.available,
    bot_username: data.bot_username,
  };
}
export async function createCode(csrf: string): Promise<Code> {
  const data = await request("/telegram/link", "POST", undefined, csrf);
  if (
    !record(data) ||
    typeof data.code !== "string" ||
    !data.code ||
    !date(data.expires_at)
  )
    throw new ApiError("INVALID_RESPONSE");
  return { code: data.code, expires_at: data.expires_at };
}
export async function unlink(csrf: string): Promise<void> {
  await request("/telegram/link", "DELETE", undefined, csrf);
}
export async function listImports(
  offset: number,
  signal?: AbortSignal,
): Promise<{ imports: Import[]; total: number }> {
  const data = await request(
    `/telegram/imports?offset=${offset}&limit=50`,
    "GET",
    undefined,
    undefined,
    signal,
  );
  if (
    !record(data) ||
    !Array.isArray(data.imports) ||
    typeof data.total !== "number" ||
    !Number.isSafeInteger(data.total) ||
    data.total < 0
  )
    throw new ApiError("INVALID_RESPONSE");
  return { imports: data.imports.map(parseImport), total: data.total };
}
export async function applyImport(
  csrf: string,
  id: number,
  body: Apply,
): Promise<number> {
  const data = await request(
    `/telegram/imports/${id}/apply`,
    "POST",
    body,
    csrf,
  );
  if (!record(data) || !positive(data.exercise_id))
    throw new ApiError("INVALID_RESPONSE");
  return data.exercise_id;
}
export async function retryImport(csrf: string, id: number): Promise<void> {
  await request(`/telegram/imports/${id}/retry`, "POST", undefined, csrf);
}
