import httpx
import pytest
from test_auth import (
    anyio_backend,
    client,
    create_user,
    database,
    login,
    settings,
)

from app.database import Database
from app.services import chapters
from app.services.auth import ServiceError

pytestmark = pytest.mark.anyio
__all__ = ["anyio_backend", "client", "database", "settings"]


def test_chapter_service_uses_permanent_numbers_and_reports_missing(
    database: Database,
) -> None:
    with database.session() as session:
        chapter = chapters.create_chapter(session)
        first_number = chapter.number
        assert first_number > 1

        chapters.delete_chapter(session, chapter.id)
        next_chapter = chapters.create_chapter(session)
        assert next_chapter.number == first_number + 1

        with pytest.raises(ServiceError) as error:
            chapters.delete_chapter(session, chapter.id)
        assert (error.value.code, error.value.status) == ("CHAPTER_NOT_FOUND", 404)

        chapters.delete_chapter(session, next_chapter.id)


async def test_chapter_routes_list_create_and_never_reuse_numbers(
    client: httpx.AsyncClient,
) -> None:
    await login(client)
    initial = await client.get("/api/chapters")
    assert initial.status_code == 200, initial.text
    assert [row["number"] for row in initial.json()["chapters"]] == [1]

    created = await client.post("/api/chapters")
    assert created.status_code == 201, created.text
    chapter = created.json()
    assert chapter["number"] > 1
    assert chapter["active_exercise_count"] == 0
    assert chapter["assigned_exercise_count"] == 0
    assert chapter in (await client.get("/api/chapters")).json()["chapters"]

    removed = await client.delete(f"/api/chapters/{chapter['id']}")
    assert removed.status_code == 200, removed.text
    assert all(
        row["id"] != chapter["id"]
        for row in (await client.get("/api/chapters")).json()["chapters"]
    )

    next_chapter = await client.post("/api/chapters")
    assert next_chapter.status_code == 201, next_chapter.text
    assert next_chapter.json()["number"] == chapter["number"] + 1
    removed_next = await client.delete(f"/api/chapters/{next_chapter.json()['id']}")
    assert removed_next.status_code == 200


async def test_chapter_read_access_and_manager_csrf_permissions(
    client: httpx.AsyncClient,
) -> None:
    assert (await client.get("/api/chapters")).status_code == 401
    await login(client)
    chapter = await client.post("/api/chapters")
    assert chapter.status_code == 201, chapter.text
    chapter_id = chapter.json()["id"]

    csrf_token = client.headers.pop("X-CSRF-Token")
    assert (await client.post("/api/chapters")).status_code == 403
    assert (await client.delete(f"/api/chapters/{chapter_id}")).status_code == 403
    client.headers["X-CSRF-Token"] = csrf_token

    await create_user(client)
    client.cookies.clear()
    await login(client, "student")
    assert (await client.get("/api/chapters")).json()["chapters"] == []
    assert (await client.post("/api/chapters")).status_code == 403
    assert (await client.delete(f"/api/chapters/{chapter_id}")).status_code == 403

    client.cookies.clear()
    await login(client)
    await create_user(client, "player", "player")
    client.cookies.clear()
    await login(client, "player")
    assert (await client.get("/api/chapters")).status_code == 403
    assert (await client.post("/api/chapters")).status_code == 403

    client.cookies.clear()
    await login(client)
    assert (await client.delete(f"/api/chapters/{chapter_id}")).status_code == 200


async def test_delete_missing_chapter_returns_stable_error(
    client: httpx.AsyncClient,
) -> None:
    await login(client)
    response = await client.delete("/api/chapters/987654321")
    assert response.status_code == 404
    assert response.json() == {"error": "CHAPTER_NOT_FOUND"}
