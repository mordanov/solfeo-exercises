import { basePath, maxShareBytes } from "./config";
import {
  saveShare,
  saveAttempt,
  type ShareAttempt,
  type SharedField,
} from "./storage";

export const errorCodes = [
  "EMPTY_SHARE",
  "TEXT_ONLY_SHARE",
  "UNEXPECTED_FILE_FIELD",
  "MULTIPLE_FILES",
  "EMPTY_FILE",
  "UNSUPPORTED_FILE",
  "FILE_TOO_LARGE",
  "INVALID_SHARE",
  "STORAGE_FAILED",
  "WORKER_FAILED",
  "UNKNOWN",
] as const;
export type ErrorCode = (typeof errorCodes)[number];

export function parseError(value: string | null): ErrorCode | null {
  if (value === null) return null;
  return errorCodes.find((code) => code === value) ?? "UNKNOWN";
}

export function isShareRequest(request: Request, origin: string): boolean {
  const url = new URL(request.url);
  return (
    request.method === "POST" &&
    url.origin === origin &&
    url.pathname === `${basePath}receive`
  );
}

export async function handleShare(
  request: Request,
  store: (file: File, attempt: ShareAttempt) => Promise<void> = saveShare,
  limit = maxShareBytes,
): Promise<Response> {
  const target = new URL(`${basePath}share`, request.url);
  const fields: SharedField[] = [];
  const receivedAt = Date.now();
  async function failure(code: ErrorCode): Promise<Response> {
    try {
      await saveAttempt({ receivedAt, outcome: code, fields });
    } catch {
      code = "STORAGE_FAILED";
    }
    target.searchParams.set("error", code);
    return Response.redirect(target, 303);
  }

  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return failure("INVALID_SHARE");
  }
  for (const [name, value] of form.entries()) {
    const field =
      name === "audio" || name === "text" || name === "title" || name === "url"
        ? name
        : "other";
    fields.push(
      value instanceof File
        ? { field, kind: "file", type: value.type, size: value.size }
        : { field, kind: "text", nonempty: value.trim().length > 0 },
    );
  }
  if (
    fields.some((field) => field.kind === "file" && field.field !== "audio")
  ) {
    return failure("UNEXPECTED_FILE_FIELD");
  }
  const files = form.getAll("audio");
  if (files.length === 0) {
    return failure(
      fields.some((field) => field.kind === "text" && field.nonempty)
        ? "TEXT_ONLY_SHARE"
        : "EMPTY_SHARE",
    );
  }
  if (files.length !== 1) return failure("MULTIPLE_FILES");
  const file = files[0];
  if (!(file instanceof File)) return failure("INVALID_SHARE");
  if (file.size === 0) return failure("EMPTY_FILE");
  if (file.size > limit) return failure("FILE_TOO_LARGE");
  const accepted =
    file.type.startsWith("audio/") ||
    file.type === "application/octet-stream" ||
    /\.(opus|ogg)$/i.test(file.name);
  if (!accepted) return failure("UNSUPPORTED_FILE");
  try {
    await store(file, { receivedAt, outcome: "RECEIVED", fields });
  } catch {
    return failure("STORAGE_FAILED");
  }
  return Response.redirect(target, 303);
}
