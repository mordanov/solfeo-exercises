export type Language = "en" | "ru" | "es";

const spokenDefaults = {
  defaultBpm: 72,
  minBpm: 40,
  maxBpm: 160,
  minRate: 0.75,
  maxRate: 1.5,
  maxSeconds: 1800,
  maxClipBytes: 2097152,
  maxClipSeconds: 5,
};
export function readSpokenConfiguration(value?: string): typeof spokenDefaults {
  const parsed: unknown = value ? JSON.parse(value) : spokenDefaults;
  if (typeof parsed !== "object" || parsed === null)
    throw new Error("INVALID_SPOKEN_CONFIG");
  const result = { ...spokenDefaults };
  for (const key of Object.keys(
    spokenDefaults,
  ) as (keyof typeof spokenDefaults)[]) {
    const candidate: unknown = Reflect.get(parsed, key);
    if (
      typeof candidate !== "number" ||
      !Number.isFinite(candidate) ||
      candidate <= 0
    )
      throw new Error("INVALID_SPOKEN_CONFIG");
    result[key] = candidate;
  }
  if (
    !Number.isInteger(result.minBpm) ||
    !Number.isInteger(result.maxBpm) ||
    !Number.isInteger(result.defaultBpm) ||
    result.defaultBpm < result.minBpm ||
    result.defaultBpm > result.maxBpm ||
    result.minRate > result.maxRate ||
    result.maxRate > 4 ||
    result.maxBpm > 400 ||
    result.maxSeconds > 3600 ||
    result.maxClipBytes > 10485760 ||
    result.maxClipSeconds > 30
  )
    throw new Error("INVALID_SPOKEN_CONFIG");
  return result;
}

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
