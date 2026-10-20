import { ApiError, record, request } from "./auth";

export type ListeningEvent = {
  session_id: string;
  run_id: number;
  exercise_id: number;
  audio_id: string;
  event: "start" | "heartbeat" | "end" | "ended";
  position_seconds: number;
  csrf_token: string;
};
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
