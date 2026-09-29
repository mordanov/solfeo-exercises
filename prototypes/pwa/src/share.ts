import { basePath, maxShareBytes } from "./config";
import { saveShare } from "./storage";

export const errorCodes = [
  "EMPTY_SHARE",
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
  store: (file: File) => Promise<void> = saveShare,
  limit = maxShareBytes,
): Promise<Response> {
  const target = new URL(`${basePath}share`, request.url);
  function failure(code: ErrorCode): Response {
    target.searchParams.set("error", code);
    return Response.redirect(target, 303);
  }

  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return failure("INVALID_SHARE");
  }
  const files = form.getAll("audio");
  if (files.length === 0) return failure("EMPTY_SHARE");
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
    await store(file);
  } catch {
    return failure("STORAGE_FAILED");
  }
  return Response.redirect(target, 303);
}
