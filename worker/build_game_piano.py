"""Build the licensed, reduced Salamander piano for Guess the Note."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

REVISION = "3382bf9496bba2486f5ab0de55a264d1dfc38404"
SOURCE = (
    f"https://raw.githubusercontent.com/sfzinstruments/SalamanderGrandPiano/{REVISION}"
)
LAYERS = (4, 8, 12, 16)
ROOTS = {
    60: "C4",
    63: "D#4",
    66: "F#4",
    69: "A4",
    72: "C5",
    75: "D#5",
    78: "F#5",
    81: "A5",
    84: "C6",
}
TUNING_CENTS = {60: -6, 63: -3, 66: 0, 69: -4, 72: -8, 75: -8, 78: -5, 81: -7, 84: -8}
PITCHES = [
    (f"{name}{octave}", 12 * (octave + 1) + offset)
    for octave in (4, 5)
    for name, offset in zip("CDEFGAB", (0, 2, 4, 5, 7, 9, 11), strict=True)
]


def download(source_dir: Path, filename: str) -> tuple[str, str]:
    path = source_dir / filename
    if not path.exists():
        with urlopen(f"{SOURCE}/Samples/{quote(filename)}", timeout=60) as response:
            path.write_bytes(response.read())
    return filename, hashlib.sha256(path.read_bytes()).hexdigest()


def build(source_dir: Path, public_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)
    names = [f"{root}v{layer}.flac" for root in ROOTS.values() for layer in LAYERS]
    with ThreadPoolExecutor(max_workers=4) as executor:
        hashes = dict(
            executor.map(lambda filename: download(source_dir, filename), names)
        )
    asset: dict[str, str] = {}
    for note, midi in PITCHES:
        root_midi = min(ROOTS, key=lambda root: abs(root - midi))
        for layer in LAYERS:
            filename = f"{ROOTS[root_midi]}v{layer}.flac"
            output = source_dir / f"{note}-v{layer}.m4a"
            rate = 48000 * 2 ** (
                (midi - root_midi + TUNING_CENTS[root_midi] / 100) / 12
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(source_dir / filename),
                    "-af",
                    f"asetrate={rate:.8f},aresample=32000,atrim=duration=2.5,"
                    "afade=t=out:st=2.3:d=0.2",
                    "-ac",
                    "1",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "48k",
                    "-movflags",
                    "+faststart",
                    str(output),
                ],
                check=True,
                timeout=60,
            )
            asset[f"{note}-v{layer}"] = "data:audio/mp4;base64," + base64.b64encode(
                output.read_bytes()
            ).decode("ascii")
    encoded = (json.dumps(asset, indent=2) + "\n").encode("ascii")
    if len(encoded) > 1_500_000:
        raise ValueError("The reduced piano exceeds the 1.5 MB budget")
    (public_dir / "salamander-c4-b5.json").write_bytes(encoded)
    provenance = {
        "author": "Alexander Holm",
        "source": "Salamander Grand Piano V3",
        "source_url": f"https://github.com/sfzinstruments/SalamanderGrandPiano/tree/{REVISION}",
        "revision": REVISION,
        "license": "CC BY 3.0",
        "license_url": "https://creativecommons.org/licenses/by/3.0/",
        "changes": "C4–B5 natural notes; 4 velocity layers; pitch resampling; "
        "2.5 s samples; fade; mono 32 kHz AAC at 48 kbit/s.",
        "layers": LAYERS,
        "tuning": "Upstream Data/tune_ret.txt corrections",
        "tuning_cents": TUNING_CENTS,
        "notes": [name for name, _ in PITCHES],
        "asset_bytes": len(encoded),
        "asset_sha256": hashlib.sha256(encoded).hexdigest(),
        "source_sha256": hashes,
    }
    (public_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    with urlopen(f"{SOURCE}/LICENSE", timeout=60) as response:
        attribution = (
            "Salamander Grand Piano V3\nAuthor: Alexander Holm\n"
            f"Source: {provenance['source_url']}\n"
            f"Changes: {provenance['changes']}\n"
            "License: Creative Commons Attribution 3.0 Unported\n\n"
        )
        (public_dir / "LICENSE.txt").write_bytes(
            attribution.encode("utf-8") + response.read()
        )
    print(f"Built {len(asset)} samples in 1 asset ({len(encoded)} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--public-dir", type=Path, required=True)
    args = parser.parse_args()
    build(args.source_dir, args.public_dir)


if __name__ == "__main__":
    main()
