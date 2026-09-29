from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import NAMESPACE_URL, uuid5

import httpx
import pytest
from sqlalchemy import func, select
from test_auth import anyio_backend, client, create_user, database, login
from test_exercises import auth_settings, opus, png, settings

from app.database import Database
from app.models import (
    Exercise,
    MediaFile,
    TelegramLink,
    TelegramLinkCode,
    TelegramState,
    TelegramUpdate,
    User,
)
from app.services import telegram
from app.services.auth import ServiceError
from app.services.media import prepare_media
from app.services.telegram_api import TelegramApi
from app.settings import Settings
from worker.telegram import cycle

__all__ = [
    "anyio_backend",
    "client",
    "database",
    "settings",
    "auth_settings",
    "opus",
    "png",
]
pytestmark = pytest.mark.anyio


def message(update: int, sender: int, **fields: object) -> dict[str, object]:
    return {
        "update_id": update,
        "message": {
            "from": {"id": sender},
            "chat": {"id": sender, "type": "private"},
            **fields,
        },
    }


async def link(
    client: httpx.AsyncClient, database: Database, sender: int = 12345
) -> str:
    response = await client.post("/api/telegram/link")
    assert response.status_code == 200, response.text
    code = response.json()["code"]
    with database.session() as session:
        telegram.receive(session, message(1, sender, text="/start " + code))
    return str(code)


async def test_link_permissions_single_use_expiry_and_unlink(
    client: httpx.AsyncClient, database: Database, settings: Settings
) -> None:
    assert (await client.get("/api/telegram")).status_code == 401
    await login(client)
    token = client.headers.pop("X-CSRF-Token")
    assert (await client.post("/api/telegram/link")).status_code == 403
    client.headers["X-CSRF-Token"] = token
    assert (
        await client.post("/api/telegram/link", headers={"Origin": "https://other"})
    ).status_code == 403
    await create_user(client)
    code = await link(client, database)
    assert (await client.get("/api/telegram")).json()["linked"]
    with database.session() as session:
        telegram.receive(session, message(2, 67890, text="/start " + code))
        assert session.scalar(select(func.count()).select_from(TelegramLink)) == 1
    assert (await client.delete("/api/telegram/link")).status_code == 200
    assert not (await client.get("/api/telegram")).json()["linked"]
    await login(client, "student")
    for method, path in (
        ("GET", "/api/telegram"),
        ("POST", "/api/telegram/link"),
        ("GET", "/api/telegram/imports"),
        ("DELETE", "/api/telegram/link"),
        ("GET", "/api/telegram/imports/2/audio"),
        ("POST", "/api/telegram/imports/2/apply"),
        ("POST", "/api/telegram/imports/2/retry"),
    ):
        assert (
            await client.request(
                method,
                path,
                json={"title": "Denied"} if path.endswith("/apply") else None,
            )
        ).status_code == 403


async def test_expired_codes_and_account_reset_revoke_link(
    client: httpx.AsyncClient, database: Database
) -> None:
    await login(client)
    user_id = await create_user(client, "linked-manager", "manager")
    await login(client, "linked-manager")
    code = (await client.post("/api/telegram/link")).json()["code"]
    with database.session() as session:
        saved = session.get(TelegramLinkCode, user_id)
        assert saved and saved.token_hash != code
        saved.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
        telegram.receive(session, message(10, 12345, text="/start " + code))
        assert session.get(TelegramLink, user_id) is None
    await link(client, database)
    await login(client)
    response = await client.post(
        f"/api/users/{user_id}/password",
        json={
            "password": "changed-long-password",
            "must_change_password": True,
        },
    )
    assert response.status_code == 200
    with database.session() as session:
        assert session.get(TelegramLink, user_id) is None
        assert session.get(TelegramLinkCode, user_id) is None


async def test_real_conversion_retry_reuses_media_and_preserves_existing_image(
    client: httpx.AsyncClient,
    database: Database,
    settings: Settings,
    opus: bytes,
    png: bytes,
) -> None:
    await login(client)
    await link(client, database)
    exercise = (
        await client.post(
            "/api/exercises",
            data={"title": "Existing"},
            files={"image": ("image.png", png)},
        )
    ).json()
    with database.session() as session:
        telegram.receive(session, message(2, 12345, voice={"file_id": "voice"}))

        def unavailable(_: str) -> BytesIO:
            raise ServiceError("TELEGRAM_UNAVAILABLE", 503)

        telegram.process_one(session, settings, unavailable)
        row = session.get(TelegramUpdate, 2)
        assert row and row.status == "pending" and row.attempts == 1
        row.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
    identifier = uuid5(NAMESPACE_URL, "solfeo:telegram:2")
    prepare_media(BytesIO(opus), "audio", settings, identifier)
    with database.session() as session:
        telegram.process_one(session, settings, lambda _: BytesIO(opus))
        telegram.process_one(
            session, settings, lambda _: pytest.fail("duplicate conversion")
        )
    assert len(list(settings.media_root.glob("*.m4a"))) == 1
    response = await client.post(
        "/api/telegram/imports/2/apply",
        json={
            "exercise_id": exercise["id"],
            "title": "Updated",
            "description": "Imported",
        },
    )
    assert response.status_code == 200
    result = (await client.get(f"/api/exercises/{exercise['id']}")).json()
    assert result["image"]["id"] == exercise["image"]["id"]
    assert result["audio"]["id"] == str(identifier)


