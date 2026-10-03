import httpx
import pytest

from app.database import Database
from app.services.auth import create_user
from app.settings import Settings

pytestmark = pytest.mark.anyio


async def _login(
    client: httpx.AsyncClient, username: str, password: str
) -> dict[str, object]:
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert r.status_code == 200
    return r.json()  # type: ignore[no-any-return]


async def _make_manager(settings: Settings, database: Database) -> tuple[str, str]:
    with database.session() as s:
        create_user(
            s,
            settings,
            username="mgr3",
            password="P@ssw0rd!!",
            first_name="M",
            last_name="X",
            role="manager",
            must_change_password=False,
        )
    return "mgr3", "P@ssw0rd!!"


async def _make_student(settings: Settings, database: Database) -> tuple[str, str]:
    with database.session() as s:
        create_user(
            s,
            settings,
            username="stu3",
            password="P@ssw0rd!!",
            first_name="S",
            last_name="X",
            role="student",
            must_change_password=False,
        )
    return "stu3", "P@ssw0rd!!"


async def test_stats_empty_for_new_player(
    client: httpx.AsyncClient, settings: Settings, database: Database
) -> None:
    u, p = await _make_manager(settings, database)
    auth = await _login(client, u, p)
    r = await client.post(
        "/api/game/players",
        json={"name": "Stat", "avatar_animal": "unicorn"},
        headers={"X-CSRF-Token": str(auth["csrf_token"])},
    )
    assert r.status_code == 200
    pid = r.json()["id"]
    sr = await client.get(f"/api/game/players/{pid}/stats")
    assert sr.status_code == 200
    data = sr.json()
    assert isinstance(data, dict)


async def test_confusion_requires_manager(
    client: httpx.AsyncClient, settings: Settings, database: Database
) -> None:
    u, p = await _make_student(settings, database)
    await _login(client, u, p)
    r = await client.get("/api/game/players/999/confusion")
    assert r.status_code == 403
