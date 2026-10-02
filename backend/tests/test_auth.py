from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr, ValidationError
from sqlalchemy import delete, select

from app.database import Database
from app.main import create_app
from app.models import Base, LoginSession, User
from app.services.auth import (
    ServiceError,
    hash_password,
    require_password,
    sync_emergency,
    verify_password,
)
from app.settings import Settings

PASSWORD = "synthetic-long-password"
APPEARANCE = {
    "light_scheme": "classic",
    "dark_scheme": "classic",
    "ui_font": "roboto",
    "ui_font_size": 16,
}
ORIGIN = "https://test"
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def settings() -> Settings:
    result = Settings(
        auth_allowed_origins=[ORIGIN],
        emergency_manager_username="recovery",
        emergency_manager_password=SecretStr(PASSWORD),
        session_cookie_secure=True,
        session_lifetime_days=90,
        password_min_length=8,
        login_username_limit=5,
    )
    if result.database_name != "solfeo_test":
        raise pytest.UsageError("Auth tests require a disposable solfeo_test database")
    return result


@pytest.fixture
def database(settings: Settings) -> Iterator[Database]:
    database = Database(settings)
    with database.engine.begin() as connection:
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(delete(table))
    try:
        yield database
    finally:
        with database.engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(delete(table))
        database.close()


@pytest.fixture
async def client(
    settings: Settings, database: Database
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=ORIGIN,
            headers={"Origin": ORIGIN},
        ) as client:
            yield client


async def login(
    client: httpx.AsyncClient, username: str = "recovery", password: str = PASSWORD
) -> httpx.Response:
    response = await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    if response.status_code == 200:
        client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response


async def create_user(
    client: httpx.AsyncClient, username: str = "student", role: str = "student"
) -> int:
    response = await client.post(
        "/api/users",
        json={
            "username": username,
            "password": PASSWORD,
            "first_name": "First",
            "last_name": "Last",
            "role": role,
            "must_change_password": False,
        },
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


@pytest.mark.parametrize("role", ["manager", "student"])
async def test_appearance_preferences_persist_without_changing_other_settings(
    client: httpx.AsyncClient, role: str
) -> None:
    await login(client)
    await create_user(client, role=role)
    client.cookies.clear()
    response = await login(client, "student")
    assert {key: response.json()["user"][key] for key in APPEARANCE} == APPEARANCE
    changed = {
        "light_scheme": "forest",
        "dark_scheme": "plum",
        "ui_font": "serif",
        "ui_font_size": 20,
    }
    response = await client.patch("/api/settings", json=changed)
    assert response.status_code == 200, response.text
    assert {key: response.json()[key] for key in changed} == changed
    assert response.json()["ui_language"] == "en"
    assert response.json()["note_naming"] == "letters"
    await client.patch("/api/settings", json={"ui_language": "es"})
    await client.post("/api/auth/logout")
    response = await login(client, "student")
    assert {key: response.json()["user"][key] for key in changed} == changed
    assert response.json()["user"]["ui_language"] == "es"
    assert (await client.patch("/api/settings", json=APPEARANCE)).status_code == 200
    assert (await client.get("/api/auth/me")).json()["user"]["ui_language"] == "es"


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"light_scheme": "#ffffff"},
        {"dark_scheme": "unknown"},
        {"ui_font": "url(https://example.invalid/font)"},
        {"ui_font_size": 15},
        {"ui_font_size": "20"},
        {"ui_font_size": True},
        {"light_scheme": "forest", "ui_font_size": 15},
        {"ui_font": None},
        {"ui_language": None},
        {"user_id": 999, "light_scheme": "warm"},
    ],
)
async def test_appearance_rejects_invalid_preferences_atomically(
    client: httpx.AsyncClient, changes: dict[str, str | int | None]
) -> None:
    await login(client)
    before = (await client.get("/api/auth/me")).json()["user"]
    assert (await client.patch("/api/settings", json=changes)).status_code == 422
    assert (await client.get("/api/auth/me")).json()["user"] == before


