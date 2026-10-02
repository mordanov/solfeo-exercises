import { config } from "../config";
import { isLanguage, type Language } from "../configuration";
import {
  isColorScheme,
  isUiFont,
  isUiFontSize,
  type Appearance,
} from "../appearance";

export type Role = "manager" | "student";
export type NoteNaming = "letters" | "solfege";
export type User = Appearance & {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  role: Role;
  is_active: boolean;
  is_emergency: boolean;
  must_change_password: boolean;
  ui_language: Language;
  note_naming: NoteNaming;
};
export type Auth = { user: User; csrf_token: string };
export type NewUser = Pick<
  User,
  "username" | "first_name" | "last_name" | "role" | "must_change_password"
> & { password: string };
export type UserChanges = Partial<
  Pick<User, "first_name" | "last_name" | "role" | "is_active">
>;

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    public readonly status = 0,
  ) {
    super(code);
    this.name = "ApiError";
  }
}

export function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function parseUser(value: unknown): User {
  if (
    !record(value) ||
    typeof value.id !== "number" ||
    !Number.isSafeInteger(value.id) ||
    value.id <= 0 ||
    typeof value.username !== "string" ||
    typeof value.first_name !== "string" ||
    typeof value.last_name !== "string" ||
    (value.role !== "manager" && value.role !== "student") ||
    typeof value.is_active !== "boolean" ||
    typeof value.is_emergency !== "boolean" ||
    typeof value.must_change_password !== "boolean" ||
    typeof value.ui_language !== "string" ||
    !isLanguage(value.ui_language) ||
    (value.note_naming !== "letters" && value.note_naming !== "solfege") ||
    !isColorScheme(value.light_scheme) ||
    !isColorScheme(value.dark_scheme) ||
    !isUiFont(value.ui_font) ||
    !isUiFontSize(value.ui_font_size)
  )
    throw new ApiError("INVALID_RESPONSE");
  return {
    id: value.id,
    username: value.username,
    first_name: value.first_name,
    last_name: value.last_name,
    role: value.role,
    is_active: value.is_active,
    is_emergency: value.is_emergency,
    must_change_password: value.must_change_password,
    ui_language: value.ui_language,
    note_naming: value.note_naming,
    light_scheme: value.light_scheme,
    dark_scheme: value.dark_scheme,
    ui_font: value.ui_font,
    ui_font_size: value.ui_font_size,
  };
}

function parseAuth(value: unknown): Auth {
  if (
    !record(value) ||
    typeof value.csrf_token !== "string" ||
    !value.csrf_token
  ) {
    throw new ApiError("INVALID_RESPONSE");
  }
  return { user: parseUser(value.user), csrf_token: value.csrf_token };
}

export async function request(
  path: string,
  method = "GET",
  body?: unknown,
  csrf?: string,
  signal?: AbortSignal,
  keepalive = false,
  responseType: "json" | "text" = "json",
): Promise<unknown> {
  signal?.throwIfAborted();
  const controller = new AbortController();
  const abort = () => controller.abort(signal?.reason);
  signal?.addEventListener("abort", abort, { once: true });
  const timer = window.setTimeout(
    () => controller.abort(),
    config.healthTimeoutMs,
  );
  try {
    const response = await fetch(`/api${path}`, {
      method,
      credentials: "same-origin",
      cache: "no-store",
      keepalive,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(csrf ? { "X-CSRF-Token": csrf } : {}),
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    let data: unknown;
    try {
      data =
        responseType === "text" && response.ok
          ? await response.text()
          : await response.json();
    } catch {
      throw new ApiError(
        response.ok
          ? "INVALID_RESPONSE"
          : response.status === 429
            ? "RATE_LIMITED"
            : "SERVICE_UNAVAILABLE",
        response.status,
      );
    }
    if (!response.ok) {
      if (
        response.status === 401 &&
        path !== "/auth/login" &&
        path !== "/auth/me"
      ) {
        window.dispatchEvent(new Event("solfeo:unauthorized"));
      }
      throw new ApiError(
        record(data) && typeof data.error === "string" ? data.error : "UNKNOWN",
        response.status,
      );
    }
    return data;
  } catch (error: unknown) {
    if (signal?.aborted) throw signal.reason;
    if (controller.signal.aborted) throw new ApiError("REQUEST_TIMEOUT");
    if (error instanceof ApiError) throw error;
    throw new ApiError("NETWORK_ERROR");
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", abort);
  }
}

export async function fetchMe(signal?: AbortSignal): Promise<Auth | null> {
  try {
    return parseAuth(
      await request("/auth/me", "GET", undefined, undefined, signal),
    );
  } catch (error: unknown) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}
export async function login(username: string, password: string): Promise<Auth> {
  return parseAuth(
    await request("/auth/login", "POST", { username, password }),
  );
}
export async function logout(csrf: string): Promise<void> {
  await request("/auth/logout", "POST", {}, csrf);
}
export async function changePassword(
  csrf: string,
  current_password: string,
  new_password: string,
): Promise<Auth> {
  return parseAuth(
    await request(
      "/auth/password",
      "PUT",
      { current_password, new_password },
      csrf,
    ),
  );
}
export async function saveSettings(
  csrf: string,
  ui_language: Language,
  note_naming: NoteNaming,
): Promise<User> {
  return parseUser(
    await request("/settings", "PATCH", { ui_language, note_naming }, csrf),
  );
}
export async function saveAppearance(
  csrf: string,
  appearance: Appearance,
): Promise<User> {
  return parseUser(await request("/settings", "PATCH", appearance, csrf));
}
export async function listUsers(
  offset: number,
  signal?: AbortSignal,
): Promise<{ users: User[]; total: number }> {
  const data = await request(
    `/users?offset=${offset}&limit=50`,
    "GET",
    undefined,
    undefined,
    signal,
  );
  if (
    !record(data) ||
    !Array.isArray(data.users) ||
    typeof data.total !== "number" ||
    !Number.isSafeInteger(data.total) ||
    data.total < 0
  )
    throw new ApiError("INVALID_RESPONSE");
  return { users: data.users.map(parseUser), total: data.total };
}
export async function createUser(csrf: string, user: NewUser): Promise<User> {
  return parseUser(await request("/users", "POST", user, csrf));
}
export async function updateUser(
  csrf: string,
  id: number,
  changes: UserChanges,
): Promise<User> {
  return parseUser(await request(`/users/${id}`, "PATCH", changes, csrf));
}
export async function resetPassword(
  csrf: string,
  id: number,
  password: string,
  must_change_password: boolean,
): Promise<void> {
  await request(
    `/users/${id}/password`,
    "POST",
    { password, must_change_password },
    csrf,
  );
}
