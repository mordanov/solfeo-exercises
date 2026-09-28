import subprocess

from app import Settings


def prepare_audio(settings: Settings) -> None:
    if not settings.source_audio.is_file():
        raise FileNotFoundError(settings.source_audio)
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    target = settings.media_dir / "sample.m4a"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-n",
            "-i",
            str(settings.source_audio),
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            settings.audio_bitrate,
            "-movflags",
            "+faststart",
            str(target),
        ],
        check=True,
        timeout=settings.ffmpeg_timeout_seconds,
    )
    metadata = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(target),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=settings.ffmpeg_timeout_seconds,
    )
    (settings.output_dir / "audio-metadata.json").write_text(metadata.stdout)


if __name__ == "__main__":
    prepare_audio(Settings())
