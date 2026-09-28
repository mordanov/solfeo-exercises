import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from omr import Settings, classify, create_command, main, run_sample, samples


@pytest.mark.parametrize(
    ("expected", "substitutions", "omissions", "extras", "label", "percentage"),
    [
        (100, 0, 0, 0, "fully", 100),
        (100, 10, 5, 5, "fully", 80),
        (100, 21, 0, 0, "partly", 79),
        (100, 20, 20, 10, "partly", 50),
        (100, 51, 0, 0, "failed", 49),
        (10, 0, 0, 20, "failed", 0),
        (10001, 2001, 0, 0, "partly", 79.99200079992001),
    ],
)
def test_classification(
    expected: int,
    substitutions: int,
    omissions: int,
    extras: int,
    label: str,
    percentage: float,
) -> None:
    result = classify(expected, substitutions, omissions, extras)
    assert result.label == label
    assert result.percentage == pytest.approx(percentage)


@pytest.mark.parametrize(
    ("expected", "substitutions", "omissions", "extras"),
    [
        (0, 0, 0, 0),
        (-1, 0, 0, 0),
        (1, -1, 0, 0),
        (1, 0, -1, 0),
        (1, 0, 0, -1),
        (2, 2, 1, 0),
    ],
)
def test_invalid_counts_raise(
    expected: int, substitutions: int, omissions: int, extras: int
) -> None:
    with pytest.raises(ValueError):
        classify(expected, substitutions, omissions, extras)


def test_unusable_musicxml_is_not_a_measured_zero() -> None:
    result = classify(20, 0, 0, 0, usable=False)
    assert result.label == "failed"
    assert result.percentage is None


def test_settings_from_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("OMR_TIMEOUT_SECONDS=31\nOMR_CPUS=1\n")
    settings = Settings()
    assert settings.timeout_seconds == 31
    assert settings.cpus == 1


@pytest.mark.parametrize("value", [0, -1])
def test_invalid_timeout(value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(timeout_seconds=value)


def test_only_selected_samples_in_numeric_order(tmp_path: Path) -> None:
    for n in range(1, 12):
        (tmp_path / f"ejercicio_{n}.jpeg").write_bytes(b"sample")
    result = samples(tmp_path)
    assert len(result) == 10
    assert result[-1].name == "ejercicio_10.jpeg"
    assert all(path.name != "ejercicio_11.jpeg" for path in result)


def test_missing_sample_fails_before_run(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="ejercicio_1.jpeg"):
        samples(tmp_path)


def test_command_is_offline_and_mounts_only_one_read_only_sample(
    tmp_path: Path,
) -> None:
    image = tmp_path / "a space.jpeg"
    output = tmp_path / "output"
    command = create_command(Settings(), "sha256:123", image, output)
    assert command[:2] == ["docker", "create"]
    assert command[command.index("--network") + 1] == "none"
    assert f"type=bind,source={image},target=/input/sample.jpeg,readonly" in command
    assert f"type=bind,source={output},target=/output" in command
    assert "sha256:123" in command
    assert command[-1] == "/input/sample.jpeg"
    assert "-batch" in command and "-export" in command and "-transcribe" in command


def test_runner_records_export_without_claiming_accuracy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = tmp_path / "image.jpeg"
    image.write_bytes(b"sample")
    output = tmp_path / "output"

    def execute(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if command[1] == "start":
            (output / "sample.mxl").write_bytes(b"export")
        stdout = "container-id\n" if command[1] == "create" else "0\n"
        return subprocess.CompletedProcess(command, 0, stdout=stdout)

    monkeypatch.setattr(subprocess, "run", execute)
    result = run_sample(Settings(), "sha256:123", image, output)
    assert result["outcome"] == "exported"
    assert result["exports"] == ["sample.mxl"]
    assert "percentage" not in result
    assert (output / "run.json").exists()


@pytest.mark.parametrize("exit_code", [0, 1])
def test_no_export_or_process_failure_is_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int
) -> None:
    image = tmp_path / "image.jpeg"
    image.write_bytes(b"sample")
    process = Mock(
        side_effect=[
            subprocess.CompletedProcess([], 0, stdout="container-id\n"),
            subprocess.CompletedProcess([], exit_code),
            subprocess.CompletedProcess([], 0, stdout=str(exit_code)),
            subprocess.CompletedProcess([], 0),
        ]
    )
    monkeypatch.setattr(subprocess, "run", process)
    result = run_sample(Settings(), "sha256:123", image, tmp_path / "output")
    assert result["outcome"] == "failed"
    assert result["exit_code"] == exit_code
    assert process.call_args_list[-1].args[0] == [
        "docker",
        "rm",
        "--force",
        "container-id",
    ]


def test_timeout_removes_only_its_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = tmp_path / "image.jpeg"
    image.write_bytes(b"sample")
    process = Mock(
        side_effect=[
            subprocess.CompletedProcess([], 0, stdout="container-id\n"),
            subprocess.TimeoutExpired(["docker", "start"], 1),
            subprocess.CompletedProcess([], 0),
        ]
    )
    monkeypatch.setattr(subprocess, "run", process)
    output = tmp_path / "output"
    result = run_sample(Settings(), "sha256:123", image, output)
    assert result["outcome"] == "timed_out"
    assert (output / "run.json").exists()
    assert process.call_args_list[-1].args[0] == [
        "docker",
        "rm",
        "--force",
        "container-id",
    ]


def test_existing_output_is_never_reused(tmp_path: Path) -> None:
    image = tmp_path / "image.jpeg"
    image.write_bytes(b"sample")
    with pytest.raises(FileExistsError):
        run_sample(Settings(), "sha256:123", image, tmp_path)


def test_main_records_runtime_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    Path("samples").mkdir()
    for n in range(1, 11):
        Path(f"samples/ejercicio_{n}.jpeg").write_bytes(b"sample")
    process = Mock(
        side_effect=[
            subprocess.CompletedProcess([], 0, stdout='[{"Id": "sha256:123"}]'),
            subprocess.CompletedProcess([], 0, stdout="Docker version"),
            subprocess.CompletedProcess([], 0, stdout="Audiveris 5.11.0"),
        ]
    )
    monkeypatch.setattr(subprocess, "run", process)
    monkeypatch.setattr("omr.run_sample", Mock(return_value={"outcome": "exported"}))
    assert main() == 0
    version_file = next(Path("output").glob("*/audiveris-version.txt"))
    assert version_file.read_text() == "Audiveris 5.11.0"
    assert "--network" in process.call_args.args[0]
    assert "sha256:123" in process.call_args.args[0]
