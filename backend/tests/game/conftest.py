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
