export const animals = [
  "unicorn",
  "dragon",
  "phoenix",
  "griffin",
  "sphinx_cat",
  "kitsune_fox",
  "pegasus",
  "mermaid",
  "lion",
  "panda",
  "rhino",
] as const;
export type AvatarMood = "neutral" | "happy" | "sad";

export function roundMood(correct: number): AvatarMood {
  return correct >= 5 ? "happy" : correct >= 3 ? "neutral" : "sad";
}

export function avatarSource(
  animal: string,
  level: number,
  mood: AvatarMood,
  customId?: number | null,
): string {
  if (customId)
    return `/api/game/avatars/${customId}/files/${mood}?level=${level}`;
  return `/assets/avatars/${animal}/${animal}_${String(level).padStart(2, "0")}_${mood}.png`;
}
