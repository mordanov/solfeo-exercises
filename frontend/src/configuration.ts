export type Language = "en" | "ru" | "es";

export function isLanguage(value: string): value is Language {
  return value === "en" || value === "ru" || value === "es";
}

export function readConfiguration(language = "en", timeout = "5000") {
  if (!isLanguage(language)) {
    throw new Error("VITE_DEFAULT_LANGUAGE must be en, ru, or es");
  }

  const healthTimeoutMs = Number(timeout);
  if (
    !Number.isSafeInteger(healthTimeoutMs) ||
    healthTimeoutMs <= 0 ||
    healthTimeoutMs > 2147483647
  ) {
    throw new Error(
      "VITE_HEALTH_TIMEOUT_MS must be an integer from 1 to 2147483647",
    );
  }
  return { language, healthTimeoutMs };
}

export function readUploadTimeout(value = "600000"): number {
  const timeout = Number(value);
  if (!Number.isSafeInteger(timeout) || timeout <= 0 || timeout > 2147483647)
    throw new Error(
      "VITE_UPLOAD_TIMEOUT_MS must be an integer from 1 to 2147483647",
    );
  return timeout;
}

export function readHeartbeat(value = "5000"): number {
  const interval = Number(value);
  if (!Number.isSafeInteger(interval) || interval < 1000 || interval > 60000)
    throw new Error(
      "VITE_LISTENING_HEARTBEAT_MS must be an integer from 1000 to 60000",
    );
  return interval;
}
