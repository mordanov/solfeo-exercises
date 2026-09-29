import { ApiError, record, request } from "./auth";
import { uploadTimeoutMs } from "../config";

export type Media = {
  id: string;
  mime_type: string;
  size_bytes: number;
  duration_seconds: number | null;
};
export type Exercise = {
  id: number;
  title: string;
  description: string;
  category: string | null;
  position: number;
  image: Media | null;
  audio: Media | null;
};

function parseMedia(value: unknown): Media | null {
  if (value === null) return null;
  if (
    !record(value) ||
    typeof value.id !== "string" ||
    typeof value.mime_type !== "string" ||
    typeof value.size_bytes !== "number" ||
    !Number.isSafeInteger(value.size_bytes) ||
    value.size_bytes <= 0 ||
    (value.duration_seconds !== null &&
      (typeof value.duration_seconds !== "number" ||
        !Number.isFinite(value.duration_seconds) ||
        value.duration_seconds <= 0))
  )
    throw new ApiError("INVALID_RESPONSE");
  return {
    id: value.id,
    mime_type: value.mime_type,
    size_bytes: value.size_bytes,
    duration_seconds: value.duration_seconds,
  };
}

export function parseExercise(value: unknown): Exercise {
  if (
    !record(value) ||
    typeof value.id !== "number" ||
    !Number.isSafeInteger(value.id) ||
    value.id <= 0 ||
    typeof value.title !== "string" ||
    typeof value.description !== "string" ||
    (value.category !== null && typeof value.category !== "string") ||
    typeof value.position !== "number" ||
    !Number.isSafeInteger(value.position) ||
    value.position < 0
  )
    throw new ApiError("INVALID_RESPONSE");
  const image = parseMedia(value.image),
    audio = parseMedia(value.audio);
  if (!image && !audio) throw new ApiError("INVALID_RESPONSE");
  return {
    id: value.id,
    title: value.title,
    description: value.description,
    category: value.category,
    position: value.position,
    image,
    audio,
  };
}

export async function listExercises(
  signal?: AbortSignal,
): Promise<{ exercises: Exercise[]; total: number }> {
  const data = await request("/exercises", "GET", undefined, undefined, signal);
  if (
    !record(data) ||
    !Array.isArray(data.exercises) ||
    typeof data.total !== "number" ||
    !Number.isSafeInteger(data.total) ||
    data.total < 0
  )
    throw new ApiError("INVALID_RESPONSE");
  return { exercises: data.exercises.map(parseExercise), total: data.total };
}

export async function deleteExercise(csrf: string, id: number): Promise<void> {
  await request(`/exercises/${id}`, "DELETE", undefined, csrf);
}

export async function reorderExercises(
  csrf: string,
  ids: number[],
): Promise<void> {
  await request("/exercises/order", "PUT", { ids }, csrf);
}

export function saveExercise(
  csrf: string,
  id: number | null,
  data: FormData,
  progress: (percent: number) => void,
  signal?: AbortSignal,
): Promise<Exercise> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new ApiError("UPLOAD_CANCELLED"));
      return;
    }
    const xhr = new XMLHttpRequest();
    const abort = () => xhr.abort();
    xhr.open(
      id === null ? "POST" : "PUT",
      `/api/exercises${id === null ? "" : `/${id}`}`,
    );
    xhr.timeout = uploadTimeoutMs;
    xhr.setRequestHeader("X-CSRF-Token", csrf);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable)
        progress(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status === 401)
        window.dispatchEvent(new Event("solfeo:unauthorized"));
      try {
        let value: unknown;
        try {
          value = JSON.parse(xhr.responseText);
        } catch {
          throw new ApiError(
            xhr.status === 413 ? "FILE_TOO_LARGE" : "INVALID_RESPONSE",
            xhr.status,
          );
        }
        if (xhr.status < 200 || xhr.status >= 300)
          throw new ApiError(
            record(value) && typeof value.error === "string"
              ? value.error
              : "UNKNOWN",
            xhr.status,
          );
        resolve(parseExercise(value));
      } catch (error: unknown) {
        reject(error);
      }
    };
    xhr.onerror = () => reject(new ApiError("NETWORK_ERROR"));
    xhr.ontimeout = () => reject(new ApiError("REQUEST_TIMEOUT"));
    xhr.onabort = () => reject(new ApiError("UPLOAD_CANCELLED"));
    xhr.onloadend = () => signal?.removeEventListener("abort", abort);
    signal?.addEventListener("abort", abort, { once: true });
    xhr.send(data);
  });
}
