import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from bot import TEXTS, Bot, BotError, Settings, Telegram, Update

TOKEN = "123456:TEST_TOKEN_NOT_A_REAL_TELEGRAM_SECRET"


def config(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "token": TOKEN,
        "allowed_user_ids": [42],
        "data_dir": tmp_path,
        "min_free_bytes": 0,
    }
    values.update(overrides)
    return Settings.model_validate(values)


def update(kind: str = "voice", sender: int = 42, chat_type: str = "private") -> Update:
    return Update.model_validate(
        {
            "update_id": 10,
            "message": {
                "message_id": 20,
                "from": {"id": sender},
                "chat": {"id": sender, "type": chat_type},
                kind: {"file_id": "telegram-file", "file_size": 12},
            },
        }
    )


def test_requires_token_and_nonempty_numeric_allowlist(tmp_path: Path) -> None:
    cases: list[dict[str, object]] = [
        {"token": ""},
        {"allowed_user_ids": []},
        {"allowed_user_ids": [True]},
        {"allowed_user_ids": [-1]},
    ]
    for overrides in cases:
        with pytest.raises(ValidationError):
            config(tmp_path, **overrides)


def test_config_errors_do_not_reveal_token(tmp_path: Path) -> None:
    with pytest.raises(ValidationError) as error:
        config(tmp_path, token="private-invalid-token")
    assert "private-invalid-token" not in str(error.value)


@pytest.mark.parametrize("kind", ["audio", "voice", "document"])
def test_downloads_authorized_attachments_and_replies_after_save(
    tmp_path: Path, kind: str
) -> None:
    events: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/getFile"):
            events.append("getFile")
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {
                        "file_path": "voice/file.oga",
                        "file_size": 12,
                    },
                },
            )
        if "/file/" in request.url.path:
            events.append("download")
            return httpx.Response(200, content=b"test content")
        assert request.url.path.endswith("/sendMessage")
        assert (tmp_path / "10.m4a").read_bytes() == b"converted"
        events.append("reply")
        return httpx.Response(200, json={"ok": True, "result": {}})

    def convert(source: Path, target: Path) -> None:
        assert source.read_bytes() == b"test content"
        assert not target.exists()
        target.write_bytes(b"converted")
        events.append("convert")

    settings = config(tmp_path)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        bot = Bot(settings, Telegram(settings, client), convert)
        bot.process(update(kind))
    assert events == ["getFile", "download", "convert", "reply"]
    assert not list(tmp_path.glob(".incoming-*"))


@pytest.mark.parametrize(
    "sender,chat_type", [(43, "private"), (42, "group"), (42, "channel")]
)
def test_denies_unauthorized_sources_without_api_calls(
    tmp_path: Path, sender: int, chat_type: str
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("Unauthorized input must not call Telegram")

    settings = config(tmp_path)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        Bot(settings, Telegram(settings, client)).process(
            update(sender=sender, chat_type=chat_type)
        )
    assert not list(tmp_path.glob("*.m4a"))


def test_rejects_known_oversized_file_without_downloading(tmp_path: Path) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path.rsplit("/", 1)[-1])
        assert b"FILE_TOO_LARGE" in request.content
        return httpx.Response(200, json={"ok": True, "result": {}})

    settings = config(tmp_path, max_file_bytes=5)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        Bot(settings, Telegram(settings, client)).process(update())
    assert calls == ["sendMessage"]


def test_limits_actual_download_and_removes_partial_file(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/getFile"):
            return httpx.Response(
                200, json={"ok": True, "result": {"file_path": "voice/file.oga"}}
            )
        if "/file/" in request.url.path:
            return httpx.Response(200, stream=httpx.ByteStream(b"x" * 30))
        assert b"FILE_TOO_LARGE" in request.content
        return httpx.Response(200, json={"ok": True, "result": {}})

    settings = config(tmp_path, max_file_bytes=20)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        Bot(settings, Telegram(settings, client)).process(update())
    assert not list(tmp_path.glob("*.m4a"))
    assert not list(tmp_path.glob(".incoming-*"))


def test_rejects_unsafe_telegram_file_paths(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"ok": True, "result": {"file_path": "../private"}}
        )

    settings = config(tmp_path)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(BotError, match="INVALID_RESPONSE"):
            Telegram(settings, client).download("file-id", tmp_path / "download")
    assert not (tmp_path / "download").exists()


def test_does_not_advance_offset_when_reply_fails_and_does_not_resave(
    tmp_path: Path,
) -> None:
    settings = config(tmp_path)
    (tmp_path / "10.m4a").write_bytes(b"already stored")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/getUpdates"):
            payload = json.loads(request.content)
            assert payload["offset"] == 0
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": [
                        update().model_dump(by_alias=True),
                    ],
                },
            )
        assert request.url.path.endswith("/sendMessage")
        return httpx.Response(500, text=TOKEN)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        bot = Bot(settings, Telegram(settings, client))
        with pytest.raises(BotError) as error:
            bot.poll_once()
    assert TOKEN not in str(error.value)
    assert not (tmp_path / "offset.json").exists()
    assert (tmp_path / "10.m4a").read_bytes() == b"already stored"


