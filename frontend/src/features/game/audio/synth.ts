import Soundfont, { type Piano, type PlayingNote } from "soundfont-player";
import { GAME_NOTES } from "../notes";
import type { Note } from "../api/hooks";

export const PIANO_ASSET = "/assets/piano/salamander-c4-b5.json";
let ctx: AudioContext | null = null;
let piano: Piano | null = null;
let loading: Promise<void> | null = null;

export function isMuted(): boolean {
  try {
    return localStorage.getItem("game_muted") === "1";
  } catch {
    return false;
  }
}

export function sampleKey(note: Note, velocity = 64): string {
  if (
    !GAME_NOTES.some(
      (pitch) => pitch.name === note.name && pitch.octave === note.octave,
    )
  ) {
    throw new Error("GAME_AUDIO_INVALID_NOTE");
  }
  if (!Number.isInteger(velocity) || velocity < 1 || velocity > 127) {
    throw new Error("GAME_AUDIO_INVALID_VELOCITY");
  }
  const layer =
    velocity <= 43 ? 4 : velocity <= 64 ? 8 : velocity <= 96 ? 12 : 16;
  return `${note.name}${note.octave}-v${layer}`;
}

function getCtx(): AudioContext {
  if (!ctx || ctx.state === "closed") {
    ctx = new AudioContext();
    piano = null;
    loading = null;
  }
  return ctx;
}

export async function preparePiano(): Promise<void> {
  const ac = getCtx();
  const resume = ac.state === "running" ? Promise.resolve() : ac.resume();
  if (!loading) {
    loading = Soundfont.instrument(ac, "salamander-c4-b5", {
      nameToUrl: () => PIANO_ASSET,
      map: (key) => key,
      adsr: [0.005, 0.1, 0.9, 0.1],
    })
      .then((loaded) => {
        for (const note of GAME_NOTES) {
          for (const velocity of [40, 64, 96, 127]) {
            const buffer = loaded.buffers[sampleKey(note, velocity)];
            if (
              !buffer ||
              !Number.isFinite(buffer.duration) ||
              buffer.duration <= 0
            ) {
              throw new Error("GAME_AUDIO_MISSING_SAMPLE");
            }
          }
        }
        piano = loaded;
      })
      .catch((error: unknown) => {
        loading = null;
        throw error;
      });
  }
  await Promise.all([resume, loading]);
  if (ac.state !== "running") throw new Error("GAME_AUDIO_UNAVAILABLE");
}

export async function playNotes(
  notes: readonly Note[],
  signal: AbortSignal,
  velocity = 64,
): Promise<void> {
  if (signal.aborted) return;
  if (isMuted()) throw new Error("GAME_AUDIO_MUTED");
  if (notes.length === 0) throw new Error("GAME_AUDIO_EMPTY");
  const keys = notes.map((note) => sampleKey(note, velocity));
  await preparePiano();
  if (signal.aborted) return;
  const ac = getCtx();
  const instrument = piano;
  if (!instrument) throw new Error("GAME_AUDIO_UNAVAILABLE");

  return new Promise<void>((resolve, reject) => {
    const nodes: PlayingNote[] = [];
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      signal.removeEventListener("abort", cancel);
      resolve();
    };
    const cancel = () => {
      if (settled) return;
      for (const node of nodes) {
        node.source.stop();
      }
      finish();
    };
    signal.addEventListener("abort", cancel, { once: true });
    const start = ac.currentTime;
    try {
      keys.forEach((key, index) => {
        const node = instrument.play(key, start + index * 0.75, {
          duration: 0.5,
          gain: 0.8,
        });
        if (!node) throw new Error("GAME_AUDIO_MISSING_SAMPLE");
        nodes.push(node);
        if (index === keys.length - 1)
          node.source.addEventListener("ended", finish, { once: true });
      });
    } catch (error) {
      for (const node of nodes) node.source.stop();
      settled = true;
      signal.removeEventListener("abort", cancel);
      reject(error);
    }
  });
}
