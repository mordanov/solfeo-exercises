import base64
import hashlib
import json
from pathlib import Path


def test_reduced_piano_contains_only_four_layers_of_fourteen_pitches() -> None:
    directory = Path(__file__).parents[2] / "frontend/public/assets/piano"
    encoded = (directory / "salamander-c4-b5.json").read_bytes()
    asset = json.loads(encoded)
    expected = {
        f"{name}{octave}-v{layer}"
        for name in "CDEFGAB"
        for octave in (4, 5)
        for layer in (4, 8, 12, 16)
    }
    assert set(asset) == expected
    assert len(encoded) <= 1_500_000
    for sample in asset.values():
        assert sample.startswith("data:audio/mp4;base64,")
        assert b"ftyp" in base64.b64decode(sample.split(",", 1)[1], validate=True)[:40]
    provenance = json.loads((directory / "provenance.json").read_text())
    assert provenance["asset_sha256"] == hashlib.sha256(encoded).hexdigest()
    assert provenance["asset_bytes"] == len(encoded)
    assert provenance["license"] == "CC BY 3.0"
    assert len(provenance["source_sha256"]) == 36
    assert (directory / "LICENSE.txt").stat().st_size > 1000
