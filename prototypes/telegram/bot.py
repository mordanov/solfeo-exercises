import argparse
import fcntl
import json
import logging
import math
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Literal

import httpx
from pydantic import (
    BaseModel,
    Field,
    JsonValue,
    SecretStr,
    TypeAdapter,
    ValidationError,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("solfeo.telegram")
PositiveId = Annotated[int, Field(gt=0, strict=True)]
Offset = Annotated[int, Field(ge=0, strict=True)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SOLFEO_TELEGRAM_PROTOTYPE_",
        extra="forbid",
        hide_input_in_errors=True,
    )
    token: SecretStr
    allowed_user_ids: list[PositiveId] = Field(min_length=1)
    language: Literal["ru", "en", "es"] = "ru"
    data_dir: Path = Path("data")
    max_file_bytes: int = Field(default=20_000_000, gt=0, le=20_000_000)
    storage_limit_bytes: int = Field(default=200_000_000, gt=0)
    min_free_bytes: int = Field(default=100_000_000, ge=0)
    max_audio_seconds: int = Field(default=900, gt=0)
    poll_seconds: int = Field(default=25, ge=1, le=50)
    http_timeout_seconds: int = Field(default=15, gt=0)
    download_timeout_seconds: int = Field(default=90, gt=0)
    media_timeout_seconds: int = Field(default=120, gt=0)
    retry_seconds: int = Field(default=5, gt=0)
    health_max_age_seconds: int = Field(default=600, gt=0)
    file_binary: str = "/usr/bin/file"
    ffprobe_binary: str = "/usr/bin/ffprobe"
    ffmpeg_binary: str = "/usr/bin/ffmpeg"
    audio_bitrate: str = Field(default="128k", pattern=r"^[1-9][0-9]*k$")

    @field_validator("token")
    @classmethod
    def valid_token(cls, value: SecretStr) -> SecretStr:
        if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{20,}", value.get_secret_value()):
            raise ValueError("A dedicated BotFather token is required")
        return value


class BotError(Exception):
    def __init__(
        self, code: str, *, retryable: bool = False, retry_after: int | None = None
    ) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.retry_after = retry_after


class Attachment(BaseModel):
    file_id: str = Field(min_length=1)
    file_size: int | None = Field(default=None, ge=0)


class User(BaseModel):
    id: PositiveId


class Chat(BaseModel):
    id: int
    type: str


class Message(BaseModel):
    sender: User | None = Field(default=None, alias="from")
    chat: Chat
    text: str | None = None
    audio: Attachment | None = None
    voice: Attachment | None = None
    document: Attachment | None = None


class Update(BaseModel):
    update_id: Offset
    message: Message | None = None


class ApiFile(BaseModel):
    file_path: str
    file_size: int | None = Field(default=None, ge=0)


class RetryParameters(BaseModel):
    retry_after: int | None = Field(default=None, gt=0)


class Envelope(BaseModel):
    ok: bool
    result: JsonValue = None
    error_code: int | None = None
    parameters: RetryParameters | None = None


class Identity(BaseModel):
    id: PositiveId
    is_bot: bool


class Webhook(BaseModel):
    url: str


class Telegram:
    def __init__(self, settings: Settings, client: httpx.Client) -> None:
        self.settings = settings
        self.client = client

    def call(
        self, method: str, payload: dict[str, JsonValue] | None = None
    ) -> JsonValue:
        token = self.settings.token.get_secret_value()
        try:
            response = self.client.post(
                f"https://api.telegram.org/bot{token}/{method}",
                json=payload or {},
                timeout=self.settings.http_timeout_seconds
                + (self.settings.poll_seconds if method == "getUpdates" else 0),
                follow_redirects=False,
            )
        except httpx.HTTPError:
            raise BotError("TELEGRAM_UNAVAILABLE", retryable=True) from None
        if response.status_code == 401:
            raise BotError("TOKEN_REJECTED")
        if response.status_code == 409:
            raise BotError("POLL_CONFLICT")
        if response.status_code >= 500:
            raise BotError("TELEGRAM_UNAVAILABLE", retryable=True)
        try:
            envelope = Envelope.model_validate_json(response.content)
        except ValidationError:
            raise BotError("INVALID_RESPONSE", retryable=True) from None
        if not response.is_success or not envelope.ok:
            retry = envelope.parameters.retry_after if envelope.parameters else None
            raise BotError(
                "RATE_LIMITED" if response.status_code == 429 else "TELEGRAM_REJECTED",
                retryable=response.status_code == 429,
                retry_after=retry,
            )
        return envelope.result

    def verify(self) -> int:
        try:
            identity = Identity.model_validate(self.call("getMe"))
            webhook = Webhook.model_validate(self.call("getWebhookInfo"))
        except ValidationError:
            raise BotError("INVALID_RESPONSE") from None
        if not identity.is_bot:
            raise BotError("INVALID_BOT")
        if webhook.url:
            raise BotError("WEBHOOK_CONFIGURED")
        return identity.id

    def updates(self, offset: int) -> list[Update]:
        result = self.call(
            "getUpdates",
            {
                "offset": offset,
                "timeout": self.settings.poll_seconds,
                "allowed_updates": ["message"],
            },
        )
        try:
            return TypeAdapter(list[Update]).validate_python(result)
        except ValidationError:
            raise BotError("INVALID_RESPONSE", retryable=True) from None

    def reply(self, chat_id: int, text: str) -> None:
        self.call("sendMessage", {"chat_id": chat_id, "text": text})

    def download(self, file_id: str, target: Path) -> None:
        try:
            info = ApiFile.model_validate(self.call("getFile", {"file_id": file_id}))
        except ValidationError:
            raise BotError("INVALID_RESPONSE") from None
        if not re.fullmatch(r"[A-Za-z0-9_./-]+", info.file_path) or any(
            part in {"", ".", ".."} for part in info.file_path.split("/")
        ):
            raise BotError("INVALID_RESPONSE")
        limit = self.settings.max_file_bytes
        if info.file_size is not None and info.file_size > limit:
            raise BotError("FILE_TOO_LARGE")
        token = self.settings.token.get_secret_value()
        started = time.monotonic()
        try:
            with self.client.stream(
                "GET",
                f"https://api.telegram.org/file/bot{token}/{info.file_path}",
                timeout=self.settings.http_timeout_seconds,
                follow_redirects=False,
            ) as response:
                if not response.is_success:
                    raise BotError(
                        "DOWNLOAD_FAILED", retryable=response.status_code >= 500
                    )
                length = response.headers.get("content-length")
                if length is not None:
                    try:
                        declared = int(length)
                    except ValueError:
                        raise BotError("INVALID_RESPONSE") from None
                    if declared < 0:
                        raise BotError("INVALID_RESPONSE")
                    if declared > limit:
                        raise BotError("FILE_TOO_LARGE")
                size = 0
                with target.open("xb") as output:
                    target.chmod(0o600)
                    for chunk in response.iter_bytes(chunk_size=65536):
                        if (
                            time.monotonic() - started
                            > self.settings.download_timeout_seconds
                        ):
                            raise BotError("DOWNLOAD_TIMEOUT", retryable=True)
                        size += len(chunk)
                        if size > limit:
                            raise BotError("FILE_TOO_LARGE")
                        output.write(chunk)
                if size == 0:
                    raise BotError("EMPTY_FILE")
                if info.file_size is not None and size != info.file_size:
                    raise BotError("DOWNLOAD_INCOMPLETE", retryable=True)
        except httpx.HTTPError:
            raise BotError("DOWNLOAD_FAILED", retryable=True) from None


class Disposition(BaseModel):
    attached_pic: int = 0


class Stream(BaseModel):
    codec_type: str
    codec_name: str = ""
    disposition: Disposition = Field(default_factory=Disposition)


class Format(BaseModel):
    duration: float = Field(gt=0, allow_inf_nan=False)


class Probe(BaseModel):
    streams: list[Stream]
    format: Format


def media_command(command: list[str], settings: Settings) -> str:
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=settings.media_timeout_seconds,
            env={},
        )
    except subprocess.TimeoutExpired:
        raise BotError("MEDIA_TIMEOUT") from None
    except subprocess.CalledProcessError:
        raise BotError("INVALID_AUDIO") from None
    except OSError:
        raise BotError("MEDIA_TOOL_UNAVAILABLE") from None
    return result.stdout


