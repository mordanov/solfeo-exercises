import { toMidi } from "../staff/staffPos";

let ctx: AudioContext | null = null;
const MUTE_KEY = "game_muted";

export function isMuted(): boolean {
  try {
    return localStorage.getItem(MUTE_KEY) === "1";
  } catch {
    return false;
  }
}

export function setMuted(muted: boolean): void {
  try {
    localStorage.setItem(MUTE_KEY, muted ? "1" : "0");
  } catch {
    /* ignore */
  }
}

function getCtx(): AudioContext {
  if (!ctx) ctx = new AudioContext();
  return ctx;
}

export function unlockAudio(): void {
  try {
    getCtx().resume();
  } catch {
    /* ignore */
  }
}

export async function playNotes(
  notes: readonly { name: string; octave: number }[],
  signal: AbortSignal,
): Promise<void> {
  if (signal.aborted) return;
  if (isMuted()) throw new Error("GAME_AUDIO_MUTED");
  if (notes.length === 0) throw new Error("GAME_AUDIO_EMPTY");
  const frequencies = notes.map(({ name, octave }) => {
    const midi = toMidi(name, octave);
    if (
      !Number.isInteger(octave) ||
      !Number.isFinite(midi) ||
      midi < 0 ||
      midi > 127
    ) {
      throw new Error("GAME_AUDIO_INVALID_NOTE");
    }
    return 440 * Math.pow(2, (midi - 69) / 12);
  });
  const ac = getCtx();
  if (ac.state !== "running") await ac.resume();
  if (signal.aborted) return;
  if (ac.state !== "running") throw new Error("GAME_AUDIO_UNAVAILABLE");

  return new Promise<void>((resolve, reject) => {
    const oscillators: OscillatorNode[] = [];
    const gains: GainNode[] = [];
    const started = new Set<OscillatorNode>();
    let settled = false;
    const cleanup = (stop: boolean) => {
      settled = true;
      signal.removeEventListener("abort", cancel);
      for (const oscillator of oscillators) {
        oscillator.onended = null;
        if (stop && started.has(oscillator)) oscillator.stop();
        oscillator.disconnect();
      }
      for (const gain of gains) gain.disconnect();
    };
    const cancel = () => {
      if (settled) return;
      cleanup(true);
      resolve();
    };
    signal.addEventListener("abort", cancel, { once: true });
    const startTime = ac.currentTime;
    try {
      frequencies.forEach((frequency, index) => {
        const oscillator = ac.createOscillator();
        oscillators.push(oscillator);
        const gain = ac.createGain();
        gains.push(gain);
        const start = startTime + index * 0.45;
        oscillator.type = "triangle";
        oscillator.frequency.value = frequency;
        gain.gain.setValueAtTime(0.35, start);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.3);
        oscillator.connect(gain);
        gain.connect(ac.destination);
        if (index === frequencies.length - 1) {
          oscillator.onended = () => {
            if (settled) return;
            cleanup(false);
            resolve();
          };
        }
        oscillator.start(start);
        started.add(oscillator);
        oscillator.stop(start + 0.3);
      });
    } catch (error) {
      cleanup(true);
      reject(error);
    }
  });
}

export function playNote(name: string, octave: number): void {
  if (isMuted()) return;
  try {
    const ac = getCtx();
    if (ac.state === "suspended") void ac.resume();
    const midi = toMidi(name, octave);
    const freq = 440 * Math.pow(2, (midi - 69) / 12);
    const osc = ac.createOscillator();
    const gain = ac.createGain();
    osc.type = "triangle";
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.35, ac.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.3);
    osc.connect(gain);
    gain.connect(ac.destination);
    osc.start(ac.currentTime);
    osc.stop(ac.currentTime + 0.3);
  } catch {
    // Audio errors must never block input
  }
}
