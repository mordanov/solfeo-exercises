"""Generate only public note vocabulary, never exercise content."""

import argparse
import hashlib
import io
import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

from app.services.auth import ServiceError
from app.services.media import duration, run_media
from app.settings import Settings

VOCABULARY = (
    Path(__file__).resolve().parents[1] / "frontend/src/features/spoken/vocabulary.json"
)


class GenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Clip:
    language: str
    text: str
    path: str


# Native-accent hints per language, so every clip in a language sounds like one
# consistent native speaker instead of a foreign-accented reading.
ACCENT_HINTS = {
    "en": "Speak with a neutral, native English accent and standard pronunciation.",
    "ru": "Speak with a natural, native Russian accent and standard pronunciation.",
    "es": "Speak with a natural, neutral Spanish accent and standard pronunciation.",
}


def speech_instructions(language: str) -> str:
    return (
        "Speak only the supplied note name or accidental "
        f"in {language}. "
        f"{ACCENT_HINTS[language]} "
        "Use a clear, short, natural speaking voice. "
        "Do not sing, hum, "
        "add music, introductions, or other words."
    )


def vocabulary() -> list[Clip]:
    data: dict[str, dict[str, dict[str, str]]] = json.loads(VOCABULARY.read_text())
    return [
        Clip(language, text, f"{language}/{naming}/{name}.m4a")
        for language in ("en", "ru", "es")
        for naming in ("letters", "solfege")
        for name, text in {
            **data[language][naming],
            **data[language]["suffixes"],
        }.items()
    ]


def fingerprint(settings: Settings, clip: Clip) -> str:
    return hashlib.sha256(
        json.dumps(
            [
                settings.spoken_model,
                settings.spoken_voice,
                clip.language,
                clip.text,
                # The fingerprint does not track the instructions text, so the
                # committed clips stay valid after a wording-only change (for
                # example, the accent hint). Bump this tag only when a change
                # must force an explicit, separate-directory regeneration.
                "spoken-v1",
                settings.audio_bitrate_kbps,
            ],
            ensure_ascii=False,
        ).encode()
    ).hexdigest()


def validate_audio(path: Path, settings: Settings) -> None:
    if not 0 < path.stat().st_size <= settings.spoken_max_clip_bytes:
        raise GenerationError("SPOKEN_INVALID_AUDIO")
    duration(
        path,
        settings.model_copy(
            update={"audio_max_seconds": settings.spoken_max_clip_seconds}
        ),
    )
    data = json.loads(
        run_media(
            [
                settings.ffprobe_binary,
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-show_entries",
                "stream=codec_name:format=format_name",
                "-of",
                "json",
                str(path),
            ],
            settings,
        )
    )
    if data.get("streams") != [{"codec_name": "aac"}] or "mp4" not in data.get(
        "format", {}
    ).get("format_name", "").split(","):
        raise GenerationError("SPOKEN_INVALID_AUDIO")


def write_timings(settings: Settings) -> None:
    timings: dict[str, float] = {}
    for clip in vocabulary():
        data: dict[str, list[dict[str, str]]] = json.loads(
            run_media(
                [
                    settings.ffprobe_binary,
                    "-v",
                    "error",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-show_entries",
                    "stream=codec_name,profile,sample_rate,nb_frames",
                    "-of",
                    "json",
                    str(settings.spoken_output / clip.path),
                ],
                settings,
            )
        )
        try:
            stream = data["streams"][0]
            if (
                len(data["streams"]) != 1
                or stream["codec_name"] != "aac"
                or stream["profile"] != "LC"
            ):
                raise GenerationError("SPOKEN_INVALID_AUDIO")
            frames, rate = int(stream["nb_frames"]), int(stream["sample_rate"])
            if frames <= 0 or rate <= 0:
                raise GenerationError("SPOKEN_INVALID_AUDIO")
            # Full AAC frames include padding, unlike the container duration.
            seconds = math.ceil(frames * 1024 / rate * 1_000_000) / 1_000_000
            if not 0 < seconds <= settings.spoken_max_clip_seconds:
                raise GenerationError("SPOKEN_INVALID_AUDIO")
            timings["/solfege/" + clip.path] = seconds
        except (KeyError, ValueError, TypeError, IndexError):
            raise GenerationError("SPOKEN_INVALID_AUDIO") from None
    path = settings.spoken_output / "timings.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(timings, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def verify(settings: Settings, manifest_path: Path | None = None) -> None:
    root = settings.spoken_output
    try:
        manifest = json.loads((manifest_path or root / "manifest.json").read_text())
        if (
            manifest["version"] != 1
            or manifest["model"] != settings.spoken_model
            or manifest["voice"] != settings.spoken_voice
            or set(manifest["clips"]) != {clip.path for clip in vocabulary()}
        ):
            raise GenerationError("SPOKEN_ASSETS_CHANGED")
        checked: set[str] = set()
        for clip in vocabulary():
            entry = manifest["clips"][clip.path]
            path = root / clip.path
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if (
                entry["fingerprint"] != fingerprint(settings, clip)
                or entry["sha256"] != digest
                or json.loads(path.with_suffix(".json").read_text()) != entry
            ):
                raise GenerationError("SPOKEN_ASSETS_CHANGED")
            if digest not in checked:
                validate_audio(path, settings)
                checked.add(digest)
    except (OSError, ValueError, KeyError, TypeError, ServiceError):
        raise GenerationError("SPOKEN_ASSETS_INCOMPLETE") from None


