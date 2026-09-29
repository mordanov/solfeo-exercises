import shutil
import subprocess
from pathlib import Path

import pytest

from bot import BotError, Settings, convert_audio, probe


def media_settings(tmp_path: Path) -> Settings:
    tools = {name: shutil.which(name) for name in ("ffmpeg", "ffprobe", "file")}
    assert all(tools.values()), "Media tests require ffmpeg, ffprobe, and file"
    return Settings.model_validate(
        {
            "token": "123456:TEST_TOKEN_NOT_A_REAL_TELEGRAM_SECRET",
            "allowed_user_ids": [42],
            "data_dir": tmp_path,
            "ffmpeg_binary": tools["ffmpeg"],
            "ffprobe_binary": tools["ffprobe"],
            "file_binary": tools["file"],
        }
    )


def test_detects_and_converts_real_opus_without_trusting_extension(
    tmp_path: Path,
) -> None:
    settings = media_settings(tmp_path)
    source = tmp_path / "sample.opus"
    subprocess.run(
        [
            settings.ffmpeg_binary,
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.25",
            "-c:a",
            "libopus",
            str(source),
        ],
        check=True,
        timeout=30,
        capture_output=True,
    )
    source = source.rename(tmp_path / "input")
    target = tmp_path / "result.m4a"
    convert_audio(source, target, settings)
    assert target.stat().st_size > 0
    assert probe(target, settings).streams[0].codec_name == "aac"


def test_rejects_text_disguised_as_audio(tmp_path: Path) -> None:
    settings = media_settings(tmp_path)
    source = tmp_path / "fake.opus"
    source.write_text("not an audio file")
    with pytest.raises(BotError, match="NOT_AUDIO"):
        convert_audio(source, tmp_path / "result.m4a", settings)
    assert not (tmp_path / "result.m4a").exists()


def test_rejects_audio_over_duration_limit(tmp_path: Path) -> None:
    settings = media_settings(tmp_path)
    settings.max_audio_seconds = 1
    source = tmp_path / "sample.wav"
    subprocess.run(
        [
            settings.ffmpeg_binary,
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            str(source),
        ],
        check=True,
        timeout=30,
        capture_output=True,
    )
    with pytest.raises(BotError, match="AUDIO_TOO_LONG"):
        convert_audio(source, tmp_path / "result.m4a", settings)
