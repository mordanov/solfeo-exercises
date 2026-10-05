"""Build a wordless hourglass badge; the UI supplies a translated caption."""

from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    scale = 4
    size = 384 * scale
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def box(values: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        left, top, right, bottom = values
        return left * scale, top * scale, right * scale, bottom * scale

    draw.ellipse(
        box((8, 8, 376, 376)), fill="#FFD851", outline="#B87719", width=8 * scale
    )
    draw.ellipse(
        box((26, 26, 358, 358)), fill="#50246D", outline="#FFF1A5", width=3 * scale
    )
    draw.polygon(
        [
            (x * scale, y * scale)
            for x, y in (
                (116, 95),
                (268, 95),
                (258, 145),
                (212, 191),
                (258, 237),
                (268, 287),
                (116, 287),
                (126, 237),
                (172, 191),
                (126, 145),
            )
        ],
        fill="#AFA0D5",
        outline="#FFF2C3",
        width=5 * scale,
    )
    draw.polygon(
        [(x * scale, y * scale) for x, y in ((137, 129), (247, 129), (192, 181))],
        fill="#FFDA54",
    )
    draw.polygon(
        [(x * scale, y * scale) for x, y in ((136, 273), (248, 273), (192, 224))],
        fill="#FFDA54",
    )
    draw.line(
        (192 * scale, 182 * scale, 192 * scale, 237 * scale),
        fill="#FFD851",
        width=5 * scale,
    )
    for y in (78, 283):
        draw.rounded_rectangle(
            box((100, y, 284, y + 24)),
            radius=10 * scale,
            fill="#FFD851",
            outline="#A96719",
            width=4 * scale,
        )
    for x, y in ((67, 130), (308, 242), (289, 105), (90, 285)):
        draw.polygon(
            [
                (x * scale, (y - 11) * scale),
                ((x + 4) * scale, (y - 4) * scale),
                ((x + 11) * scale, y * scale),
                ((x + 4) * scale, (y + 4) * scale),
                (x * scale, (y + 11) * scale),
                ((x - 4) * scale, (y + 4) * scale),
                ((x - 11) * scale, y * scale),
                ((x - 4) * scale, (y - 4) * scale),
            ],
            fill="#FFF3A1",
        )
    path = Path("frontend/public/assets/avatars/selection/under_moderation.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.resize((384, 384), Image.Resampling.LANCZOS).save(path, optimize=True)


if __name__ == "__main__":
    main()
