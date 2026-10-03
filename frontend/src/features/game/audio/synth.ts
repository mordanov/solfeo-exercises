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
