import io
import subprocess
from pathlib import Path

import httpx
import pytest
from PIL import Image
from test_auth import (  # Reuse the disposable database and authenticated API fixtures.
    anyio_backend,
    client,
    create_user,
    database,
    login,
)
from test_auth import (
    settings as auth_settings,
)

from app.models import Exercise
from app.services.auth import ServiceError
from app.services.media import prepare_media
from app.settings import Settings

__all__ = ["anyio_backend", "client", "database", "auth_settings"]
pytestmark = pytest.mark.anyio


@pytest.fixture
def settings(auth_settings: Settings, tmp_path: Path) -> Settings:
    return auth_settings.model_copy(update={"media_root": tmp_path / "media"})


@pytest.fixture
def png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
def opus(tmp_path: Path) -> bytes:
    target = tmp_path / "tone.opus"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-c:a",
            "libopus",
            str(target),
        ],
        check=True,
        timeout=15,
    )
    return target.read_bytes()


async def create_exercise(
    client: httpx.AsyncClient, png: bytes, title: str = "Scale"
) -> int:
    response = await client.post(
        "/api/exercises",
        data={"title": title, "description": "Practice"},
        files={"image": ("untrusted.txt", png, "text/plain")},
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


async def test_crud_original_and_soft_delete(
    client: httpx.AsyncClient,
    png: bytes,
    settings: Settings,
    database: object,
) -> None:
    await login(client)
    identifier = await create_exercise(client, png)
    response = await client.get(f"/api/exercises/{identifier}")
    assert response.json()["image"]["mime_type"] == "image/png"
    file_response = await client.get(f"/api/exercises/{identifier}/files/image")
    assert file_response.status_code == 200
    target = file_response.headers["x-accel-redirect"].removeprefix(
        "/_protected_media/"
    )
    assert (settings.media_root / target).read_bytes() == png
    assert file_response.headers["content-type"] == "image/png"
    updated = await client.put(
        f"/api/exercises/{identifier}",
        data={"title": "Updated", "description": "Text", "category": "Level 1"},
    )
    assert updated.status_code == 200
    assert updated.json()["category"] == "Level 1"
    rejected = await client.put(
        f"/api/exercises/{identifier}", data={"title": "Empty", "remove_image": "true"}
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"] == "EXERCISE_MEDIA_REQUIRED"
    assert (await client.delete(f"/api/exercises/{identifier}")).status_code == 200
    assert (await client.get("/api/exercises")).json()["exercises"] == []
    assert (await client.get(f"/api/exercises/{identifier}")).status_code == 404
    assert (
        await client.get(f"/api/exercises/{identifier}/files/image")
    ).status_code == 404
    from app.database import Database

    assert isinstance(database, Database)
    with database.session() as session:
        row = session.get(Exercise, identifier)
        assert row is not None and row.deleted_at is not None
    assert (settings.media_root / target).read_bytes() == png


async def test_opus_conversion_and_atomic_validation(
    client: httpx.AsyncClient,
    opus: bytes,
    png: bytes,
    settings: Settings,
) -> None:
    await login(client)
    empty = await client.post("/api/exercises", data={"title": "Missing"})
    assert empty.status_code == 422
    assert empty.json()["error"] == "EXERCISE_MEDIA_REQUIRED"
    bad = await client.post(
        "/api/exercises",
        data={"title": "Invalid"},
        files={
            "image": ("image.png", png, "image/png"),
            "audio": ("audio.opus", b"not audio", "audio/ogg"),
        },
    )
    assert bad.status_code == 415
    assert (await client.get("/api/exercises")).json()["total"] == 0
    assert not list(settings.media_root.glob("*.*"))
    result = await client.post(
        "/api/exercises",
        data={"title": "Audio"},
        files={"audio": ("../../audio.txt", opus, "text/plain")},
    )
    assert result.status_code == 201, result.text
    audio = result.json()["audio"]
    assert audio["mime_type"] == "audio/mp4"
    assert 1.9 <= audio["duration_seconds"] <= 2.2
    response = await client.get(f"/api/exercises/{result.json()['id']}/files/audio")
    target = response.headers["x-accel-redirect"].removeprefix("/_protected_media/")
    assert target.endswith(".m4a")
    assert not list(settings.media_root.rglob("*.opus"))


async def test_reorder_requires_exact_current_set_and_is_persistent(
    client: httpx.AsyncClient,
    png: bytes,
) -> None:
    await login(client)
    first = await create_exercise(client, png, "First")
    second = await create_exercise(client, png, "Second")
    for ids in ([first], [first, first], [first, second, 999999]):
        response = await client.put("/api/exercises/order", json={"ids": ids})
        assert response.status_code == 409
    result = await client.put("/api/exercises/order", json={"ids": [second, first]})
    assert result.status_code == 200
    rows = (await client.get("/api/exercises")).json()["exercises"]
    assert [row["id"] for row in rows] == [second, first]
    assert [row["position"] for row in rows] == [0, 1]
    await client.delete(f"/api/exercises/{second}")
    rows = (await client.get("/api/exercises")).json()["exercises"]
    assert rows[0]["position"] == 0


async def test_permissions_and_csrf(client: httpx.AsyncClient, png: bytes) -> None:
    assert (await client.get("/api/exercises")).status_code == 401
    await login(client)
    identifier = await create_exercise(client, png)
    await create_user(client)
    csrf = client.headers.pop("X-CSRF-Token")
    assert (await client.delete(f"/api/exercises/{identifier}")).status_code == 403
    client.headers["X-CSRF-Token"] = csrf
    await login(client, "student")
    assert (await client.get("/api/exercises")).status_code == 200
    assert (
        await client.get(f"/api/exercises/{identifier}/files/image")
    ).status_code == 200
    for method, path in (
        ("POST", "/api/exercises"),
        ("PUT", f"/api/exercises/{identifier}"),
        ("DELETE", f"/api/exercises/{identifier}"),
        ("PUT", "/api/exercises/order"),
    ):
        response = await client.request(method, path, json={"ids": [identifier]})
        assert response.status_code == 403, response.text
    client.cookies.clear()
    assert (
        await client.get(f"/api/exercises/{identifier}/files/image")
    ).status_code == 401


def test_media_limits_and_image_validation(settings: Settings, png: bytes) -> None:
    limited = settings.model_copy(update={"image_max_bytes": len(png) - 1})
    with pytest.raises(ServiceError, match="FILE_TOO_LARGE"):
        prepare_media(io.BytesIO(png), "image", limited)
    for data in (b"<svg></svg>", png[:30], b"GIF89a" + bytes(200)):
        with pytest.raises(ServiceError, match="UNSUPPORTED_MEDIA|INVALID_IMAGE"):
            prepare_media(io.BytesIO(data), "image", settings)
    assert not list(settings.media_root.glob("*.*"))


async def test_replacement_retains_original_and_rolls_back_bad_update(
    client: httpx.AsyncClient,
    png: bytes,
    opus: bytes,
    settings: Settings,
) -> None:
    await login(client)
    identifier = await create_exercise(client, png)
    original = (await client.get(f"/api/exercises/{identifier}/files/image")).headers[
        "x-accel-redirect"
    ]
    response = await client.put(
        f"/api/exercises/{identifier}",
        data={"title": "Audio only", "remove_image": "true"},
        files={"audio": ("sound.opus", opus)},
    )
    assert response.status_code == 200, response.text
    assert response.json()["image"] is None
    assert (settings.media_root / original.rsplit("/", 1)[1]).read_bytes() == png
    response = await client.put(
        f"/api/exercises/{identifier}",
        data={"title": "Both"},
        files={"image": ("score.png", png)},
    )
    assert response.status_code == 200, response.text
    assert response.json()["audio"] is not None and response.json()["image"] is not None
    bad = await client.put(
        f"/api/exercises/{identifier}",
        data={"title": "Never saved"},
        files={"image": ("broken.png", b"broken")},
    )
    assert bad.status_code == 415
    assert (await client.get(f"/api/exercises/{identifier}")).json()["title"] == "Both"


@pytest.mark.parametrize(
    "extension,codec",
    [
        ("mp3", "libmp3lame"),
        ("ogg", "libvorbis"),
        ("wav", "pcm_s16le"),
        ("aac", "aac"),
        ("m4a", "aac"),
    ],
)
def test_common_audio_formats_convert(
    settings: Settings,
    tmp_path: Path,
    extension: str,
    codec: str,
) -> None:
    path = tmp_path / f"tone.{extension}"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=duration=1",
            "-c:a",
            codec,
            str(path),
        ],
        check=True,
        timeout=15,
    )
    with path.open("rb") as source:
        result = prepare_media(source, "audio", settings)
    assert result.mime_type == "audio/mp4"
    assert result.duration_seconds is not None and 0.9 < result.duration_seconds < 1.2
    assert result.filename.endswith(".m4a")


