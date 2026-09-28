import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import SecretStr

from app import Settings
from prepare import prepare_audio


def test_convert_to_aac_with_faststart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "input.opus"
    source.write_bytes(b"fixture")
    settings = Settings(
        password=SecretStr("synthetic-test-credential-not-for-use"),
        source_audio=source,
        media_dir=tmp_path / "media",
        output_dir=tmp_path / "output",
    )
    process = Mock(
        side_effect=[
            subprocess.CompletedProcess([], 0),
            subprocess.CompletedProcess([], 0, stdout='{"streams": []}'),
        ]
    )
    monkeypatch.setattr(subprocess, "run", process)
    prepare_audio(settings)
    command = process.call_args_list[0].args[0]
    assert command[command.index("-c:a") + 1] == "aac"
    assert command[command.index("-movflags") + 1] == "+faststart"
    assert "-n" in command
    assert command[-1].endswith("sample.m4a")
    assert process.call_args_list[0].kwargs["timeout"] == 60
    assert (settings.output_dir / "audio-metadata.json").exists()


def test_missing_source_does_not_invoke_ffmpeg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = Mock()
    monkeypatch.setattr(subprocess, "run", process)
    settings = Settings(
        password=SecretStr("synthetic-test-credential-not-for-use"),
        source_audio=tmp_path / "missing.opus",
    )
    with pytest.raises(FileNotFoundError):
        prepare_audio(settings)
    process.assert_not_called()