async def test_appearance_requires_authentication_and_csrf(
    client: httpx.AsyncClient,
) -> None:
    assert (await client.patch("/api/settings", json=APPEARANCE)).status_code == 401
    await login(client)
    client.headers.pop("X-CSRF-Token")
    assert (await client.patch("/api/settings", json=APPEARANCE)).status_code == 403


def test_appearance_defaults_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in {
        "DEFAULT_LIGHT_SCHEME": "forest",
        "DEFAULT_DARK_SCHEME": "plum",
        "DEFAULT_UI_FONT": "system",
        "DEFAULT_UI_FONT_SIZE": "18",
    }.items():
        monkeypatch.setenv(key, value)
    policy = Settings(_env_file=None, database_password=SecretStr("synthetic"))
    assert policy.default_light_scheme == "forest"
    assert policy.default_dark_scheme == "plum"
    assert policy.default_ui_font == "system"
    assert policy.default_ui_font_size == 18
    monkeypatch.setenv("DEFAULT_UI_FONT_SIZE", "19")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_password=SecretStr("synthetic"))


async def test_new_accounts_use_configured_appearance(
    client: httpx.AsyncClient, settings: Settings
) -> None:
    settings.default_light_scheme = "forest"
    settings.default_dark_scheme = "plum"
    settings.default_ui_font = "system"
    settings.default_ui_font_size = 18
    await login(client)
    await create_user(client)
    client.cookies.clear()
    user = (await login(client, "student")).json()["user"]
    assert {key: user[key] for key in APPEARANCE} == {
        "light_scheme": "forest",
        "dark_scheme": "plum",
        "ui_font": "system",
        "ui_font_size": 18,
    }


def test_emergency_appearance_defaults_do_not_replace_saved_preferences(
    database: Database, settings: Settings
) -> None:
    settings.default_light_scheme = "forest"
    settings.default_dark_scheme = "plum"
    settings.default_ui_font = "system"
    settings.default_ui_font_size = 18
    expected = {
        "light_scheme": "forest",
        "dark_scheme": "plum",
        "ui_font": "system",
        "ui_font_size": 18,
    }
    sync_emergency(database, settings)
    with database.session() as session:
        user = session.scalar(select(User).where(User.is_emergency))
        assert user is not None
        assert {key: getattr(user, key) for key in APPEARANCE} == expected
    settings.default_light_scheme = "classic"
    settings.default_dark_scheme = "classic"
    settings.default_ui_font = "roboto"
    settings.default_ui_font_size = 16
    sync_emergency(database, settings)
    with database.session() as session:
        user = session.scalar(select(User).where(User.is_emergency))
        assert user is not None
        assert {key: getattr(user, key) for key in APPEARANCE} == expected


def test_appearance_migration_preserves_existing_accounts(database: Database) -> None:
    from sqlalchemy import text

    with database.engine.begin() as connection:
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        config.attributes["connection"] = connection
        command.downgrade(config, "0006_omr")
        connection.execute(
            text(
                "INSERT INTO users (username, first_name, last_name, "
                "role, password_hash) VALUES ('migration', 'Existing', "
                "'Student', 'student', 'synthetic-hash')"
            )
        )
        command.upgrade(config, "head")
        row = (
            connection.execute(
                text(
                    "SELECT username, first_name, light_scheme, dark_scheme, "
                    "ui_font, ui_font_size FROM users"
                )
            )
            .mappings()
            .one()
        )
        assert row["username"] == "migration" and row["first_name"] == "Existing"
        assert {key: row[key] for key in APPEARANCE} == APPEARANCE
        command.downgrade(config, "0006_omr")
        command.upgrade(config, "head")


def test_passwords_use_salted_scrypt() -> None:
    first = hash_password(PASSWORD)
    assert first.startswith("scrypt$")
    assert first != hash_password(PASSWORD)
    assert PASSWORD not in first
    assert verify_password(PASSWORD, first)
    assert not verify_password("wrong-password", first)


