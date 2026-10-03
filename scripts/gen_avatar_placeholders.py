#!/usr/bin/env python3
"""Generate placeholder SVG avatars for all 8 animals × 10 stages × 3 moods.

Run from the repo root:
    python scripts/gen_avatar_placeholders.py

Outputs to frontend/public/assets/avatars/{animal}/{stage}_{mood}.svg
Real PNG files dropped into the same locations take priority via the
frontend resolver fallback order (exact match → stage neutral → 01 neutral → SVG placeholder).
"""
from pathlib import Path

ANIMALS = [
    ("unicorn", "🦄", "#e8b4f0"),
    ("dragon", "🐉", "#f0b4b4"),
    ("phoenix", "🦅", "#f0d4b4"),
    ("griffin", "🦁", "#d4c4a8"),
    ("sphinx_cat", "🐱", "#c4d4f0"),
    ("kitsune_fox", "🦊", "#f0c4a8"),
    ("pegasus", "🐴", "#b4d4f0"),
    ("mermaid", "🧜", "#b4f0e8"),
]
MOODS = {
    "neutral": ("😐", "#888888"),
    "happy": ("😊", "#22aa44"),
    "sad": ("😢", "#4488cc"),
}
STAGES = range(1, 11)

OUT = Path("frontend/public/assets/avatars")


def make_svg(
    animal_emoji: str, bg_color: str, mood_emoji: str, mood_color: str, stage: int
) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120">
  <circle cx="60" cy="60" r="56" fill="{bg_color}" stroke="#fff" stroke-width="4"/>
  <text x="60" y="62" font-size="40" text-anchor="middle" dominant-baseline="middle">{animal_emoji}</text>
  <text x="96" y="26" font-size="22" text-anchor="middle" dominant-baseline="middle">{mood_emoji}</text>
  <circle cx="24" cy="96" r="14" fill="{mood_color}"/>
  <text x="24" y="100" font-size="12" font-family="monospace" fill="#fff" text-anchor="middle" dominant-baseline="middle">{stage:02d}</text>
</svg>"""


count = 0
for animal_id, animal_emoji, bg_color in ANIMALS:
    for stage in STAGES:
        for mood, (mood_emoji, mood_color) in MOODS.items():
            path = OUT / animal_id / f"{stage:02d}_{mood}.svg"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                make_svg(animal_emoji, bg_color, mood_emoji, mood_color, stage)
            )
            count += 1

print(f"Generated {count} SVG placeholder avatars under {OUT}/")
