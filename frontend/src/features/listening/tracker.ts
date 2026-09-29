import {
  beaconListeningEvent,
  sendListeningEvent,
  type ListeningEvent,
} from "../../api/listening";
import { listeningHeartbeatMs } from "../../config";

type Context = Pick<
  ListeningEvent,
  "exercise_id" | "audio_id" | "mode" | "csrf_token"
>;

export class ListeningTracker {
  private attempt: { id: string; max: number; threshold: boolean } | null =
    null;
  private timer: number | undefined;
  private queue: Promise<void> = Promise.resolve();
  constructor(
    private context: Context,
    private duration: number,
    private position: () => number,
    private failed: (error: unknown) => void,
    private recovered: () => void = () => {},
  ) {}

  private stopTimer() {
    window.clearInterval(this.timer);
    this.timer = undefined;
  }
  private sample() {
    if (this.attempt) {
      const position = this.position();
      if (Number.isFinite(position))
        this.attempt.max = Math.max(this.attempt.max, position);
    }
  }
  private data(event: ListeningEvent["event"]): ListeningEvent | null {
    this.sample();
    return this.attempt
      ? {
          ...this.context,
          session_id: this.attempt.id,
          position_seconds: this.attempt.max,
          event,
        }
      : null;
  }
  private send(event: ListeningEvent["event"]) {
    const data = this.data(event);
    if (data)
      this.queue = this.queue
        .then(() => sendListeningEvent(data))
        .then(this.recovered)
        .catch(this.failed);
    return this.queue;
  }
  play() {
    if (!this.attempt) {
      this.attempt = { id: crypto.randomUUID(), max: 0, threshold: false };
      void this.send("start");
    } else void this.send("heartbeat");
    this.stopTimer();
    this.timer = window.setInterval(() => {
      void this.send("heartbeat");
    }, listeningHeartbeatMs);
  }
  update() {
    this.sample();
    if (
      this.attempt &&
      !this.attempt.threshold &&
      this.attempt.max >= 0.9 * this.duration
    ) {
      this.attempt.threshold = true;
      void this.send("heartbeat");
    }
  }
  pause() {
    this.stopTimer();
    void this.send("heartbeat");
  }
  finish(ended = false): Promise<void> {
    this.stopTimer();
    const pending = this.send(ended ? "ended" : "end");
    this.attempt = null;
    return pending;
  }
  leave() {
    this.stopTimer();
    const data = this.data("end");
    this.attempt = null;
    if (data) beaconListeningEvent(data, this.failed);
  }
}

let active: (() => Promise<void>) | undefined;
export function registerPlayback(stop: () => Promise<void>) {
  active = stop;
  return () => {
    if (active === stop) active = undefined;
  };
}
export async function finishPlayback(): Promise<void> {
  await active?.();
}
