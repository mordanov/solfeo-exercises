from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import httpx
import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import Depends
from pydantic import SecretStr, ValidationError
from sqlalchemy import (
    Connection,
    Engine,
    String,
    delete,
    event,
    func,
    insert,
    inspect,
    select,
    text,
)
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import QueuePool

from app.api.dependencies import get_session
from app.database import Database
from app.main import create_app
from app.models import Base, User
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
    settings = Settings(
        emergency_manager_username="", emergency_manager_password=SecretStr("")
    )
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
    assert set(tables) <= {"alembic_version", *Base.metadata.tables}
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
            == "0010_round_rules"
        )
        assert set(inspect(connection).get_table_names()) == {
            "alembic_version",
            *Base.metadata.tables,
        }
        command.upgrade(config, "head")
        command.check(config)
        command.downgrade(config, "base")
        assert connection.scalar(text("SELECT count(*) FROM alembic_version")) == 0
        command.upgrade(config, "head")
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "0010_round_rules"
        )


@pytest.mark.parametrize("previous_revision", ["0008_game", "0009_avatar_sheets"])
def test_round_rules_migration_preserves_previous_release_rows(
    database: Database,
    previous_revision: str,
) -> None:
    from app.game.models import CustomAvatar

    with database.engine.begin() as connection:
        config = migration_config(connection)
        command.downgrade(config, previous_revision)
        user_id = connection.scalar(
            text(
                "INSERT INTO users (username, password_hash, "
                "first_name, last_name, role) "
                "VALUES ('legacy-round-migration', 'synthetic-hash', "
                "'L', 'R', 'student') "
                "RETURNING id"
            )
        )
        player_id = connection.scalar(
            text(
                "INSERT INTO players (account_id, name) "
                "VALUES (:account_id, 'Legacy') RETURNING id"
            ),
            {"account_id": user_id},
        )
        season_id = connection.scalar(
            text(
                "INSERT INTO seasons (player_id, number) "
                "VALUES (:player_id, 1) RETURNING id"
            ),
            {"player_id": player_id},
        )
        avatar_id: int | None = None
        if previous_revision == "0009_avatar_sheets":
            avatar_id = connection.scalar(
                insert(CustomAvatar)
                .values(
                    account_id=user_id,
                    player_id=player_id,
                    description="Synthetic active job",
                    status="pending",
                    asset_version=2,
                    phase="generating",
                    completed_images=0,
                    attempts=1,
                    lease_token="synthetic-active-lease",
                    locked_at=func.now(),
                    base_path="avatars/custom/synthetic/sheet.png",
                )
                .returning(CustomAvatar.id)
            )
            assert avatar_id is not None
        for status in ("active", "completed"):
            connection.execute(
                text(
                    "INSERT INTO rounds (player_id, season_id, difficulty, "
                    "note_count, note_naming, "
                    "status, score, correct_count, expires_at) "
                    "VALUES (:player_id, :season_id, 'easy', 1, 'letters', :status, "
                    "3, 5, now() + interval '1 day')"
                ),
                {"player_id": player_id, "season_id": season_id, "status": status},
            )
        command.upgrade(config, "head")
        rows = (
            connection.execute(
                text(
                    "SELECT status, score, correct_count, rules_version, "
                    "show_sound_hint, show_correct_answer "
                    "FROM rounds WHERE player_id = :player_id ORDER BY status"
                ),
                {"player_id": player_id},
            )
            .tuples()
            .all()
        )
        assert rows == [
            ("active", 3, 5, 1, True, False),
            ("completed", 3, 5, 1, True, False),
        ]
        if avatar_id is not None:
            avatar = (
                connection.execute(
                    select(
                        CustomAvatar.status,
                        CustomAvatar.asset_version,
                        CustomAvatar.phase,
                        CustomAvatar.completed_images,
                        CustomAvatar.attempts,
                        CustomAvatar.lease_token,
                        CustomAvatar.base_path,
                    ).where(CustomAvatar.id == avatar_id)
                )
                .tuples()
                .one()
            )
            assert avatar == (
                "pending",
                2,
                "generating",
                0,
                1,
                "synthetic-active-lease",
                "avatars/custom/synthetic/sheet.png",
            )
            connection.execute(delete(CustomAvatar).where(CustomAvatar.id == avatar_id))
        command.check(config)
        connection.execute(
            text("DELETE FROM rounds WHERE player_id = :player_id"),
            {"player_id": player_id},
        )
        connection.execute(
            text("DELETE FROM seasons WHERE player_id = :player_id"),
            {"player_id": player_id},
        )
        connection.execute(
            text("DELETE FROM players WHERE id = :player_id"), {"player_id": player_id}
        )
        connection.execute(
            text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id}
        )


def test_round_rules_is_the_single_head_after_avatar_sheets() -> None:
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "backend/alembic.ini")))
    assert scripts.get_heads() == ["0010_round_rules"]
    revision = scripts.get_revision("0010_round_rules")
    assert revision is not None
    assert revision.down_revision == "0009_avatar_sheets"


def test_avatar_migration_preserves_ready_art_without_retrying_legacy_jobs(
    database: Database,
) -> None:
    from app.game.models import CustomAvatar, Player

    with database.engine.begin() as connection:
        config = migration_config(connection)
        command.downgrade(config, "0008_game")
        account_id = connection.scalar(
            insert(User)
            .values(
                username="synthetic-avatar-migration",
                first_name="Migration",
                last_name="Test",
                role="manager",
                password_hash="synthetic-unused-hash",
            )
            .returning(User.id)
        )
        player_id = connection.scalar(
            insert(Player)
            .values(account_id=account_id, name="Migration")
            .returning(Player.id)
        )
        job_ids = [
            connection.scalar(
                text(
                    "INSERT INTO custom_avatars "
                    "(account_id, player_id, description, status, base_path) "
                    "VALUES (:account, :player, 'Synthetic', :status, :path) "
                    "RETURNING id"
                ),
                {
                    "account": account_id,
                    "player": player_id,
                    "status": status,
                    "path": "avatars/custom/synthetic/base.png",
                },
            )
            for status in ("ready", "pending", "failed")
        ]
        command.upgrade(config, "head")
        rows = list(
            connection.execute(
                select(
                    CustomAvatar.status,
                    CustomAvatar.asset_version,
                    CustomAvatar.phase,
                    CustomAvatar.completed_images,
                    CustomAvatar.base_path,
                    CustomAvatar.error_code,
                )
                .where(CustomAvatar.id.in_(job_ids))
                .order_by(CustomAvatar.id)
            )
        )
        assert rows[0][:4] == ("ready", 1, "complete", 3)
        assert rows[0][4] == "avatars/custom/synthetic/base.png"
        assert rows[1][:4] == ("failed", 1, "failed", 0)
        assert rows[1][5] == "AVATAR_GENERATION_INTERRUPTED"
        assert rows[2][:4] == ("failed", 1, "failed", 0)
        command.check(config)
        connection.execute(delete(CustomAvatar).where(CustomAvatar.id.in_(job_ids)))
        connection.execute(delete(Player).where(Player.id == player_id))
        connection.execute(delete(User).where(User.id == account_id))


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
async def test_startup_fails_if_emergency_sync_cannot_reach_database() -> None:
    settings = Settings(
        _env_file=None,
        database_host="127.0.0.1",
        database_port=1,
        database_password=SecretStr("synthetic-test-password"),
    )
    application = create_app(settings)
    with pytest.raises(OperationalError):
        async with application.router.lifespan_context(application):
            pytest.fail("Startup must complete emergency synchronization")


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
