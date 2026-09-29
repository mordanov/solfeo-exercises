import json
import logging
import math
import subprocess
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO, Literal
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from app.models import MediaFile
from app.services.auth import ServiceError
from app.settings import Settings

logger = logging.getLogger(__name__)
Kind = Literal["image", "audio"]
IMAGES = {
    "image/png": ("PNG", ".png"),
    "image/jpeg": ("JPEG", ".jpg"),
    "image/webp": ("WEBP", ".webp"),
}
# Container signatures can identify audio-only files as video or application data.
AUDIO_CONTAINERS = {
    "application/ogg",
    "video/ogg",
    "video/mp4",
    "video/webm",
    "video/x-matroska",
    "application/vnd.ms-asf",
}


def run_media(command: list[str], settings: Settings) -> bytes:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            timeout=settings.media_timeout_seconds,
            shell=False,
        ).stdout
    except subprocess.TimeoutExpired as error:
        logger.warning("MEDIA_TIMEOUT")
        raise ServiceError("MEDIA_TIMEOUT", 422) from error
    except subprocess.CalledProcessError as error:
        logger.warning("INVALID_MEDIA")
        raise ServiceError("INVALID_MEDIA", 422) from error
    except OSError as error:
        logger.error("MEDIA_PROCESSOR_UNAVAILABLE")
        raise ServiceError("MEDIA_PROCESSOR_UNAVAILABLE", 503) from error


def duration(path: Path, settings: Settings) -> float:
    result = run_media(
        [
            settings.ffprobe_binary,
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type:format=duration",
            "-of",
            "json",
            str(path),
        ],
        settings,
    )
    try:
        data = json.loads(result)
        if not data.get("streams"):
            raise ValueError("NO_AUDIO_STREAM")
        seconds = float(data["format"]["duration"])
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("INVALID_DURATION")
    except (ValueError, KeyError, TypeError) as error:
        raise ServiceError("INVALID_MEDIA", 422) from error
    if seconds > settings.audio_max_seconds:
        raise ServiceError("AUDIO_TOO_LONG", 422)
    return seconds


def prepare_media(source: BinaryIO, kind: Kind, settings: Settings) -> MediaFile:
    root = settings.media_root
    limit = settings.image_max_bytes if kind == "image" else settings.audio_max_bytes
    try:
        root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".upload-", dir=root) as temporary:
            incoming = Path(temporary) / "input"
            size = 0
            with incoming.open("wb") as target:
                while chunk := source.read(65536):
                    size += len(chunk)
                    if size > limit:
                        raise ServiceError("FILE_TOO_LARGE", 413)
                    target.write(chunk)
            if not size:
                raise ServiceError("EMPTY_FILE", 422)
            mime = (
                run_media(
                    [settings.file_binary, "--brief", "--mime-type", str(incoming)],
                    settings,
                )
                .decode("ascii")
                .strip()
            )
            seconds: float | None = None
            if kind == "image":
                if mime not in IMAGES:
                    raise ServiceError("UNSUPPORTED_MEDIA", 415)
                expected, extension = IMAGES[mime]
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("error", Image.DecompressionBombWarning)
                        with Image.open(incoming) as image:
                            if (
                                image.format != expected
                                or image.width * image.height
                                > settings.image_max_pixels
                            ):
                                raise ServiceError("INVALID_IMAGE", 422)
                            image.verify()
                        with Image.open(incoming) as image:
                            image.load()
                except (
                    UnidentifiedImageError,
                    OSError,
                    SyntaxError,
                    ValueError,
                    Image.DecompressionBombError,
                    Image.DecompressionBombWarning,
                ) as error:
                    raise ServiceError("INVALID_IMAGE", 422) from error
                output = incoming
            else:
                if not mime.startswith("audio/") and mime not in AUDIO_CONTAINERS:
                    raise ServiceError("UNSUPPORTED_MEDIA", 415)
                duration(incoming, settings)
                output = Path(temporary) / "output.m4a"
                run_media(
                    [
                        settings.ffmpeg_binary,
                        "-nostdin",
                        "-v",
                        "error",
                        "-xerror",
                        "-protocol_whitelist",
                        "file,pipe",
                        "-i",
                        str(incoming),
                        "-map",
                        "0:a:0",
                        "-vn",
                        "-map_metadata",
                        "-1",
                        "-map_chapters",
                        "-1",
                        "-c:a",
                        "aac",
                        "-b:a",
                        f"{settings.audio_bitrate_kbps}k",
                        "-threads",
                        "1",
                        "-t",
                        str(settings.audio_max_seconds + 1),
                        "-movflags",
                        "+faststart",
                        str(output),
                    ],
                    settings,
                )
                seconds = duration(output, settings)
                mime, extension = "audio/mp4", ".m4a"
                size = output.stat().st_size
                if size > settings.audio_max_bytes:
                    raise ServiceError("FILE_TOO_LARGE", 413)
            identifier = str(uuid4())
            filename = identifier + extension
            output.chmod(0o644)
            output.replace(root / filename)
            return MediaFile(
                id=identifier,
                filename=filename,
                mime_type=mime,
                size_bytes=size,
                duration_seconds=seconds,
            )
    except OSError as error:
        logger.error("MEDIA_STORAGE_ERROR")
        raise ServiceError("MEDIA_STORAGE_ERROR", 503) from error
