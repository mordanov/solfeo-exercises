import { readConfiguration } from "./configuration";

export const config = readConfiguration(
  import.meta.env.VITE_DEFAULT_LANGUAGE,
  import.meta.env.VITE_HEALTH_TIMEOUT_MS,
);
