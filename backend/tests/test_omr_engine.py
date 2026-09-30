import zipfile
from pathlib import Path

import pytest
from test_omr import SCORE

from app.services.auth import ServiceError
from app.services.omr import validate_musicxml
from app.services.omr_engine import read_export


def test_plain_and_compressed_exports(tmp_path: Path) -> None:
    output = tmp_path / "score.musicxml"
    output.write_bytes(SCORE)
    assert b"<step>C</step>" in read_export(tmp_path, 10000)
    output.unlink()
    with zipfile.ZipFile(tmp_path / "score.mxl", "w") as archive:
        archive.writestr(
            "META-INF/container.xml",
            """<container>
        <rootfiles><rootfile full-path="score.xml"/></rootfiles></container>""",
        )
        archive.writestr("score.xml", SCORE)
    assert b"<step>C</step>" in read_export(tmp_path, 10000)


@pytest.mark.parametrize("path", ["../score.xml", "/score.xml", "score.xml"])
def test_archive_traversal_and_size_limit(tmp_path: Path, path: str) -> None:
    with zipfile.ZipFile(tmp_path / "score.mxl", "w") as archive:
        archive.writestr(
            "META-INF/container.xml",
            f"""<container>
        <rootfiles><rootfile full-path="{path}"/></rootfiles></container>""",
        )
        archive.writestr(path, SCORE + b" " * 20000)
    with pytest.raises(ServiceError):
        read_export(tmp_path, 1000)


def test_no_score_and_ambiguous_export(tmp_path: Path) -> None:
    with pytest.raises(ServiceError, match="OMR_NO_SCORE"):
        read_export(tmp_path, 10000)
    for name in ("one", "two"):
        (tmp_path / f"{name}.musicxml").write_bytes(SCORE)
    with pytest.raises(ServiceError, match="OMR_MULTIPLE_SCORES"):
        read_export(tmp_path, 10000)


@pytest.mark.parametrize("name", ["scale", "rhythm", "accidentals"])
def test_authored_score_fixtures_are_supported(name: str) -> None:
    path = Path(__file__).parent / "fixtures" / "omr" / f"{name}.musicxml"
    assert validate_musicxml(path.read_bytes(), 10000).startswith(b"<?xml")
