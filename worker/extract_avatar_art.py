"""Extract the owner's avatar artwork without image generation or network requests."""

import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

ROOT = Path(__file__).resolve().parents[1]
STATES = ("neutral", "happy", "sad")
# Coordinates use thousandths of the source sheet, not an assumed uniform grid.
SHEETS: dict[str, tuple[str, list[tuple[int, list[int]]], list[int]]] = {
    "dragon": (
        "dragon",
        [
            (194, [103, 201, 291, 398, 503, 612, 752, 866]),
            (431, [138, 290, 442, 614, 799]),
            (690, [163, 323, 460, 647, 824]),
            (1000, [160, 305, 450, 640, 820]),
        ],
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 9],
    ),
    "unicorn": (
        "unicorn",
        [
            (238, [108, 217, 329, 442, 548, 652, 760, 873]),
            (463, [116, 223, 329, 443, 544, 643, 760, 876]),
            (742, [129, 259, 407, 595, 795]),
            (1000, [146, 311, 473, 670, 850]),
        ],
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 9],
    ),
    "griffin": (
        "griffin",
        [
            (232, [115, 218, 317, 424, 528, 627, 743, 847]),
            (443, [175, 311, 464, 647, 808]),
            (689, [176, 323, 482, 650, 818]),
            (1000, [169, 331, 483, 657, 824]),
        ],
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 9],
    ),
    "phoenix": (
        "phoenix",
        [
            (205, [123, 217, 323, 440, 546, 657, 784, 898]),
            (451, [135, 232, 337, 457, 567, 667, 779, 880]),
            (708, [142, 274, 425, 612, 808]),
            (1000, [159, 293, 460, 655, 845]),
        ],
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 9],
    ),
    "panda": (
        "panda",
        [
            (225, [113, 208, 316, 426, 530, 635, 749, 863]),
            (460, [126, 239, 329, 435, 541, 645, 760, 881]),
            (713, [163, 308, 454, 626, 805]),
            (1000, [164, 311, 474, 651, 818]),
        ],
        list(range(1, 11)),
    ),
    "lion": (
        "lion",
        [
            (157, [186, 298, 438, 603, 736]),
            (327, [173, 319, 463, 626, 789]),
            (510, [173, 336, 490, 664, 822]),
            (739, [184, 340, 494, 663, 831]),
            (1000, [184, 346, 505, 682, 842]),
        ],
        list(range(1, 11)),
    ),
    "sphinx_cat": (
        "sphinx cat",
        [
            (282, [106, 211, 315, 439, 544, 650, 774, 885]),
            (570, [115, 219, 322, 438, 542, 648, 762, 875]),
            (1000, [108, 219, 315, 432, 534, 640, 762, 884]),
        ],
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 9],
    ),
    "pegasus": (
        "pegasus",
        [
            (233, [114, 204, 309, 421, 518, 616, 747, 863]),
            (452, [115, 225, 334, 449, 559, 666, 774, 884]),
            (720, [125, 241, 332, 455, 566, 665, 792, 901]),
            (1000, [151, 293, 443, 632, 820]),
        ],
        [1, 2, 3, 4, 5, 6, 7, 8, 10, 11],
    ),
    "rhino": (
        "rhino",
        [
            (244, [122, 226, 332, 445, 540, 651, 779, 884]),
            (464, [120, 227, 333, 448, 549, 671, 787, 891]),
            (707, [130, 234, 330, 445, 552, 674, 791, 902]),
            (1000, [154, 299, 445, 625, 805]),
        ],
        [1, 2, 3, 4, 5, 6, 7, 8, 10, 11],
    ),
    "kitsune_fox": (
        "fox",
        [
            (172, [106, 194, 290, 418, 519, 635, 750, 871]),
            (365, [123, 227, 339, 452, 551, 667, 779, 887]),
            (604, [142, 254, 392, 568, 707, 845]),
            (805, [198, 400, 604, 786]),
            (1000, [278, 646]),
        ],
        [1, 2, 3, 4, 5, 6, 7, 8, 10, 11],
    ),
    "mermaid": (
        "mermaid",
        [
            (155, [132, 267, 390, 512, 658, 812]),
            (343, [156, 285, 412, 551, 693, 833]),
            (550, [163, 327, 482, 645, 814]),
            (768, [169, 327, 471, 637, 800]),
            (1000, [181, 364, 571, 784]),
        ],
        list(range(1, 11)),
    ),
}


