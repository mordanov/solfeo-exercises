import { ApiError, record, request } from "./auth";

export type OmrStatus =
  | "none"
  | "pending"
  | "processing"
  | "needs_review"
  | "approved"
  | "rejected"
  | "failed";
export type Omr = {
  job_id: string | null;
  image_id: string | null;
  status: OmrStatus;
  attempts: number;
  last_error: string | null;
};
function isStatus(value: unknown): value is OmrStatus {
  return (
    value === "none" ||
    value === "pending" ||
    value === "processing" ||
    value === "needs_review" ||
    value === "approved" ||
    value === "rejected" ||
    value === "failed"
  );
}
export function parseOmr(value: unknown): Omr {
  if (
    !record(value) ||
    !isStatus(value.status) ||
    (value.job_id !== null && typeof value.job_id !== "string") ||
    (value.image_id !== null && typeof value.image_id !== "string") ||
    typeof value.attempts !== "number" ||
    !Number.isSafeInteger(value.attempts) ||
    value.attempts < 0 ||
    (value.last_error !== null && typeof value.last_error !== "string") ||
    (value.status !== "none" && !value.job_id)
  )
    throw new ApiError("INVALID_RESPONSE");
  return {
    job_id: value.job_id,
    image_id: value.image_id,
    status: value.status,
    attempts: value.attempts,
    last_error: value.last_error,
  };
}
export async function fetchOmr(id: number, signal?: AbortSignal): Promise<Omr> {
  return parseOmr(
    await request(`/exercises/${id}/omr`, "GET", undefined, undefined, signal),
  );
}
export async function rerunOmr(id: number, csrf: string): Promise<Omr> {
  return parseOmr(
    await request(`/exercises/${id}/omr/rerun`, "POST", {}, csrf),
  );
}
export async function reviewOmr(
  id: number,
  job_id: string,
  action: "approve" | "reject",
  csrf: string,
): Promise<Omr> {
  return parseOmr(
    await request(
      `/exercises/${id}/omr/review`,
      "POST",
      { job_id, action },
      csrf,
    ),
  );
}
export async function fetchScore(
  id: number,
  version: string,
  signal: AbortSignal,
): Promise<string> {
  const data = await request(
    `/exercises/${id}/score?version=${encodeURIComponent(version)}`,
    "GET",
    undefined,
    undefined,
    signal,
    false,
    "text",
  );
  if (typeof data !== "string") throw new ApiError("INVALID_RESPONSE");
  return data;
}
