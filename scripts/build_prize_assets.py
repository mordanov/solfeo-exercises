"""Extract the owner's 5-by-4 sheet without clipping unevenly placed badges."""

import argparse
from collections import deque
from collections.abc import Iterator
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SIZE = 256
PADDING = 8
COLUMNS = 5
ROWS = 4
ALPHA_THRESHOLD = 32
Bounds = tuple[int, int, int, int]

# This order describes the supplied artwork, not a sortable server catalog.
SHEET_CODES = (
    "first_round",
    "first_win",
    "perfect_round",
    "correct_streak_10",
    "notes_100",
    "note_rainbow",
    "treble_25",
    "bass_25",
    "both_clefs",
    "duet",
    "trio",
    "quartet",
    "all_difficulties",
    "independent_win",
    "days_streak_3",
    "days_7",
    "level_2",
    "level_5",
    "wins_10",
    "welcome_back",
)


def components(alpha: Image.Image) -> Iterator[tuple[list[int], Bounds]]:
    width, height = alpha.size
    values = alpha.tobytes()
    seen = bytearray(len(values))
    for start, value in enumerate(values):
        if value < ALPHA_THRESHOLD or seen[start]:
            continue
        queue = deque([start])
        seen[start] = 1
        pixels: list[int] = []
        left, top, right, bottom = width, height, 0, 0
        while queue:
            position = queue.popleft()
            pixels.append(position)
            y, x = divmod(position, width)
            left, top = min(left, x), min(top, y)
            right, bottom = max(right, x), max(bottom, y)
            for neighbor in (
                position - 1 if x else -1,
                position + 1 if x + 1 < width else -1,
                position - width if y else -1,
                position + width if y + 1 < height else -1,
            ):
                if (
                    neighbor >= 0
                    and not seen[neighbor]
                    and values[neighbor] >= ALPHA_THRESHOLD
                ):
                    seen[neighbor] = 1
                    queue.append(neighbor)
        yield pixels, (left, top, right + 1, bottom + 1)


def extract(source: Path) -> dict[str, Image.Image]:
    with Image.open(source) as image:
        if image.format != "PNG" or image.mode != "RGBA":
            raise ValueError("The source must be a transparent RGBA PNG.")
        alpha = image.getchannel("A")
        if alpha.getextrema() == (255, 255):
            raise ValueError("The source must have a genuinely transparent background.")
        minimum_area = image.width * image.height // (len(SHEET_CODES) * 5)
        badges = [
            (pixels, bounds)
            for pixels, bounds in components(alpha)
            if len(pixels) >= minimum_area
        ]
        if len(badges) != len(SHEET_CODES):
            raise ValueError(f"Expected 20 separate badges, found {len(badges)}.")
        output: dict[str, Image.Image] = {}
        for pixels, bounds in badges:
            left, top, right, bottom = bounds
            column = ((left + right) * COLUMNS) // (2 * image.width)
            row = ((top + bottom) * ROWS) // (2 * image.height)
            code = SHEET_CODES[row * COLUMNS + column]
            if code in output:
                raise ValueError(f"Multiple badges occupy the {code} grid cell.")
            bounds = (
                max(0, left - 2),
                max(0, top - 2),
                min(image.width, right + 2),
                min(image.height, bottom + 2),
            )
            crop = image.crop(bounds)
            mask = bytearray(crop.width * crop.height)
            for position in pixels:
                y, x = divmod(position, image.width)
                mask[(y - bounds[1]) * crop.width + x - bounds[0]] = 255
            silhouette = Image.frombytes("L", crop.size, bytes(mask)).filter(
                ImageFilter.MaxFilter(5)
            )
            crop.putalpha(ImageChops.multiply(crop.getchannel("A"), silhouette))
            content = crop.getchannel("A").getbbox()
            if content is None:
                raise ValueError(f"The {code} badge has no visible pixels.")
            crop = crop.crop(content)
            crop.thumbnail(
                (SIZE - 2 * PADDING, SIZE - 2 * PADDING),
                Image.Resampling.LANCZOS,
            )
            normalized = Image.new("RGBA", (SIZE, SIZE))
            normalized.paste(
                crop,
                ((SIZE - crop.width) // 2, (SIZE - crop.height) // 2),
            )
            output[code] = normalized
        return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "trophies.png")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "frontend/public/assets/prizes"
    )
    arguments = parser.parse_args()
    images = extract(arguments.source)
    arguments.output.mkdir(parents=True, exist_ok=True)
    for code in SHEET_CODES:
        path = arguments.output / f"{code}.png"
        images[code].save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main()
