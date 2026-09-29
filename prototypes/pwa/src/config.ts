export const basePath = import.meta.env.BASE_URL;
export const languages = ["en", "ru", "es"] as const;
export type Language = (typeof languages)[number];

export function isLanguage(value: string): value is Language {
  return languages.some((language) => language === value);
}

function positiveInteger(value: string, name: string): number {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed <= 0) {
    throw new Error(`${name} must be a positive integer`);
  }
  return parsed;
}

const configuredLanguage = import.meta.env.VITE_DEFAULT_LANGUAGE ?? "en";
if (!isLanguage(configuredLanguage)) {
  throw new Error("VITE_DEFAULT_LANGUAGE must be en, ru, or es");
}
export const defaultLanguage = configuredLanguage;
export const maxShareBytes = positiveInteger(
  import.meta.env.VITE_MAX_SHARE_BYTES ?? "26214400",
  "VITE_MAX_SHARE_BYTES",
);
export const workerTimeout = positiveInteger(
  import.meta.env.VITE_SW_READY_TIMEOUT_MS ?? "15000",
  "VITE_SW_READY_TIMEOUT_MS",
);
