import { request } from "../../../api/auth";

export const gameFetch = {
  get: <T>(path: string, signal?: AbortSignal) =>
    request(`/game${path}`, "GET", undefined, undefined, signal) as Promise<T>,

  post: <T>(path: string, csrf: string, body?: unknown) =>
    request(`/game${path}`, "POST", body, csrf) as Promise<T>,

  patch: <T>(path: string, csrf: string, body?: unknown) =>
    request(`/game${path}`, "PATCH", body, csrf) as Promise<T>,

  delete: <T>(path: string, csrf: string) =>
    request(`/game${path}`, "DELETE", undefined, csrf) as Promise<T>,
};