def generate(settings: Settings, client: httpx.Client) -> None:
    if not settings.openai_api_key.get_secret_value():
        raise GenerationError("OPENAI_KEY_REQUIRED")
    root = settings.spoken_output
    root.mkdir(parents=True, exist_ok=True)
    entries: dict[str, dict[str, str]] = {}
    cache: dict[str, bytes] = {}
    for clip in vocabulary():
        signature = fingerprint(settings, clip)
        path = root / clip.path
        receipt = path.with_suffix(".json")
        if path.is_file() and receipt.is_file():
            previous: dict[str, str] = json.loads(receipt.read_text())
            if (
                isinstance(previous, dict)
                and previous.get("fingerprint") == signature
                and previous.get("sha256")
                == hashlib.sha256(path.read_bytes()).hexdigest()
            ):
                entries[clip.path] = previous
                cache[signature] = path.read_bytes()
                continue
            raise GenerationError("SPOKEN_ASSET_CONFIGURATION_CHANGED")
        if signature not in cache:
            try:
                with client.stream(
                    "POST",
                    "https://api.openai.com/v1/audio/speech",
                    headers={
                        "Authorization": "Bearer "
                        + settings.openai_api_key.get_secret_value()
                    },
                    json={
                        "model": settings.spoken_model,
                        "voice": settings.spoken_voice,
                        "input": clip.text,
                        "response_format": "wav",
                        "instructions": speech_instructions(clip.language),
                    },
                    timeout=settings.spoken_timeout_seconds,
                ) as response:
                    if response.status_code != 200:
                        raise GenerationError(f"TTS_HTTP_{response.status_code}")
                    buffer = io.BytesIO()
                    for chunk in response.iter_bytes(chunk_size=65536):
                        buffer.write(chunk)
                        if buffer.tell() > settings.spoken_max_clip_bytes:
                            raise GenerationError("TTS_RESPONSE_TOO_LARGE")
                with TemporaryDirectory(prefix=".speech-", dir=root) as temporary:
                    source, output = (
                        Path(temporary) / "input.wav",
                        Path(temporary) / "clip.m4a",
                    )
                    source.write_bytes(buffer.getvalue())
                    if not buffer.getvalue().startswith(b"RIFF"):
                        raise GenerationError("TTS_INVALID_AUDIO")
                    run_media(
                        [
                            settings.ffmpeg_binary,
                            "-v",
                            "error",
                            "-nostdin",
                            "-protocol_whitelist",
                            "file,pipe",
                            "-i",
                            str(source),
                            "-af",
                            "silenceremove=start_periods=1:start_duration=0.01:start_threshold=-50dB,"
                            "areverse,silenceremove=start_periods=1:start_duration=0.01:start_threshold=-50dB,areverse",
                            "-ac",
                            "1",
                            "-c:a",
                            "aac",
                            "-b:a",
                            f"{settings.audio_bitrate_kbps}k",
                            "-movflags",
                            "+faststart",
                            str(output),
                        ],
                        settings,
                    )
                    validate_audio(output, settings)
                    cache[signature] = output.read_bytes()
            except httpx.HTTPError:
                raise GenerationError("TTS_NETWORK_ERROR") from None
        content = cache[signature]
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(".tmp")
        temporary_path.write_bytes(content)
        temporary_path.replace(path)
        entry = {
            "fingerprint": signature,
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        temporary_receipt = receipt.with_suffix(".json.tmp")
        temporary_receipt.write_text(json.dumps(entry, indent=2) + "\n")
        temporary_receipt.replace(receipt)
        entries[clip.path] = entry
    manifest = root / "manifest.tmp"
    manifest.write_text(
        json.dumps(
            {
                "version": 1,
                "model": settings.spoken_model,
                "voice": settings.spoken_voice,
                "clips": entries,
            },
            indent=2,
        )
        + "\n"
    )
    verify(settings, manifest)
    write_timings(settings)
    manifest.replace(root / "manifest.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-timings", action="store_true")
    arguments = parser.parse_args()
    settings = Settings()
    logging.basicConfig(level=logging.WARNING)
    try:
        if arguments.write_timings:
            verify(settings)
            write_timings(settings)
        elif arguments.check:
            verify(settings)
        else:
            with httpx.Client(follow_redirects=False) as client:
                generate(settings, client)
    except (GenerationError, ServiceError) as error:
        raise SystemExit(str(error)) from None
    except (OSError, ValueError):
        raise SystemExit("SPOKEN_ASSET_IO_ERROR") from None
    print("SPOKEN_ASSETS_VERIFIED")


if __name__ == "__main__":
    main()