@pytest.mark.parametrize(
    "length,accepted", [(7, False), (8, True), (256, True), (257, False)]
)
def test_default_password_policy_boundaries(
    monkeypatch: pytest.MonkeyPatch, length: int, accepted: bool
) -> None:
    monkeypatch.delenv("PASSWORD_MIN_LENGTH", raising=False)
    policy = Settings(
        _env_file=None,
        database_password=SecretStr("synthetic-password"),
        emergency_manager_username="",
        emergency_manager_password=SecretStr(""),
    )
    assert policy.password_min_length == 8
    if accepted:
        require_password("x" * length, policy)
    else:
        with pytest.raises(ServiceError, match="WEAK_PASSWORD") as failure:
            require_password("x" * length, policy)
        assert failure.value.status == 422


def test_operator_can_keep_a_stricter_password_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PASSWORD_MIN_LENGTH", "12")
    policy = Settings(
        _env_file=None,
        database_password=SecretStr("synthetic-password"),
        emergency_manager_username="",
        emergency_manager_password=SecretStr(""),
    )
    assert policy.password_min_length == 12
    with pytest.raises(ServiceError, match="WEAK_PASSWORD"):
        require_password("x" * 8, policy)
    require_password("x" * 12, policy)


@pytest.mark.parametrize("length,accepted", [(7, False), (8, True)])
def test_emergency_credentials_follow_default_password_minimum(
    monkeypatch: pytest.MonkeyPatch, length: int, accepted: bool
) -> None:
    monkeypatch.delenv("PASSWORD_MIN_LENGTH", raising=False)

    def configured() -> Settings:
        return Settings(
            _env_file=None,
            database_password=SecretStr("synthetic-password"),
            emergency_manager_username="recovery",
            emergency_manager_password=SecretStr("x" * length),
        )

    if accepted:
        assert configured().password_min_length == 8
    else:
        with pytest.raises(
            ValidationError, match="Invalid emergency manager credentials"
        ):
            configured()


@pytest.mark.parametrize("operation", ["create", "reset", "change"])
@pytest.mark.parametrize("length,accepted", [(7, False), (8, True)])
async def test_password_minimum_at_every_mutation(
    client: httpx.AsyncClient, operation: str, length: int, accepted: bool
) -> None:
    await login(client)
    replacement = "x" * length
    if operation == "create":
        response = await client.post(
            "/api/users",
            json={
                "username": "student",
                "password": replacement,
                "first_name": "First",
                "last_name": "Last",
                "role": "student",
            },
        )
        success = 201
    else:
        identifier = await create_user(client)
        if operation == "reset":
            response = await client.post(
                f"/api/users/{identifier}/password", json={"password": replacement}
            )
        else:
            client.cookies.clear()
            await login(client, "student")
            response = await client.put(
                "/api/auth/password",
                json={"current_password": PASSWORD, "new_password": replacement},
            )
        success = 200
    assert response.status_code == (success if accepted else 422)
    if accepted:
        client.cookies.clear()
        assert (await login(client, "student", replacement)).status_code == 200
    else:
        assert response.json() == {"error": "WEAK_PASSWORD"}


def test_emergency_create_reset_disable_and_reactivate(
    database: Database, settings: Settings
) -> None:
    sync_emergency(database, settings)
    with database.session() as session:
        user = session.scalar(select(User).where(User.is_emergency))
        assert user is not None and user.is_active and user.role == "manager"
        identifier = user.id
        assert verify_password(PASSWORD, user.password_hash)
    changed = settings.model_copy(
        update={"emergency_manager_password": SecretStr("changed-long-password")}
    )
    sync_emergency(database, changed)
    with database.session() as session:
        user = session.get(User, identifier)
        assert user is not None and verify_password(
            "changed-long-password", user.password_hash
        )
    disabled = settings.model_copy(
        update={
            "emergency_manager_username": "",
            "emergency_manager_password": SecretStr(""),
        }
    )
    sync_emergency(database, disabled)
    with database.session() as session:
        user = session.get(User, identifier)
        assert user is not None and not user.is_active and user.is_emergency
    sync_emergency(database, settings)
    with database.session() as session:
        user = session.get(User, identifier)
        assert (
            user is not None
            and user.is_active
            and verify_password(PASSWORD, user.password_hash)
        )