async def test_worker_restart_duplicate_update_and_real_api_transport(
    client: httpx.AsyncClient, database: Database, settings: Settings, opus: bytes
) -> None:
    await login(client)
    await link(client, database)
    with database.session() as session:
        session.add(
            TelegramState(
                id=1, bot_id=123, next_offset=2, heartbeat_at=datetime.now(UTC)
            )
        )
        session.commit()
    replies: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/getUpdates"):
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": [
                        message(
                            2,
                            12345,
                            document={"file_id": "file", "file_size": len(opus)},
                        )
                    ],
                },
            )
        if request.url.path.endswith("/getFile"):
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {
                        "file_path": "voice/file.ogg",
                        "file_size": len(opus),
                    },
                },
            )
        if "/file/bot" in request.url.path:
            return httpx.Response(200, content=opus)
        if request.url.path.endswith("/sendMessage"):
            replies.append(request.content.decode())
            return httpx.Response(200, json={"ok": True, "result": True})
        raise AssertionError("Unexpected Telegram API call")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        cycle(database, settings, TelegramApi(settings, http))
        cycle(database, settings, TelegramApi(settings, http))
    with database.session() as session:
        state = session.get(TelegramState, 1)
        assert state and state.next_offset == 3
        assert session.scalar(select(func.count()).select_from(MediaFile)) == 1
        row = session.get(TelegramUpdate, 2)
        assert row and row.status == "ready" and row.notified
    assert len(replies) == 2  # Link confirmation and one ready notification.


@pytest.mark.parametrize(
    "path", ["../private", "/absolute", "https://other/file", "audio//file"]
)
def test_download_rejects_unsafe_telegram_paths(settings: Settings, path: str) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "result": {"file_path": path}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(ServiceError, match="TELEGRAM_INVALID_RESPONSE"):
            TelegramApi(settings, http).download("file")


def test_download_enforces_stream_limit_and_rate_limit(settings: Settings) -> None:
    limited = settings.model_copy(update={"telegram_max_file_bytes": 3})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/getFile"):
            return httpx.Response(
                200, json={"ok": True, "result": {"file_path": "audio/file"}}
            )
        return httpx.Response(200, content=b"oversized")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(ServiceError, match="FILE_TOO_LARGE"):
            TelegramApi(limited, http).download("file")
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                429,
                json={
                    "ok": False,
                    "error_code": 429,
                    "parameters": {"retry_after": 17},
                },
            )
        )
    ) as http:
        with pytest.raises(ServiceError) as error:
            TelegramApi(settings, http).updates(0, 1)
        assert error.value.retry_after == 17 and error.value.status == 503


async def test_receive_convert_apply_and_retry_are_atomic(
    client: httpx.AsyncClient, database: Database, settings: Settings, opus: bytes
) -> None:
    await login(client)
    await link(client, database)
    body = message(
        2,
        12345,
        audio={"file_id": "fixture", "file_size": len(opus)},
        caption="Imported title",
    )
    with database.session() as session:
        telegram.receive(session, body)
        telegram.receive(session, body)
    with database.session() as session:
        telegram.process_one(session, settings, lambda _: BytesIO(opus))
    response = await client.get("/api/telegram/imports")
    row = response.json()["imports"][0]
    assert row["status"] == "ready" and row["title"] == "Imported title"
    assert response.json()["total"] == 1
    assert (
        await client.get(f"/api/telegram/imports/{row['id']}/audio")
    ).status_code == 200
    payload = {"title": "New exercise", "description": "From Telegram"}
    applied = await client.post(
        f"/api/telegram/imports/{row['id']}/apply", json=payload
    )
    assert applied.status_code == 200
    repeated = await client.post(
        f"/api/telegram/imports/{row['id']}/apply", json=payload
    )
    assert repeated.json() == applied.json()
    conflict = await client.post(
        f"/api/telegram/imports/{row['id']}/apply", json={**payload, "title": "Changed"}
    )
    assert conflict.status_code == 409
    with database.session() as session:
        assert session.scalar(select(func.count()).select_from(Exercise)) == 1
        assert session.scalar(select(func.count()).select_from(MediaFile)) == 1


async def test_import_owner_revocation_and_failed_media(
    client: httpx.AsyncClient, database: Database, settings: Settings
) -> None:
    await login(client)
    await create_user(client, "manager-two", "manager")
    await link(client, database)
    with database.session() as session:
        telegram.receive(session, message(2, 999, document={"file_id": "denied"}))
        telegram.receive(session, message(3, 12345, document={"file_id": "bad"}))
        telegram.process_one(session, settings, lambda _: BytesIO(b"not audio"))
    row = (await client.get("/api/telegram/imports")).json()["imports"][0]
    assert row["status"] == "failed" and row["last_error"] == "UNSUPPORTED_MEDIA"
    await login(client, "manager-two")
    assert (await client.get("/api/telegram/imports")).json()["total"] == 0
    assert (
        await client.get(f"/api/telegram/imports/{row['id']}/audio")
    ).status_code == 404
    assert (
        await client.post(
            f"/api/telegram/imports/{row['id']}/apply",
            json={"title": "Denied", "description": ""},
        )
    ).status_code == 404
    with database.session() as session:
        owner = session.scalar(select(User).where(User.is_emergency))
        assert owner
        owner.is_active = False
        session.commit()
        telegram.receive(session, message(4, 12345, audio={"file_id": "denied"}))
        assert (
            session.scalar(
                select(func.count())
                .select_from(TelegramUpdate)
                .where(TelegramUpdate.file_id.is_not(None))
            )
            == 1
        )