def test_persists_offset_only_after_processing(tmp_path: Path) -> None:
    settings = config(tmp_path)
    (tmp_path / "10.m4a").write_bytes(b"stored")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/getUpdates"):
            return httpx.Response(
                200, json={"ok": True, "result": [update().model_dump(by_alias=True)]}
            )
        assert request.url.path.endswith("/sendMessage")
        assert not (tmp_path / "offset.json").exists()
        return httpx.Response(200, json={"ok": True, "result": {}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        bot = Bot(settings, Telegram(settings, client))
        bot.poll_once()
        assert Bot(settings, Telegram(settings, client)).offset == 11


def test_startup_checks_identity_and_refuses_existing_webhook(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/getMe"):
            return httpx.Response(
                200, json={"ok": True, "result": {"id": 123456, "is_bot": True}}
            )
        assert request.url.path.endswith("/getWebhookInfo")
        return httpx.Response(
            200,
            json={"ok": True, "result": {"url": "https://existing.example/webhook"}},
        )

    settings = config(tmp_path)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(BotError, match="WEBHOOK_CONFIGURED"):
            Telegram(settings, client).verify()


def test_rate_limit_preserves_retry_after_without_exposing_api_body(
    tmp_path: Path,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={
                "ok": False,
                "description": TOKEN,
                "parameters": {"retry_after": 60},
            },
        )

    settings = config(tmp_path)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(BotError) as error:
            Telegram(settings, client).updates(0)
    assert error.value.retryable
    assert error.value.retry_after == 60
    assert TOKEN not in str(error.value)


@pytest.mark.parametrize("limit", [1, 10])
def test_storage_capacity_rejects_without_downloading(
    tmp_path: Path, limit: int
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/sendMessage")
        assert b"STORAGE_FULL" in request.content
        return httpx.Response(200, json={"ok": True, "result": {}})

    settings = config(tmp_path, storage_limit_bytes=limit)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        Bot(settings, Telegram(settings, client)).process(update())


def test_invalid_media_does_not_leave_files_or_claim_success(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/getFile"):
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {
                        "file_path": "documents/file.opus",
                        "file_size": 12,
                    },
                },
            )
        if "/file/" in request.url.path:
            return httpx.Response(200, content=b"test content")
        assert b"NOT_AUDIO" in request.content
        return httpx.Response(200, json={"ok": True, "result": {}})

    def convert(source: Path, target: Path) -> None:
        raise BotError("NOT_AUDIO")

    settings = config(tmp_path)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        Bot(settings, Telegram(settings, client), convert).process(update())
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "text,expected", [("/start", "help"), ("https://example.com/file", "NO_AUDIO")]
)
def test_text_and_links_are_not_downloaded(
    tmp_path: Path, text: str, expected: str
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/sendMessage")
        message = json.loads(request.content)["text"]
        assert (
            TEXTS["ru"]["help"] in message
            if expected == "help"
            else expected in message
        )
        return httpx.Response(200, json={"ok": True, "result": {}})

    message = Update.model_validate(
        {
            "update_id": 10,
            "message": {
                "from": {"id": 42},
                "chat": {"id": 42, "type": "private"},
                "text": text,
            },
        }
    )
    settings = config(tmp_path)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        Bot(settings, Telegram(settings, client)).process(message)


def test_bot_texts_have_identical_nonempty_translation_keys() -> None:
    for values in TEXTS.values():
        assert values.keys() == TEXTS["en"].keys()
        assert all(values.values())


def test_does_not_follow_file_redirects(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.telegram.org"
        if request.url.path.endswith("/getFile"):
            return httpx.Response(
                200, json={"ok": True, "result": {"file_path": "voice/file.oga"}}
            )
        return httpx.Response(
            302, headers={"Location": "https://untrusted.example/file"}
        )

    settings = config(tmp_path)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(BotError, match="DOWNLOAD_FAILED"):
            Telegram(settings, client).download("file-id", tmp_path / "input")


def test_refuses_corrupt_offset_instead_of_replaying_messages(tmp_path: Path) -> None:
    (tmp_path / "offset.json").write_text("broken")
    settings = config(tmp_path)
    with httpx.Client() as client:
        with pytest.raises(BotError, match="INVALID_STATE"):
            Bot(settings, Telegram(settings, client))


def test_rejects_incomplete_download(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/getFile"):
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {
                        "file_path": "voice/file.oga",
                        "file_size": 20,
                    },
                },
            )
        return httpx.Response(200, content=b"short")

    settings = config(tmp_path)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(BotError, match="DOWNLOAD_INCOMPLETE"):
            Telegram(settings, client).download("file-id", tmp_path / "input")