async def test_login_cookie_csrf_sliding_expiry_and_logout(
    client: httpx.AsyncClient, database: Database
) -> None:
    assert (await client.get("/api/auth/me")).status_code == 401
    response = await login(client)
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert all(
        part in cookie.lower()
        for part in ("httponly", "secure", "samesite=lax", "max-age=7776000")
    )
    token = client.cookies.get("solfeo_session")
    with database.session() as session, session.begin():
        stored = session.scalar(select(LoginSession))
        assert stored is not None and stored.token_hash != token
        stored.expires_at = datetime.now(UTC) + timedelta(hours=1)
    assert (await client.get("/api/auth/me")).json()["user"]["role"] == "manager"
    with database.session() as session:
        stored = session.scalar(select(LoginSession))
        assert stored is not None and stored.expires_at > datetime.now(UTC) + timedelta(
            days=89
        )
    assert (await client.post("/api/auth/logout")).status_code == 200
    assert (await client.get("/api/auth/me")).status_code == 401


@pytest.mark.parametrize(
    "path,method",
    [
        ("/api/auth/me", "GET"),
        ("/api/users", "GET"),
        ("/api/users", "POST"),
        ("/api/settings", "PATCH"),
        ("/api/users/1", "PATCH"),
        ("/api/users/1/password", "POST"),
        ("/api/auth/password", "PUT"),
        ("/api/auth/logout", "POST"),
    ],
)
async def test_anonymous_cannot_access_protected_routes(
    client: httpx.AsyncClient, path: str, method: str
) -> None:
    assert (await client.request(method, path, json={})).status_code == 401


async def test_csrf_and_login_origin_are_required(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"username": "recovery", "password": PASSWORD},
        headers={"Origin": "https://attacker.test"},
    )
    assert response.status_code == 403
    await login(client)
    del client.headers["X-CSRF-Token"]
    response = await client.patch(
        "/api/settings", json={"ui_language": "ru", "note_naming": "solfege"}
    )
    assert response.status_code == 403 and response.json()["error"] == "CSRF_FAILED"
    response = await client.get("/api/auth/me")
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    response = await client.post(
        "/api/auth/logout", headers={"Origin": "https://attacker.test"}
    )
    assert response.status_code == 403


async def test_student_boundaries_settings_persist_and_deactivation_revokes(
    client: httpx.AsyncClient, settings: Settings
) -> None:
    await login(client)
    identifier = await create_user(client)
    manager_cookie = client.cookies.get("solfeo_session")
    manager_csrf = client.headers["X-CSRF-Token"]
    client.cookies.clear()
    assert (await login(client, "STUDENT")).status_code == 200
    student_cookie = client.cookies.get("solfeo_session")
    for method, path, data in [
        ("GET", "/api/users", None),
        ("POST", "/api/users", {}),
        ("PATCH", f"/api/users/{identifier}", {"is_active": False}),
        ("POST", f"/api/users/{identifier}/password", {"password": PASSWORD}),
    ]:
        assert (await client.request(method, path, json=data)).status_code == 403
    response = await client.patch(
        "/api/settings", json={"ui_language": "es", "note_naming": "solfege"}
    )
    assert response.status_code == 200
    await client.post("/api/auth/logout")
    response = await login(client, "student")
    assert response.json()["user"]["ui_language"] == "es"
    assert response.json()["user"]["note_naming"] == "solfege"
    student_cookie = client.cookies.get("solfeo_session")
    client.cookies.clear()
    assert manager_cookie is not None
    client.cookies.set("solfeo_session", manager_cookie)
    client.headers["X-CSRF-Token"] = manager_csrf
    assert (
        await client.patch(f"/api/users/{identifier}", json={"is_active": False})
    ).status_code == 200
    client.cookies.clear()
    assert student_cookie is not None
    client.cookies.set("solfeo_session", student_cookie)
    assert (await client.get("/api/auth/me")).status_code == 401
    assert (await login(client, "student")).json()["error"] == "INVALID_CREDENTIALS"


