interface AvatarImageProps {
  animalId: string;
  stage?: number;
  mood?: "neutral" | "happy" | "sad";
  size?: number;
  customBasePath?: string | null;
  customMoodPath?: string | null;
}

const PLACEHOLDER_COLORS: Record<string, string> = {
  unicorn: "#e8b4f0",
  dragon: "#f0b4b4",
  phoenix: "#f0d4b4",
  griffin: "#d4c4a8",
  sphinx_cat: "#c4d4f0",
  kitsune_fox: "#f0c4a8",
  pegasus: "#b4d4f0",
  mermaid: "#b4f0e8",
};
const ANIMAL_EMOJI: Record<string, string> = {
  unicorn: "🦄",
  dragon: "🐉",
  phoenix: "🦅",
  griffin: "🦁",
  sphinx_cat: "🐱",
  kitsune_fox: "🦊",
  pegasus: "🐴",
  mermaid: "🧜",
};

function placeholderSvgUrl(
  animalId: string,
  stage: number,
  mood: string,
): string {
  const bg = PLACEHOLDER_COLORS[animalId] ?? "#ddd";
  const emoji = ANIMAL_EMOJI[animalId] ?? "?";
  const moodEmoji = mood === "happy" ? "😊" : mood === "sad" ? "😢" : "😐";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">
    <circle cx="60" cy="60" r="56" fill="${bg}" stroke="#fff" stroke-width="4"/>
    <text x="60" y="62" font-size="40" text-anchor="middle" dominant-baseline="middle">${emoji}</text>
    <text x="96" y="26" font-size="22" text-anchor="middle" dominant-baseline="middle">${moodEmoji}</text>
    <circle cx="24" cy="96" r="14" fill="#888"/>
    <text x="24" y="100" font-size="12" font-family="monospace" fill="#fff" text-anchor="middle" dominant-baseline="middle">${String(stage).padStart(2, "0")}</text>
  </svg>`;
  return "data:image/svg+xml;utf8," + encodeURIComponent(svg);
}

export default function AvatarImage({
  animalId,
  stage = 1,
  mood = "neutral",
  size = 80,
  customBasePath = null,
  customMoodPath = null,
}: AvatarImageProps) {
  const moodPath = mood === "neutral" ? customBasePath : customMoodPath;
  if (moodPath) {
    return (
      <img
        src={moodPath}
        width={size}
        height={size}
        alt={animalId}
        style={{ borderRadius: "50%", objectFit: "cover" }}
      />
    );
  }
  const pad = String(stage).padStart(2, "0");
  const base = `/assets/avatars/${animalId}/`;
  const fallbackSrc = placeholderSvgUrl(animalId, stage, mood);

  return (
    <img
      src={`${base}${pad}_${mood}.png`}
      width={size}
      height={size}
      alt={animalId}
      style={{ borderRadius: "50%", objectFit: "cover" }}
      onError={(e) => {
        const img = e.currentTarget;
        if (!img.dataset.s1) {
          img.dataset.s1 = "1";
          img.src = `${base}${pad}_neutral.png`;
        } else if (!img.dataset.s2) {
          img.dataset.s2 = "1";
          img.src = `${base}01_neutral.png`;
        } else {
          img.src = fallbackSrc;
          img.onerror = null;
        }
      }}
    />
  );
}
