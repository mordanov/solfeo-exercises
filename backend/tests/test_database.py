from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi import Depends
from pydantic import SecretStr, ValidationError
from sqlalchemy import Connection, Engine, String, event, func, inspect, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import QueuePool

from app.api.dependencies import get_session
from app.database import Database
from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class ProbeBase(DeclarativeBase):
    pass


class Probe(ProbeBase):
    __tablename__ = "_solfeo_session_probe"

    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(String(50))


@pytest.fixture
def database_settings() -> Settings:
    settings = Settings()
    if settings.database_name != "solfeo_test":
        raise pytest.UsageError(
            "Database tests require DATABASE_NAME=solfeo_test "
            "on a disposable PostgreSQL."
        )
    return settings


@pytest.fixture
def database(database_settings: Settings) -> Iterator[Database]:
    database = Database(database_settings)
    try:
        with database.engine.connect() as connection:
            assert connection.scalar(text("SELECT current_database()")) == "solfeo_test"
        yield database
    finally:
        database.close()


@pytest.fixture
def probe(database: Database) -> Iterator[Database]:
    ProbeBase.metadata.create_all(database.engine)
    try:
        yield database
    finally:
        ProbeBase.metadata.drop_all(database.engine)


def count_rows(database: Database) -> int:
    with database.session() as session:
        return session.scalar(select(func.count()).select_from(Probe)) or 0


def migration_config(connection: Connection) -> Config:
    config = Config(str(ROOT / "backend" / "alembic.ini"))
    config.attributes["connection"] = connection
    return config


def test_explicit_transaction_commits(probe: Database) -> None:
    with probe.session() as session, session.begin():
        session.add(Probe(value="committed"))
    assert count_rows(probe) == 1


def test_closing_session_does_not_commit(probe: Database) -> None:
    with probe.session() as session:
        session.add(Probe(value="not committed"))
        session.flush()
    assert count_rows(probe) == 0


def test_exception_rolls_back_and_does_not_poison_next_session(probe: Database) -> None:
    with pytest.raises(RuntimeError, match="synthetic failure"):
        with probe.session() as session, session.begin():
            session.add(Probe(value="rolled back"))
            session.flush()
            raise RuntimeError("synthetic failure")
    assert count_rows(probe) == 0
    with probe.session() as session, session.begin():
        session.add(Probe(value="after rollback"))
    assert count_rows(probe) == 1


def test_database_error_rolls_back(probe: Database) -> None:
    with pytest.raises(IntegrityError) as error:
        with probe.session() as session, session.begin():
            session.add_all(
                [
                    Probe(id=1, value="private-synthetic-value"),
                    Probe(id=1, value="duplicate"),
                ]
            )
    assert count_rows(probe) == 0
    assert "private-synthetic-value" not in str(error.value)


def test_migration_upgrade_repeat_downgrade_and_upgrade(database: Database) -> None:
    tables = inspect(database.engine).get_table_names()
    assert set(tables) <= {"alembic_version"}
    if tables:
        with database.engine.begin() as connection:
            command.downgrade(migration_config(connection), "base")
            connection.execute(text("DROP TABLE alembic_version"))
    assert inspect(database.engine).get_table_names() == []

    with database.engine.connect() as connection:
        config = migration_config(connection)
        command.upgrade(config, "head")
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "0001_initial"
        )
        assert inspect(connection).get_table_names() == ["alembic_version"]
        command.upgrade(config, "head")
        command.check(config)
        command.downgrade(config, "base")
        assert connection.scalar(text("SELECT count(*) FROM alembic_version")) == 0
        command.upgrade(config, "head")
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "0001_initial"
        )


@pytest.mark.anyio
async def test_application_owns_database_and_dependency_closes_sessions(
    database_settings: Settings,
) -> None:
    application = create_app(database_settings)
    disposed: list[bool] = []

    @application.get("/_test/database")
    def database_probe(
        session: Annotated[Session, Depends(get_session)],
    ) -> dict[str, int]:
        result = session.scalar(text("SELECT 1"))
        assert isinstance(result, int)
        return {"value": result}

    async with application.router.lifespan_context(application):
        database = application.state.database
        assert isinstance(database, Database)

        @event.listens_for(database.engine, "engine_disposed")
        def record_disposal(_engine: Engine) -> None:
            disposed.append(True)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test"
        ) as client:
            assert (await client.get("/_test/database")).json() == {"value": 1}
            assert isinstance(database.engine.pool, QueuePool)
            assert database.engine.pool.checkedout() == 0
            assert (await client.get("/api/health")).json() == {"status": "ok"}
    assert disposed == [True]


@pytest.mark.anyio
async def test_health_does_not_claim_database_readiness() -> None:
    settings = Settings(
        _env_file=None,
        database_host="127.0.0.1",
        database_port=1,
        database_password=SecretStr("synthetic-test-password"),
    )
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test"
        ) as client:
            assert (await client.get("/api/health")).json() == {"status": "ok"}


def test_failed_connection_is_not_hidden() -> None:
    database = Database(
        Settings(
            _env_file=None,
            database_host="127.0.0.1",
            database_port=1,
            database_password=SecretStr("synthetic-test-password"),
            database_connect_timeout_seconds=1,
        )
    )
    try:
        with pytest.raises(OperationalError):
            with database.session() as session:
                session.scalar(text("SELECT 1"))
    finally:
        database.close()


@pytest.mark.anyio
async def test_dependency_rolls_back_a_failed_request(
    probe: Database, database_settings: Settings
) -> None:
    application = create_app(database_settings)

    @application.post("/_test/error")
    def failing_request(session: Annotated[Session, Depends(get_session)]) -> None:
        session.add(Probe(value="request rollback"))
        session.flush()
        raise RuntimeError("synthetic request failure")

    async with application.router.lifespan_context(application):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test"
        ) as client:
            with pytest.raises(RuntimeError, match="synthetic request failure"):
                await client.post("/_test/error")
        database = application.state.database
        assert isinstance(database, Database)
        assert isinstance(database.engine.pool, QueuePool)
        assert database.engine.pool.checkedout() == 0
    assert count_rows(probe) == 0


def test_password_with_url_characters_is_not_interpolated() -> None:
    password = "synthetic:p@ss/%?#"
    settings = Settings(_env_file=None, database_password=SecretStr(password))
    assert settings.database_url.password == password
    assert settings.database_url.drivername == "postgresql+psycopg"
    assert password not in repr(settings)
    assert password not in str(settings.database_url)


@pytest.mark.parametrize(
    "setting,value",
    [
        ("DATABASE_PORT", "0"),
        ("DATABASE_PORT", "65536"),
        ("DATABASE_POOL_SIZE", "0"),
        ("DATABASE_MAX_OVERFLOW", "-1"),
        ("DATABASE_POOL_TIMEOUT_SECONDS", "0"),
        ("DATABASE_CONNECT_TIMEOUT_SECONDS", "0"),
        ("DATABASE_PASSWORD", ""),
        ("ALEMBIC_VERSION_SCHEMA", ""),
        ("ALEMBIC_VERSION_SCHEMA", "invalid.name"),
        ("ALEMBIC_VERSION_SCHEMA", "a" * 64),
    ],
)
def test_invalid_database_configuration_is_rejected(
    setting: str, value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_PASSWORD", "synthetic-test-password")
    monkeypatch.setenv(setting, value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_database_password_has_no_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_PASSWORD", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
