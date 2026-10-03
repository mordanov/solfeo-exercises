import httpx
import pytest

from app.database import Database
from app.settings import Settings

pytestmark = pytest.mark.anyio


async def _make_manager(settings: Settings, database: Database) -> tuple[str, str]:
    from app.services.auth import create_user

    with database.session() as s:
        create_user(
            s,
            settings,
            username="mgr2",
            password="P@ssw0rd!!",
            first_name="M",
            last_name="X",
            role="manager",
            must_change_password=False,
        )
    return "mgr2", "P@ssw0rd!!"


async def _make_student(settings: Settings, database: Database) -> tuple[str, str]:
    from app.services.auth import create_user

    with database.session() as s:
        create_user(
            s,
            settings,
            username="stu2",
            password="P@ssw0rd!!",
            first_name="S",
            last_name="X",
            role="student",
            must_change_password=False,
        )
    return "stu2", "P@ssw0rd!!"


async def _login(
    client: httpx.AsyncClient, username: str, password: str
) -> dict[str, object]:
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert r.status_code == 200
    return r.json()  # type: ignore[no-any-return]


async def _create_player(c: httpx.AsyncClient, auth: dict[str, object]) -> int:
    r = await c.post(
        "/api/game/players",
        json={"name": "Kid1", "avatar_animal": "dragon"},
        headers={"X-CSRF-Token": str(auth["csrf_token"])},
    )
    assert r.status_code == 200
    return int(r.json()["id"])


async def test_reset_creates_new_season(
    client: httpx.AsyncClient, settings: Settings, database: Database
) -> None:
    u, p = await _make_manager(settings, database)
    auth = await _login(client, u, p)
    pid = await _create_player(client, auth)

    r = await client.post(
        f"/api/game/players/{pid}/seasons/reset",
        json={"confirmation": "RESET"},
        headers={"X-CSRF-Token": str(auth["csrf_token"])},
    )
    assert r.status_code == 200
    assert r.json()["number"] == 2


async def test_xp_preserved_after_reset(
    client: httpx.AsyncClient, settings: Settings, database: Database
) -> None:
    u, p = await _make_manager(settings, database)
    auth = await _login(client, u, p)
    pid = await _create_player(client, auth)

    r = await client.post(
        f"/api/game/players/{pid}/seasons/reset",
        json={"confirmation": "RESET"},
        headers={"X-CSRF-Token": str(auth["csrf_token"])},
    )
    assert r.status_code == 200

    pr = await client.get(
        f"/api/game/players/{pid}",
        headers={"X-CSRF-Token": str(auth["csrf_token"])},
    )
    assert pr.json()["xp"] >= 0


async def test_list_seasons(
    client: httpx.AsyncClient, settings: Settings, database: Database
) -> None:
    u, p = await _make_manager(settings, database)
    auth = await _login(client, u, p)
    pid = await _create_player(client, auth)

    r = await client.get(f"/api/game/players/{pid}/seasons")
    assert r.status_code == 200
    seasons = r.json()
    assert len(seasons) >= 1
    assert seasons[0]["number"] == 1


async def test_student_cannot_reset_season(
    client: httpx.AsyncClient, settings: Settings, database: Database
) -> None:
    mu, mp = await _make_manager(settings, database)
    mauth = await _login(client, mu, mp)
    pid = await _create_player(client, mauth)

    su, sp = await _make_student(settings, database)
    sauth = await _login(client, su, sp)

    r = await client.post(
        f"/api/game/players/{pid}/seasons/reset",
        json={"confirmation": "RESET"},
        headers={"X-CSRF-Token": str(sauth["csrf_token"])},
    )
    assert r.status_code == 403


async def test_wrong_confirmation_rejected(
    client: httpx.AsyncClient, settings: Settings, database: Database
) -> None:
    u, p = await _make_manager(settings, database)
    auth = await _login(client, u, p)
    pid = await _create_player(client, auth)

    r = await client.post(
        f"/api/game/players/{pid}/seasons/reset",
        json={"confirmation": "yes"},
        headers={"X-CSRF-Token": str(auth["csrf_token"])},
    )
    assert r.status_code == 400
