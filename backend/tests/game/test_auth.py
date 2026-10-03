import httpx
import pytest

from app.database import Database
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
    from app.services.auth import create_user

    with database.session() as s:
        create_user(
            s,
            settings,
            username="mgr",
            password="P@ssw0rd!!",
            first_name="M",
            last_name="X",
            role="manager",
            must_change_password=False,
        )
    return "mgr", "P@ssw0rd!!"


async def _make_student(settings: Settings, database: Database) -> tuple[str, str]:
    from app.services.auth import create_user

    with database.session() as s:
        create_user(
            s,
            settings,
            username="stu",
            password="P@ssw0rd!!",
            first_name="S",
            last_name="X",
            role="student",
            must_change_password=False,
        )
    return "stu", "P@ssw0rd!!"


async def test_student_cannot_create_player(
    client: httpx.AsyncClient, settings: Settings, database: Database
) -> None:
    u, p = await _make_student(settings, database)
    auth = await _login(client, u, p)
    r = await client.post(
        "/api/game/players",
        json={"name": "Kid", "avatar_animal": "dragon"},
        headers={"X-CSRF-Token": str(auth["csrf_token"])},
    )
    assert r.status_code == 403


async def test_student_cannot_reset_season(
    client: httpx.AsyncClient, settings: Settings, database: Database
) -> None:
    u, p = await _make_student(settings, database)
    auth = await _login(client, u, p)
    r = await client.post(
        "/api/game/players/999/seasons/reset",
        json={"confirmation": "RESET"},
        headers={"X-CSRF-Token": str(auth["csrf_token"])},
    )
    assert r.status_code == 403
