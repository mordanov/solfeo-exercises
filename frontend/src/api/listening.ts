import { ApiError, record, request } from "./auth";
import { parseExercise, type Exercise } from "./exercises";

export type Mode = "sequential" | "random";
export type ListeningEvent = {
  session_id: string;
  exercise_id: number;
  audio_id: string;
  mode: Mode;
  event: "start" | "heartbeat" | "end" | "ended";
  position_seconds: number;
  csrf_token: string;
};
function selection(value: unknown): Exercise | null {
  if (!record(value)) throw new ApiError("INVALID_RESPONSE");
  return value.exercise === null ? null : parseExercise(value.exercise);
}
export async function currentExercise(
  signal?: AbortSignal,
): Promise<Exercise | null> {
  return selection(
    await request("/listening/current", "GET", undefined, undefined, signal),
  );
}
export async function selectExercise(
  csrf: string,
  mode: Mode,
  direction: "current" | "next" | "previous",
  current_id?: number,
  previous_id?: number,
): Promise<Exercise | null> {
  return selection(
    await request(
      "/listening/select",
      "POST",
      { mode, direction, current_id, previous_id },
      csrf,
    ),
  );
}
export async function sendListeningEvent(event: ListeningEvent): Promise<void> {
  const result = await request(
    "/listening/events",
    "POST",
    event,
    undefined,
    undefined,
    true,
  );
  if (
    !record(result) ||
    result.session_id !== event.session_id ||
    typeof result.completed !== "boolean" ||
    (result.ended_at !== null && typeof result.ended_at !== "string")
  )
    throw new ApiError("INVALID_RESPONSE");
}
export function beaconListeningEvent(
  event: ListeningEvent,
  failed: (error: unknown) => void,
): void {
  let queued = false;
  try {
    queued =
      typeof navigator.sendBeacon === "function" &&
      navigator.sendBeacon(
        "/api/listening/events",
        new Blob([JSON.stringify(event)], { type: "application/json" }),
      );
  } catch (error: unknown) {
    failed(error);
  }
  if (!queued)
    void sendListeningEvent(event).catch((error: unknown) => {
      console.warn("LISTENING_DELIVERY_FAILED");
      failed(error);
    });
}
