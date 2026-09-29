import re
import time
from tempfile import TemporaryFile
from typing import BinaryIO

import httpx
from pydantic import BaseModel, Field, JsonValue, ValidationError

from app.services.auth import ServiceError
from app.settings import Settings


class ApiResponse(BaseModel):
    ok: bool
    result: JsonValue = None
    error_code: int = 0
    parameters: dict[str, int] = Field(default_factory=dict)


class ApiFile(BaseModel):
    file_path: str
    file_size: int | None = Field(default=None, ge=0)


class BotIdentity(BaseModel):
    id: int = Field(gt=0)
    username: str


class TelegramApi:
    def __init__(self, settings: Settings, client: httpx.Client) -> None:
        self.settings, self.client = settings, client
        self.base = (
            "https://api.telegram.org/bot" + settings.telegram_token.get_secret_value()
        )

    def call(self, method: str, data: dict[str, JsonValue]) -> JsonValue:
        try:
            response = self.client.post(
                self.base + "/" + method,
                json=data,
                follow_redirects=False,
                timeout=self.settings.telegram_http_seconds
                + self.settings.telegram_poll_seconds,
            )
            result = ApiResponse.model_validate_json(response.content)
        except (httpx.HTTPError, ValidationError):
            raise ServiceError("TELEGRAM_UNAVAILABLE", 503) from None
        if not response.is_success or not result.ok:
            retry = result.parameters.get("retry_after")
            raise ServiceError(
                "TELEGRAM_RATE_LIMITED"
                if result.error_code == 429
                else "TELEGRAM_REQUEST_FAILED",
                503 if response.status_code >= 500 or result.error_code == 429 else 422,
                retry_after=retry,
            )
        return result.result

    def verify(self) -> int:
        try:
            identity = BotIdentity.model_validate(self.call("getMe", {}))
        except ValidationError:
            raise ServiceError("TELEGRAM_INVALID_RESPONSE", 503) from None
        if identity.username != self.settings.telegram_bot_username:
            raise ServiceError("TELEGRAM_BOT_CHANGED", 503)
        webhook = self.call("getWebhookInfo", {})
        if not isinstance(webhook, dict) or webhook.get("url") != "":
            raise ServiceError("TELEGRAM_WEBHOOK_CONFLICT", 503)
        return identity.id

    def updates(self, offset: int, wait: int) -> list[JsonValue]:
        result = self.call(
            "getUpdates",
            {
                "offset": offset,
                "timeout": wait,
                "allowed_updates": ["message"],
                "limit": 20,
            },
        )
        if not isinstance(result, list):
            raise ServiceError("TELEGRAM_INVALID_RESPONSE", 503)
        return result

    def reply(self, chat_id: int, content: str) -> None:
        self.call("sendMessage", {"chat_id": chat_id, "text": content})

    def download(self, file_id: str) -> BinaryIO:
        try:
            info = ApiFile.model_validate(self.call("getFile", {"file_id": file_id}))
        except ValidationError:
            raise ServiceError("TELEGRAM_INVALID_RESPONSE", 503) from None
        if not re.fullmatch(r"[A-Za-z0-9_./-]+", info.file_path) or any(
            part in {"", ".", ".."} for part in info.file_path.split("/")
        ):
            raise ServiceError("TELEGRAM_INVALID_RESPONSE", 422)
        limit = min(
            self.settings.telegram_max_file_bytes, self.settings.audio_max_bytes
        )
        if info.file_size is not None and info.file_size > limit:
            raise ServiceError("FILE_TOO_LARGE", 413)
        target = TemporaryFile()
        try:
            with self.client.stream(
                "GET",
                "https://api.telegram.org/file/bot"
                + self.settings.telegram_token.get_secret_value()
                + "/"
                + info.file_path,
                follow_redirects=False,
                timeout=self.settings.telegram_http_seconds,
            ) as response:
                if not response.is_success:
                    raise ServiceError(
                        "TELEGRAM_DOWNLOAD_FAILED",
                        503 if response.status_code >= 500 else 422,
                    )
                size, started = 0, time.monotonic()
                for chunk in response.iter_bytes(65536):
                    size += len(chunk)
                    if size > limit:
                        raise ServiceError("FILE_TOO_LARGE", 413)
                    if (
                        time.monotonic() - started
                        > self.settings.telegram_download_seconds
                    ):
                        raise ServiceError("TELEGRAM_DOWNLOAD_FAILED", 503)
                    target.write(chunk)
                if not size or (info.file_size is not None and size != info.file_size):
                    raise ServiceError("TELEGRAM_DOWNLOAD_FAILED", 503)
            target.seek(0)
            return target
        except httpx.HTTPError:
            target.close()
            raise ServiceError("TELEGRAM_DOWNLOAD_FAILED", 503) from None
        except BaseException:
            target.close()
            raise