def trim(image: Image.Image) -> Image.Image:
    bounds = (
        image.getchannel("A").point(lambda value: 255 if value > 16 else 0).getbbox()
    )
    if bounds is None:
        raise ValueError("EMPTY_AVATAR_CROP")
    return image.crop(bounds)


def square(image: Image.Image, size: int = 384) -> Image.Image:
    # Remove disconnected pieces from neighbouring figures and source-sheet speckles.
    alpha = image.getchannel("A")
    pixels = alpha.tobytes()
    visited: set[tuple[int, int]] = set()
    largest: list[tuple[int, int]] = []
    for y in range(image.height):
        for x in range(image.width):
            if (x, y) in visited or pixels[y * image.width + x] <= 24:
                continue
            component: list[tuple[int, int]] = []
            queue = deque([(x, y)])
            visited.add((x, y))
            while queue:
                point = queue.popleft()
                component.append(point)
                px, py = point
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if (
                        0 <= nx < image.width
                        and 0 <= ny < image.height
                        and (nx, ny) not in visited
                        and pixels[ny * image.width + nx] > 24
                    ):
                        visited.add((nx, ny))
                        queue.append((nx, ny))
            if len(component) > len(largest):
                largest = component
    if not largest:
        raise ValueError("EMPTY_AVATAR_COMPONENT")
    mask = Image.new("L", image.size)
    mask_pixels = mask.load()
    assert mask_pixels is not None
    for point in largest:
        mask_pixels[point] = 255
    image.putalpha(ImageChops.multiply(alpha, mask.filter(ImageFilter.MaxFilter(5))))
    image = trim(image)
    scale = min((size - 24) / image.width, (size - 24) / image.height)
    image = image.resize(
        (round(image.width * scale), round(image.height * scale)),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", (size, size))
    canvas.alpha_composite(image, ((size - image.width) // 2, size - 12 - image.height))
    return canvas


def valley(image: Image.Image, estimate: int, axis: int, radius: int = 12) -> int:
    """Move a crop boundary to the nearest low-alpha gutter."""
    alpha = image.getchannel("A")
    extent = image.width if axis == 0 else image.height
    candidates = range(
        max(1, estimate - radius), min(extent - 1, estimate + radius) + 1
    )

    def cost(position: int) -> float:
        strip = alpha.crop(
            (position, 0, position + 1, image.height)
            if axis == 0
            else (0, position, image.width, position + 1)
        )
        return ImageStat.Stat(strip).sum[0] + abs(position - estimate) * 20

    return min(candidates, key=cost)


def seam(image: Image.Image, estimate: int, radius: int) -> list[int]:
    """Follow transparent gutters around overlapping wings instead of straight cuts."""
    alpha = image.getchannel("A")
    pixels = alpha.tobytes()
    columns = list(
        range(max(1, estimate - radius), min(image.width - 1, estimate + radius) + 1)
    )
    costs = [float(pixels[x]) + abs(x - estimate) * 0.2 for x in columns]
    parents: list[list[int]] = []
    for y in range(1, image.height):
        row: list[float] = []
        previous: list[int] = []
        for index, x in enumerate(columns):
            options = range(max(0, index - 2), min(len(columns), index + 3))
            best = min(
                options, key=lambda candidate: costs[candidate] + abs(candidate - index)
            )
            previous.append(best)
            row.append(
                costs[best]
                + abs(best - index)
                + float(pixels[y * image.width + x])
                + abs(x - estimate) * 0.2
            )
        parents.append(previous)
        costs = row
    index = min(range(len(columns)), key=lambda candidate: costs[candidate])
    path = [columns[index]]
    for previous in reversed(parents):
        index = previous[index]
        path.append(columns[index])
    return list(reversed(path))


def extract() -> None:
    manifest: dict[str, object] = {"states": STATES, "size": 384, "avatars": {}}
    mappings: dict[str, object] = {}
    for animal, (folder, rows, levels) in SHEETS.items():
        sources = list((ROOT / "avatars" / folder).glob("download*.png"))
        if len(sources) != 1:
            raise ValueError(f"EXPECTED_ONE_SHEET:{folder}")
        source = Image.open(sources[0]).convert("RGBA")
        crops: list[tuple[Image.Image, tuple[int, int, int, int]]] = []
        top = 0
        for end, columns in rows:
            bottom = (
                source.height
                if end == 1000
                else valley(source, round(source.height * end / 1000), 1)
            )
            row = source.crop((0, top, source.width, bottom))
            estimates = [
                0,
                *(round(source.width * x / 1000) for x in columns),
                source.width,
            ]
            paths = [[0] * row.height]
            for index, estimate in enumerate(estimates[1:-1], 1):
                radius = min(
                    60,
                    (estimate - estimates[index - 1]) // 3,
                    (estimates[index + 1] - estimate) // 3,
                )
                paths.append(seam(row, estimate, radius))
            paths.append([source.width] * row.height)
            for left, right in zip(paths, paths[1:], strict=False):
                mask = Image.new("L", row.size)
                polygon = [(x, y) for y, x in enumerate(left)]
                polygon += [(x - 1, y) for y, x in reversed(list(enumerate(right)))]
                ImageDraw.Draw(mask).polygon(polygon, fill=255)
                image = row.copy()
                image.putalpha(ImageChops.multiply(image.getchannel("A"), mask))
                bounds = (min(left), top, max(right), bottom)
                crops.append(
                    (square(image.crop((bounds[0], 0, bounds[2], row.height))), bounds)
                )
            top = bottom
        public = ROOT / "frontend/public/assets/avatars" / animal
        public.mkdir(parents=True, exist_ok=True)
        mapping: list[dict[str, object]] = []
        for level, source_level in enumerate(levels, 1):
            for state_index, state in enumerate(STATES):
                index = (source_level - 1) * 3 + state_index
                if index >= len(crops):
                    raise ValueError(f"MISSING_SOURCE:{animal}:{index}")
                image, bounds = crops[index]
                filename = f"{animal}_{level:02}_{state}.png"
                image.save(ROOT / "avatars" / folder / filename, optimize=True)
                image.save(public / filename, optimize=True)
                mapping.append(
                    {"file": filename, "source_index": index + 1, "source_box": bounds}
                )
        mappings[animal] = {
            "source": str(sources[0].relative_to(ROOT)),
            "source_figures": len(crops),
            "level_mapping": levels,
            "crops": mapping,
        }
    manifest["avatars"] = mappings
    selection = Image.open(ROOT / "avatars/selection.png").convert("RGBA")
    # Retain the gold frame and interior; remove only the exterior.
    portraits = [
        ("dragon", 190, 141, 132),
        ("kitsune_fox", 465, 141, 134),
        ("griffin", 741, 142, 132),
        ("lion", 1015, 141, 133),
        ("mermaid", 181, 400, 137),
        ("panda", 459, 401, 136),
        ("pegasus", 736, 400, 136),
        ("phoenix", 1012, 400, 137),
        ("rhino", 315, 645, 139),
        ("sphinx_cat", 599, 643, 141),
        ("custom", 881, 643, 139),
    ]
    output = ROOT / "avatars/selection"
    public = ROOT / "frontend/public/assets/avatars/selection"
    output.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    for animal, x, y, radius in portraits:
        scale_x, scale_y = selection.width / 1208, selection.height / 805
        box = (
            round((x - radius) * scale_x),
            round((y - radius) * scale_y),
            round((x + radius) * scale_x),
            round((y + radius) * scale_y),
        )
        image = selection.crop(box)
        mask = Image.new("L", (image.width * 4, image.height * 4))
        ImageDraw.Draw(mask).ellipse((0, 0, mask.width - 1, mask.height - 1), fill=255)
        mask = mask.resize(image.size, Image.Resampling.LANCZOS)
        image.putalpha(ImageChops.multiply(image.getchannel("A"), mask))
        image.save(output / f"{animal}.png", optimize=True)
        image.save(public / f"{animal}.png", optimize=True)
    # The selection sheet has no unicorn; use its first neutral full-body drawing.
    unicorn = ROOT / "avatars/unicorn/unicorn_01_neutral.png"
    for directory in (output, public):
        (directory / "unicorn.png").write_bytes(unicorn.read_bytes())
    (ROOT / "avatars/crops.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    extract()
