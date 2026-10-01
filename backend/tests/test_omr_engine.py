import subprocess
import zipfile
from pathlib import Path
from typing import BinaryIO
from unittest.mock import patch

import pytest
from PIL import Image
from pydantic import SecretStr
from test_omr import SCORE

from app.services.auth import ServiceError
from app.services.omr import validate_musicxml
from app.services.omr_engine import AudiverisEngine, read_export
from app.settings import Settings


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


@pytest.mark.parametrize("detect_movements", [False, True])
def test_system_indentation_does_not_split_one_exercise(
    tmp_path: Path,
    detect_movements: bool,
) -> None:
    image = tmp_path / "original.png"
    Image.new("RGB", (30, 30), "white").save(image)
    original = image.read_bytes()
    commands: list[list[str]] = []

    def run(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        check: bool,
        timeout: float,
        stdout: BinaryIO,
        stderr: int,
    ) -> subprocess.CompletedProcess[bytes]:
        commands.append(command)
        output = Path(command[command.index("-output") + 1])
        (output / "score.musicxml").write_bytes(SCORE)
        assert "DATABASE_PASSWORD" not in env
        assert "OPENAI_API_KEY" not in env
        return subprocess.CompletedProcess(command, 0)

    settings = Settings(
        _env_file=None,
        database_password=SecretStr("unused"),
        omr_detect_movements=detect_movements,
    )
    with patch("app.services.omr_engine.subprocess.run", side_effect=run):
        assert b"<step>C</step>" in AudiverisEngine(settings).recognize(image)
    assert (
        "org.audiveris.omr.sheet.ProcessingSwitches.indentations="
        + str(detect_movements).lower()
        in commands[0]
    )
    assert image.read_bytes() == original


@pytest.mark.parametrize(
    ("second_error", "expected"),
    [
        (None, None),
        ("No system found", "OMR_NO_STAFF"),
        ("Java failed", "OMR_ENGINE_FAILED"),
        ("deadline", "OMR_TIMEOUT"),
    ],
)
def test_faint_staff_retry_is_bounded_and_uses_fresh_output(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    second_error: str | None,
    expected: str | None,
) -> None:
    image = tmp_path / "original.png"
    Image.new("RGB", (30, 30), "white").save(image)
    commands: list[list[str]] = []
    outputs: list[Path] = []
    timeouts: list[float] = []

    def run(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        check: bool,
        timeout: float,
        stdout: BinaryIO,
        stderr: int,
    ) -> subprocess.CompletedProcess[bytes]:
        commands.append(command)
        output = Path(command[command.index("-output") + 1])
        assert not list(output.iterdir())
        outputs.append(output)
        timeouts.append(timeout)
        error = "No system found" if len(commands) == 1 else second_error
        if error:
            (output / "stale.musicxml").write_bytes(SCORE)
            stdout.write(f"private-engine-output: {error}".encode())
            raise subprocess.CalledProcessError(1, command)
        (output / "score.musicxml").write_bytes(SCORE)
        return subprocess.CompletedProcess(command, 0)

    settings = Settings(
        _env_file=None,
        database_password=SecretStr("unused"),
        omr_timeout_seconds=100,
    )
    with (
        patch("app.services.omr_engine.subprocess.run", side_effect=run),
        patch(
            "app.services.omr_engine.time.monotonic",
            side_effect=[0, 1, 101 if second_error == "deadline" else 4],
        ),
    ):
        if expected:
            with pytest.raises(ServiceError, match=expected):
                AudiverisEngine(settings).recognize(image)
        else:
            assert b"<step>C</step>" in AudiverisEngine(settings).recognize(image)
    if second_error == "deadline":
        assert len(commands) == 1
        assert timeouts == [99]
    else:
        assert len(commands) == 2
        assert outputs[0] != outputs[1]
        assert timeouts == [99, 96]
        assert "org.audiveris.omr.image.AdaptiveDescriptor.meanCoeff=0.9" in commands[1]
    assert not any("meanCoeff" in argument for argument in commands[0])
    assert "OMR_FAINT_STAFF_RETRY" in caplog.text
    assert "private-engine-output" not in caplog.text


@pytest.mark.parametrize("failure", ["engine", "timeout", "no_export", "invalid"])
def test_unrelated_failures_do_not_trigger_faint_staff_retry(
    tmp_path: Path,
    failure: str,
) -> None:
    image = tmp_path / "original.png"
    Image.new("RGB", (30, 30), "white").save(image)

    def run(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        check: bool,
        timeout: float,
        stdout: BinaryIO,
        stderr: int,
    ) -> subprocess.CompletedProcess[bytes]:
        if failure == "engine":
            raise subprocess.CalledProcessError(1, command)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, timeout)
        if failure == "invalid":
            output = Path(command[command.index("-output") + 1])
            (output / "score.musicxml").write_bytes(b"invalid")
        return subprocess.CompletedProcess(command, 0)

    codes = {
        "engine": "OMR_ENGINE_FAILED",
        "timeout": "OMR_TIMEOUT",
        "no_export": "OMR_NO_SCORE",
        "invalid": "OMR_INVALID_SCORE",
    }
    settings = Settings(_env_file=None, database_password=SecretStr("unused"))
    with patch("app.services.omr_engine.subprocess.run", side_effect=run) as process:
        with pytest.raises(ServiceError, match=codes[failure]):
            AudiverisEngine(settings).recognize(image)
    assert process.call_count == 1
