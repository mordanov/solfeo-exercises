from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete

from app.database import Database
from app.models import Base
from app.settings import Settings

pytestmark = pytest.mark.anyio

ORIGIN = "https://test"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def settings() -> Settings:
    result = Settings(auth_allowed_origins=[ORIGIN], session_cookie_secure=True)
    if result.database_name != "solfeo_test":
        raise pytest.UsageError("Set DATABASE_NAME=solfeo_test")
    return result


@pytest.fixture
def database(settings: Settings) -> Iterator[Database]:
    db = Database(settings)
    with db.engine.begin() as conn:
        config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
        config.attributes["connection"] = conn
        command.upgrade(config, "head")
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(delete(table))
    try:
        yield db
    finally:
        with db.engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(delete(table))
        db.close()


@pytest.fixture
async def client(
    settings: Settings, database: Database
) -> AsyncIterator[httpx.AsyncClient]:
    from app.main import create_app

    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=ORIGIN
        ) as c:
            yield c


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


@pytest.mark.skip(reason="season reset route added in T7")
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