@pytest.mark.parametrize("format", ["JPEG", "WEBP"])
def test_original_image_formats(settings: Settings, format: str) -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (24, 24), "white").save(buffer, format)
    original = buffer.getvalue()
    result = prepare_media(io.BytesIO(original), "image", settings)
    assert (settings.media_root / result.filename).read_bytes() == original


def test_duration_and_pixel_limits(settings: Settings, opus: bytes, png: bytes) -> None:
    with pytest.raises(ServiceError, match="AUDIO_TOO_LONG"):
        prepare_media(
            io.BytesIO(opus),
            "audio",
            settings.model_copy(update={"audio_max_seconds": 1}),
        )
    with pytest.raises(ServiceError, match="INVALID_IMAGE"):
        prepare_media(
            io.BytesIO(png),
            "image",
            settings.model_copy(update={"image_max_pixels": 10}),
        )
    with pytest.raises(ServiceError, match="EMPTY_FILE"):
        prepare_media(io.BytesIO(), "audio", settings)
    with pytest.raises(ServiceError, match="MEDIA_PROCESSOR_UNAVAILABLE"):
        prepare_media(
            io.BytesIO(png),
            "image",
            settings.model_copy(update={"file_binary": "/no-such-solfeo-binary"}),
        )


async def test_request_limit_before_parsing_and_for_chunked_requests(
    settings: Settings,
    database: object,
) -> None:
    from app.main import create_app

    app = create_app(settings.model_copy(update={"upload_max_bytes": 1024}))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://test"
        ) as http:
            response = await http.post("/api/exercises", content=b"x" * 1025)
            assert response.status_code == 413
            assert response.json() == {"error": "FILE_TOO_LARGE"}

            from collections.abc import AsyncIterator

            async def chunks() -> AsyncIterator[bytes]:
                yield b"x" * 600
                yield b"x" * 600

            response = await http.post(
                "/api/auth/login",
                content=chunks(),
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 413, response.text
