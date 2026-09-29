export const errorCodes = [
  "SERVICE_UNAVAILABLE",
  "INVALID_RESPONSE",
  "NETWORK_ERROR",
  "REQUEST_TIMEOUT",
] as const;

export type HealthErrorCode = (typeof errorCodes)[number];
export type HealthResponse = { status: "ok" };

export class HealthError extends Error {
  constructor(public readonly code: HealthErrorCode) {
    super(code);
    this.name = "HealthError";
  }
}

export async function fetchHealth(
  signal: AbortSignal,
  timeoutMs: number,
): Promise<HealthResponse> {
  signal.throwIfAborted();
  const controller = new AbortController();
  const abort = () => controller.abort(signal.reason);
  signal.addEventListener("abort", abort, { once: true });
  const timeout = window.setTimeout(() => {
    controller.abort(new HealthError("REQUEST_TIMEOUT"));
  }, timeoutMs);
  try {
    const response = await fetch("/api/health", {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new HealthError("SERVICE_UNAVAILABLE");
    }
    const data: unknown = await response.json();
    if (
      typeof data !== "object" ||
      data === null ||
      !("status" in data) ||
      data.status !== "ok"
    ) {
      throw new HealthError("INVALID_RESPONSE");
    }
    return { status: "ok" };
  } catch (error: unknown) {
    if (controller.signal.aborted) {
      throw controller.signal.reason;
    }
    if (error instanceof HealthError) {
      throw error;
    }
    if (error instanceof SyntaxError) {
      throw new HealthError("INVALID_RESPONSE");
    }
    throw new HealthError("NETWORK_ERROR");
  } finally {
    window.clearTimeout(timeout);
    signal.removeEventListener("abort", abort);
  }
}
