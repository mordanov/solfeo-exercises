import { readConfiguration, readUploadTimeout } from "./configuration";

export const config = readConfiguration(
  import.meta.env.VITE_DEFAULT_LANGUAGE,
  import.meta.env.VITE_HEALTH_TIMEOUT_MS,
);
export const uploadTimeoutMs = readUploadTimeout(
  import.meta.env.VITE_UPLOAD_TIMEOUT_MS,
);