async def test_reset_requires_password_change_and_revokes_old_sessions(
    client: httpx.AsyncClient,
) -> None:
    await login(client)
    identifier = await create_user(client)
    manager_cookie = client.cookies.get("solfeo_session")
    manager_csrf = client.headers["X-CSRF-Token"]
    client.cookies.clear()
    await login(client, "student")
    old_cookie = client.cookies.get("solfeo_session")
    client.cookies.clear()
    assert manager_cookie is not None
    client.cookies.set("solfeo_session", manager_cookie)
    client.headers["X-CSRF-Token"] = manager_csrf
    replacement = "replacement-long-password"
    assert (
        await client.post(
            f"/api/users/{identifier}/password",
            json={"password": replacement, "must_change_password": True},
        )
    ).status_code == 200
    client.cookies.clear()
    assert old_cookie is not None
    client.cookies.set("solfeo_session", old_cookie)
    assert (await client.get("/api/auth/me")).status_code == 401
    assert (await login(client, "student")).status_code == 401
    assert (await login(client, "student", replacement)).json()["user"][
        "must_change_password"
    ]
    assert (
        await client.patch(
            "/api/settings", json={"ui_language": "ru", "note_naming": "letters"}
        )
    ).json()["error"] == "PASSWORD_CHANGE_REQUIRED"
    response = await client.put(
        "/api/auth/password",
        json={"current_password": replacement, "new_password": PASSWORD},
    )
    assert (
        response.status_code == 200
        and not response.json()["user"]["must_change_password"]
    )
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    assert (
        await client.patch(
            "/api/settings", json={"ui_language": "ru", "note_naming": "letters"}
        )
    ).status_code == 200


async def test_login_throttle_is_persistent_and_unknown_users_are_generic(
    client: httpx.AsyncClient, settings: Settings
) -> None:
    for _ in range(settings.login_username_limit):
        response = await login(client, "unknown", "wrong")
        assert response.status_code == 401 and response.json() == {
            "error": "INVALID_CREDENTIALS"
        }
    response = await login(client, "unknown", "wrong")
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0


async def test_expired_sessions_and_emergency_restart_are_revoked(
    client: httpx.AsyncClient, database: Database, settings: Settings
) -> None:
    await login(client)
    with database.session() as session, session.begin():
        stored = session.scalar(select(LoginSession))
        assert stored is not None
        stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert (await client.get("/api/auth/me")).status_code == 401
    await login(client)
    sync_emergency(database, settings)
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_manager_validation_duplicate_username_and_emergency_protection(
    client: httpx.AsyncClient,
) -> None:
    await login(client)
    await create_user(client)
    response = await client.post(
        "/api/users",
        json={
            "username": "STUDENT",
            "password": PASSWORD,
            "first_name": "First",
            "last_name": "Last",
            "role": "student",
        },
    )
    assert response.status_code == 409 and response.json()["error"] == "USERNAME_TAKEN"
    me = (await client.get("/api/auth/me")).json()["user"]
    assert (
        await client.patch(f"/api/users/{me['id']}", json={"is_active": False})
    ).status_code == 403
    assert (
        await client.post(
            f"/api/users/{me['id']}/password", json={"password": PASSWORD}
        )
    ).status_code == 403
    response = await client.patch(
        "/api/settings", json={"ui_language": "xx", "note_naming": "letters"}
    )
    assert response.status_code == 422 and response.json() == {
        "error": "VALIDATION_ERROR"
    }
    assert "password_hash" not in (await client.get("/api/users")).text


