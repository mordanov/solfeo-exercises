import { ApiError, type NoteNaming } from "../../api/auth";
import { config, spokenConfig } from "../../config";
import type { Language } from "../../configuration";
import type { NoteEvent } from "./sequence";
import { clipPaths } from "./vocabulary";

type ClipTiming = {
  path: string;
  start: number;
  duration: number;
  rate: number;
};
export type PlaybackPlan = {
  total: number;
  clips: ClipTiming[];
  markers: { start: number; event: NoteEvent }[];
};
export function planPlayback(
  events: NoteEvent[],
  durations: ReadonlyMap<string, number>,
  bpm: number,
  language: Language,
  naming: NoteNaming,
  limits = spokenConfig,
): PlaybackPlan {
  if (!Number.isFinite(bpm) || bpm < limits.minBpm || bpm > limits.maxBpm)
    throw new ApiError("SPOKEN_INVALID_TEMPO");
  const plan: PlaybackPlan = { total: 0, clips: [], markers: [] };
  for (const event of events) {
    const seconds = (event.beats * 60) / bpm;
    if (!Number.isFinite(seconds) || seconds <= 0)
      throw new ApiError("SPOKEN_UNSUPPORTED_SCORE");
    plan.markers.push({ start: plan.total, event });
    if (event.pitch) {
      const paths = clipPaths(
        event.pitch.step,
        event.pitch.alter,
        language,
        naming,
      );
      const sizes = paths.map((path) => {
        const duration = durations.get(path);
        if (
          !duration ||
          !Number.isFinite(duration) ||
          duration > limits.maxClipSeconds
        )
          throw new ApiError("SPOKEN_CLIPS_UNAVAILABLE");
        return duration;
      });
      const requiredRate = sizes.reduce((sum, size) => sum + size, 0) / seconds;
      if (requiredRate > limits.maxRate + 1e-9)
        throw new ApiError("SPOKEN_TEMPO_TOO_FAST");
      const rate = Math.max(
        limits.minRate,
        Math.min(limits.maxRate, requiredRate),
      );
      let start = plan.total;
      paths.forEach((path, index) => {
        const duration = sizes[index] / rate;
        plan.clips.push({ path, start, rate, duration });
        start += duration;
      });
    }
    plan.total += seconds;
    if (plan.total > limits.maxSeconds) throw new ApiError("SPOKEN_TOO_LONG");
  }
  return plan;
}

export function scheduleAudio(
  context: BaseAudioContext,
  plan: PlaybackPlan,
  buffers: ReadonlyMap<string, AudioBuffer>,
  start: number,
): AudioBufferSourceNode[] {
  const sources: AudioBufferSourceNode[] = [];
  for (const clip of plan.clips) {
    const buffer = buffers.get(clip.path);
    if (!buffer) throw new ApiError("SPOKEN_CLIPS_UNAVAILABLE");
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.playbackRate.value = clip.rate;
    source.connect(context.destination);
    source.start(start + clip.start);
    sources.push(source);
  }
  return sources;
}

export class SpeechPlayer {
  private context: AudioContext | undefined;
  private controller: AbortController | undefined;
  private sources: AudioBufferSourceNode[] = [];
  private frame: number | undefined;
  private generation = 0;
  constructor(
    private position: (event: NoteEvent | null) => void,
    private ended: () => void,
    private failed: (error: unknown) => void,
  ) {}

  stop() {
    this.generation++;
    this.controller?.abort();
    this.controller = undefined;
    if (this.frame !== undefined) cancelAnimationFrame(this.frame);
    this.frame = undefined;
    for (const source of this.sources) {
      source.stop();
      source.disconnect();
    }
    this.sources = [];
    const context = this.context;
    this.context = undefined;
    if (context && context.state !== "closed") {
      void context
        .close()
        .catch(() => console.error("SPOKEN_AUDIO_CLOSE_FAILED"));
    }
    this.position(null);
  }

  async play(
    load: (signal: AbortSignal) => Promise<NoteEvent[]>,
    bpm: number,
    language: Language,
    naming: NoteNaming,
    ready: () => void,
  ): Promise<void> {
    this.stop();
    const generation = this.generation;
    const controller = new AbortController();
    this.controller = controller;
    try {
      // Resume within the click handler, before any network await (Safari).
      const context = new AudioContext();
      this.context = context;
      await context.resume();
      const events = await load(controller.signal);
      if (generation !== this.generation) return;
      const paths = new Set(
        events.flatMap((event) =>
          event.pitch
            ? clipPaths(event.pitch.step, event.pitch.alter, language, naming)
            : [],
        ),
      );
      const buffers = new Map<string, AudioBuffer>();
      for (const path of paths) {
        const timer = window.setTimeout(
          () => controller.abort(),
          config.healthTimeoutMs,
        );
        try {
          const response = await fetch(path, {
            signal: controller.signal,
            credentials: "same-origin",
          });
          if (!response.ok) throw new ApiError("SPOKEN_CLIPS_UNAVAILABLE");
          const type = response.headers.get("content-type")?.split(";")[0];
          if (
            !["audio/mp4", "audio/x-m4a", "application/octet-stream"].includes(
              type ?? "",
            )
          )
            throw new ApiError("SPOKEN_CLIPS_UNAVAILABLE");
          const reader = response.body?.getReader();
          if (!reader) throw new ApiError("SPOKEN_CLIPS_UNAVAILABLE");
          const chunks: Uint8Array<ArrayBuffer>[] = [];
          let size = 0;
          try {
            while (true) {
              const next = await reader.read();
              if (next.done) break;
              size += next.value.byteLength;
              if (size > spokenConfig.maxClipBytes)
                throw new ApiError("SPOKEN_CLIPS_UNAVAILABLE");
              chunks.push(new Uint8Array(next.value));
            }
          } finally {
            await reader.cancel();
          }
          if (!size) throw new ApiError("SPOKEN_CLIPS_UNAVAILABLE");
          const data = new Uint8Array(size);
          let offset = 0;
          for (const chunk of chunks) {
            data.set(chunk, offset);
            offset += chunk.length;
          }
          let buffer: AudioBuffer;
          try {
            buffer = await context.decodeAudioData(data.buffer);
          } catch {
            throw new ApiError("SPOKEN_CLIPS_UNAVAILABLE");
          }
          if (controller.signal.aborted)
            throw new ApiError("SPOKEN_AUDIO_ERROR");
          buffers.set(path, buffer);
        } finally {
          clearTimeout(timer);
        }
        if (generation !== this.generation) return;
      }
      if (generation !== this.generation) return;
      const plan = planPlayback(
        events,
        new Map([...buffers].map(([path, buffer]) => [path, buffer.duration])),
        bpm,
        language,
        naming,
      );
      const start = context.currentTime + 0.05;
      this.sources = scheduleAudio(context, plan, buffers, start);
      ready();
      let last = -1;
      const tick = () => {
        if (generation !== this.generation) return;
        const elapsed = context.currentTime - start;
        if (elapsed >= plan.total) {
          this.stop();
          this.ended();
          return;
        }
        let index = last;
        while (
          index + 1 < plan.markers.length &&
          plan.markers[index + 1].start <= elapsed
        )
          index++;
        if (index !== last) {
          last = index;
          this.position(plan.markers[index].event);
        }
        this.frame = requestAnimationFrame(tick);
      };
      tick();
    } catch (error: unknown) {
      if (generation !== this.generation) return;
      this.stop();
      this.failed(
        error instanceof ApiError ? error : new ApiError("SPOKEN_AUDIO_ERROR"),
      );
    }
  }
}
