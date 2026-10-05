import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from app.game.services.achievements import ACHIEVEMENT_CODES

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "frontend/public/assets/prizes"
SOURCE = ROOT / "trophies.png"


def assert_same_pixels(actual_path: Path, expected_path: Path) -> None:
    with Image.open(actual_path) as actual, Image.open(expected_path) as expected:
        assert actual.format == expected.format == "PNG"
        assert actual.mode == expected.mode == "RGBA"
        assert actual.size == expected.size
        same_pixels = actual.tobytes() == expected.tobytes()
        assert same_pixels, f"Pixels differ in {actual_path.name}"


def test_same_pixels_allow_different_png_compression(tmp_path: Path) -> None:
    original = ASSETS / "first_round.png"
    reencoded = tmp_path / original.name
    with Image.open(original) as image:
        image.save(reencoded, compress_level=0)
    assert reencoded.read_bytes() != original.read_bytes()
    assert_same_pixels(reencoded, original)


def test_different_pixels_are_rejected(tmp_path: Path) -> None:
    original = ASSETS / "first_round.png"
    changed = tmp_path / original.name
    with Image.open(original) as image:
        image.putpixel((128, 128), (1, 2, 3, 255))
        image.save(changed)
    with pytest.raises(AssertionError, match="Pixels differ"):
        assert_same_pixels(changed, original)


def test_all_twenty_prizes_have_distinct_transparent_artwork() -> None:
    assert {path.stem for path in ASSETS.glob("*.png")} == set(ACHIEVEMENT_CODES)
    hashes: set[str] = set()
    for code in ACHIEVEMENT_CODES:
        path = ASSETS / f"{code}.png"
        with Image.open(path) as image:
            hashes.add(hashlib.sha256(image.tobytes()).hexdigest())
            assert image.format == "PNG"
            assert image.mode == "RGBA"
            assert image.size == (256, 256)
            alpha = image.getchannel("A")
            assert alpha.getextrema() == (0, 255)
            assert all(
                alpha.getpixel(point) == 0
                for point in ((0, 0), (255, 0), (0, 255), (255, 255), (128, 0))
            )
            bounds = alpha.getbbox()
            assert bounds is not None
            left, top, right, bottom = bounds
            assert left >= 8 and top >= 8 and right <= 248 and bottom <= 248
            assert max(right - left, bottom - top) == 240
            assert abs((left + right) / 2 - 128) <= 1
            assert abs((top + bottom) / 2 - 128) <= 1
    assert len(hashes) == 20


def test_prize_extraction_reproduces_assets_without_changing_the_source(
    tmp_path: Path,
) -> None:
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_prize_assets.py"),
            "--output",
            str(tmp_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=30,
    )
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before
    for code in ACHIEVEMENT_CODES:
        assert_same_pixels(tmp_path / f"{code}.png", ASSETS / f"{code}.png")


def test_invalid_sheet_does_not_write_partial_assets(tmp_path: Path) -> None:
    source = tmp_path / "incomplete.png"
    with Image.open(SOURCE) as image:
        image.paste(
            (0, 0, 0, 0),
            (image.width * 4 // 5, image.height * 3 // 4, image.width, image.height),
        )
        image.save(source)
    output = tmp_path / "assets"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_prize_assets.py"),
            "--source",
            str(source),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "Expected 20 separate badges" in result.stderr
    assert not output.exists()