@pytest.mark.parametrize(
    "changes",
    [
        {
            "emergency_manager_username": "recovery",
            "emergency_manager_password": SecretStr(""),
        },
        {
            "emergency_manager_username": "",
            "emergency_manager_password": SecretStr(PASSWORD),
        },
        {
            "emergency_manager_username": "bad user",
            "emergency_manager_password": SecretStr(PASSWORD),
        },
        {
            "emergency_manager_username": "recovery",
            "emergency_manager_password": SecretStr("short"),
        },
        {"auth_allowed_origins": ["*"]},
        {"auth_allowed_origins": ["https://example.test/path"]},
    ],
)
def test_invalid_auth_configuration_fails_explicitly(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"DATABASE_PASSWORD": "synthetic-password", **changes})


async def test_ip_budget_ignores_username_and_untrusted_forwarded_headers(
    database: Database, settings: Settings
) -> None:
    app = create_app(settings.model_copy(update={"login_ip_limit": 2}))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=ORIGIN,
            headers={"Origin": ORIGIN},
        ) as client:
            for index in range(2):
                response = await client.post(
                    "/api/auth/login",
                    json={"username": f"unknown{index}", "password": "wrong"},
                    headers={"X-Forwarded-For": f"192.0.2.{index}"},
                )
                assert response.status_code == 401
            assert (await login(client, "another", "wrong")).status_code == 429


async def test_manager_can_reactivate_and_edit_other_users_but_not_demote_self(
    client: httpx.AsyncClient,
) -> None:
    await login(client)
    identifier = await create_user(client, "normal-manager", "manager")
    response = await client.patch(
        f"/api/users/{identifier}", json={"first_name": "Updated", "is_active": False}
    )
    assert response.json()["first_name"] == "Updated"
    assert (
        await client.patch(f"/api/users/{identifier}", json={"is_active": True})
    ).json()["is_active"]
    client.cookies.clear()
    await login(client, "normal-manager")
    assert (
        await client.patch(f"/api/users/{identifier}", json={"role": "student"})
    ).json()["error"] == "SELF_CHANGE_FORBIDDEN"


async def test_emergency_username_change_retires_previous_account(
    client: httpx.AsyncClient, database: Database, settings: Settings
) -> None:
    await login(client)
    sync_emergency(
        database,
        settings.model_copy(
            update={"emergency_manager_username": "replacement-manager"}
        ),
    )
    assert (await client.get("/api/auth/me")).status_code == 401
    with database.session() as session:
        old = session.scalar(select(User).where(User.username == "recovery"))
        assert old is not None and not old.is_active and not old.is_emergency
        replacement = session.scalar(select(User).where(User.is_emergency))
        assert replacement is not None and replacement.username == "replacement-manager"


async def test_current_password_required_and_all_sessions_revoked_on_change(
    client: httpx.AsyncClient, database: Database
) -> None:
    await login(client)
    await create_user(client)
    client.cookies.clear()
    await login(client, "student")
    original = client.cookies.get("solfeo_session")
    client.cookies.clear()
    await login(client, "student")
    response = await client.put(
        "/api/auth/password",
        json={
            "current_password": "incorrect",
            "new_password": "different-long-password",
        },
    )
    assert response.status_code == 400
    response = await client.put(
        "/api/auth/password",
        json={"current_password": PASSWORD, "new_password": "different-long-password"},
    )
    assert response.status_code == 200
    assert (await client.get("/api/auth/me")).status_code == 200
    client.cookies.clear()
    assert original is not None
    client.cookies.set("solfeo_session", original)
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_missing_origin_and_foreign_csrf_are_rejected(
    client: httpx.AsyncClient,
) -> None:
    del client.headers["Origin"]
    assert (await login(client)).status_code == 403
    client.headers["Origin"] = ORIGIN
    await login(client)
    client.headers["X-CSRF-Token"] = "foreign-csrf"
    assert (await client.post("/api/auth/logout")).status_code == 403
    assert (await client.get("/api/auth/me")).status_code == 200


async def test_non_ascii_csrf_is_rejected_without_a_server_error(
    client: httpx.AsyncClient,
) -> None:
    await login(client)
    response = await client.post("/api/auth/logout", headers={b"X-CSRF-Token": b"\xff"})
    assert response.status_code == 403
    assert response.json() == {"error": "CSRF_FAILED"}