def probe(path: Path, settings: Settings) -> Probe:
    output = media_command(
        [
            settings.ffprobe_binary,
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        settings,
    )
    try:
        return Probe.model_validate_json(output)
    except ValidationError:
        raise BotError("INVALID_AUDIO") from None


def convert_audio(source: Path, target: Path, settings: Settings) -> None:
    mime = media_command(
        [settings.file_binary, "--brief", "--mime-type", "--", str(source)], settings
    ).strip()
    if not mime.startswith("audio/") and mime not in {
        "application/ogg",
        "video/mp4",
        "video/webm",
        "video/x-matroska",
    }:
        raise BotError("NOT_AUDIO")
    original = probe(source, settings)
    if not any(stream.codec_type == "audio" for stream in original.streams):
        raise BotError("NOT_AUDIO")
    if any(
        stream.codec_type == "video" and not stream.disposition.attached_pic
        for stream in original.streams
    ):
        raise BotError("NOT_AUDIO")
    if original.format.duration > settings.max_audio_seconds:
        raise BotError("AUDIO_TOO_LONG")
    media_command(
        [
            settings.ffmpeg_binary,
            "-nostdin",
            "-v",
            "error",
            "-n",
            "-protocol_whitelist",
            "file,pipe",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-vn",
            "-map_metadata",
            "-1",
            "-c:a",
            "aac",
            "-b:a",
            settings.audio_bitrate,
            "-t",
            str(settings.max_audio_seconds + 1),
            "-fs",
            str(settings.max_file_bytes + 65536),
            "-movflags",
            "+faststart",
            str(target),
        ],
        settings,
    )
    if not 0 < target.stat().st_size <= settings.max_file_bytes:
        raise BotError("FILE_TOO_LARGE")
    converted = probe(target, settings)
    if converted.format.duration > settings.max_audio_seconds:
        raise BotError("AUDIO_TOO_LONG")
    if not any(stream.codec_name == "aac" for stream in converted.streams):
        raise BotError("INVALID_AUDIO")
    if abs(converted.format.duration - original.format.duration) > 1:
        raise BotError("INCOMPLETE_AUDIO")


TEXTS = {
    "ru": {
        "received": (
            "Аудио сохранено: {name}; {size} байт. Это прототип, упражнение не создано."
        ),
        "error": (
            "Файл не принят. Код: {code}. Отправьте одно аудиовложение до {limit} байт."
        ),
        "help": (
            "Отправьте или перешлите одно аудиовложение, "
            "голосовое сообщение или аудиофайл. Ссылки не загружаются."
        ),
    },
    "en": {
        "received": (
            "Audio saved: {name}; {size} bytes. "
            "This is a prototype; no exercise was created."
        ),
        "error": (
            "File not accepted. Code: {code}. "
            "Send one audio attachment up to {limit} bytes."
        ),
        "help": (
            "Send or forward one audio attachment, voice message, or audio file. "
            "Links are not downloaded."
        ),
    },
    "es": {
        "received": (
            "Audio guardado: {name}; {size} bytes. "
            "Es un prototipo; no se ha creado un ejercicio."
        ),
        "error": (
            "Archivo no aceptado. Código: {code}. "
            "Envía un archivo de audio de hasta {limit} bytes."
        ),
        "help": (
            "Envía o reenvía un archivo de audio o un mensaje de voz. "
            "No se descargan enlaces."
        ),
    },
}


def durable_replace(source: Path, target: Path) -> None:
    os.replace(source, target)
    directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def atomic_number(path: Path, value: int | float) -> None:
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            json.dump(value, output)
            output.flush()
            os.fsync(output.fileno())
            durable_replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


class Bot:
    def __init__(
        self,
        settings: Settings,
        telegram: Telegram,
        converter: Callable[[Path, Path], None] | None = None,
    ) -> None:
        self.settings = settings
        self.telegram = telegram
        self.converter = converter or (
            lambda source, target: convert_audio(source, target, settings)
        )
        self.data = settings.data_dir
        self.data.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            self.offset = TypeAdapter(Offset).validate_json(
                (self.data / "offset.json").read_bytes()
            )
        except FileNotFoundError:
            self.offset = 0
        except ValidationError:
            raise BotError("INVALID_STATE") from None

    def store(self, update: Update, attachment: Attachment) -> Path:
        target = self.data / f"{update.update_id}.m4a"
        if target.is_file() and not target.is_symlink():
            if target.stat().st_size == 0:
                raise BotError("INVALID_STATE")
            return target
        limit = self.settings.max_file_bytes
        if attachment.file_size is not None and attachment.file_size > limit:
            raise BotError("FILE_TOO_LARGE")
        used = sum(path.stat().st_size for path in self.data.glob("*.m4a"))
        if used + limit > self.settings.storage_limit_bytes:
            raise BotError("STORAGE_FULL")
        if shutil.disk_usage(self.data).free < self.settings.min_free_bytes + 2 * limit:
            raise BotError("STORAGE_FULL")
        with tempfile.TemporaryDirectory(
            prefix=".incoming-", dir=self.data
        ) as directory:
            source = Path(directory) / "input"
            converted = Path(directory) / "audio.m4a"
            self.telegram.download(attachment.file_id, source)
            self.converter(source, converted)
            converted.chmod(0o600)
            with converted.open("rb") as output:
                os.fsync(output.fileno())
            durable_replace(converted, target)
        return target

    def process(self, update: Update) -> None:
        message = update.message
        if message is None:
            logger.info("IGNORED_UPDATE")
            return
        if (
            message.sender is None
            or message.chat.type != "private"
            or message.sender.id not in self.settings.allowed_user_ids
            or message.chat.id != message.sender.id
        ):
            logger.warning("ACCESS_DENIED")
            return
        text = TEXTS[self.settings.language]
        if message.text in {"/start", "/help"}:
            self.telegram.reply(message.chat.id, text["help"])
            return
        attachments = [
            value
            for value in (message.audio, message.voice, message.document)
            if value is not None
        ]
        try:
            if len(attachments) != 1:
                raise BotError("NO_AUDIO" if not attachments else "MULTIPLE_FILES")
            target = self.store(update, attachments[0])
        except BotError as error:
            logger.warning("%s", error.code)
            if error.retryable:
                raise
            self.telegram.reply(
                message.chat.id,
                text["error"].format(
                    code=error.code, limit=self.settings.max_file_bytes
                ),
            )
            return
        self.telegram.reply(
            message.chat.id,
            text["received"].format(name=target.name, size=target.stat().st_size),
        )
        logger.info("RECEIVED")

    def poll_once(self, stop: threading.Event | None = None) -> None:
        updates = self.telegram.updates(self.offset)
        atomic_number(self.data / "heartbeat.json", time.time())
        for update in updates:
            if stop is not None and stop.is_set():
                return
            if update.update_id < self.offset:
                continue
            self.process(update)
            atomic_number(self.data / "offset.json", update.update_id + 1)
            self.offset = update.update_id + 1
            atomic_number(self.data / "heartbeat.json", time.time())

    def run(self, stop: threading.Event) -> None:
        (self.data / "heartbeat.json").unlink(missing_ok=True)
        identity = self.telegram.verify()
        identity_file = self.data / "bot-id.json"
        if identity_file.exists():
            try:
                previous = TypeAdapter(PositiveId).validate_json(
                    identity_file.read_bytes()
                )
            except ValidationError:
                raise BotError("INVALID_STATE") from None
            if previous != identity:
                raise BotError("BOT_ID_MISMATCH")
        else:
            atomic_number(identity_file, identity)
        logger.info("BOT_VERIFIED")
        while not stop.is_set():
            try:
                self.poll_once(stop)
            except BotError as error:
                logger.error("%s", error.code)
                if not error.retryable:
                    raise
                stop.wait(error.retry_after or self.settings.retry_seconds)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    try:
        settings = Settings()
        if args.healthcheck:
            try:
                timestamp = TypeAdapter(float).validate_json(
                    (settings.data_dir / "heartbeat.json").read_bytes()
                )
            except (OSError, ValidationError):
                return 1
            age = time.time() - timestamp
            return (
                0
                if math.isfinite(age) and 0 <= age <= settings.health_max_age_seconds
                else 1
            )
        stop = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
        signal.signal(signal.SIGINT, lambda *_: stop.set())
        settings.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (settings.data_dir / "worker.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with httpx.Client(trust_env=False) as client:
                Bot(settings, Telegram(settings, client)).run(stop)
    except ValidationError:
        logger.error("INVALID_CONFIGURATION")
        return 1
    except BotError as error:
        logger.error("%s", error.code)
        return 1
    except OSError:
        logger.error("STORAGE_OR_LOCK_FAILED")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
