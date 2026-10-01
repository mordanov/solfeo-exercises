import logging
import socket
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy.exc import OperationalError

from app.logging import JsonFormatter
from app.main import create_app
from app.settings import Settings

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(
            app=create_app(
                Settings(
                    _env_file=None,
                    database_password=SecretStr("synthetic-test-password"),
                )
            )
        ),
        base_url="http://test",
    ) as client:
        yield client


async def test_health_is_public_and_not_cached(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-type"] == "application/json"
    assert "set-cookie" not in response.headers


async def test_head_has_no_body(client: httpx.AsyncClient) -> None:
    response = await client.head("/api/health")
    assert response.status_code == 200
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("path", ["/api/missing", "/docs", "/redoc", "/openapi.json"])
async def test_unknown_routes_return_codes(
    client: httpx.AsyncClient, path: str
) -> None:
    response = await client.get(path)
    assert response.status_code == 404
    assert response.json() == {"error": "NOT_FOUND"}


async def test_health_post_is_not_a_success(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/health")
    assert response.status_code == 405
    assert response.json() == {"error": "METHOD_NOT_ALLOWED"}
    assert "GET" in response.headers["allow"]


def test_settings_read_dotenv(tmp_path: Path) -> None:
    config = tmp_path / ".env"
    config.write_text("API_HOST=127.0.0.1\nAPI_PORT=18777\nAPI_LOG_LEVEL=warning\n")
    settings = Settings(
        _env_file=config, database_password=SecretStr("synthetic-test-password")
    )
    assert settings.host == "127.0.0.1"
    assert settings.port == 18777
    assert settings.log_level == "warning"


def test_default_dotenv_path_is_the_repository_root() -> None:
    assert Settings.model_config["env_file"] == (
        Path(__file__).resolve().parents[2] / ".env"
    )


@pytest.mark.parametrize("port", [0, -1, 65536])
def test_settings_reject_invalid_port(port: int) -> None:
    with pytest.raises(ValidationError):
        Settings(
            port=port,
            _env_file=None,
            database_password=SecretStr("synthetic-test-password"),
        )


@pytest.mark.parametrize(
    "origins,secure",
    [
        (["https://example.test"], False),
        (["http://example.test"], True),
        (["http://example.test"], False),
    ],
)
def test_settings_reject_insecure_public_authentication(
    origins: list[str], secure: bool
) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_password=SecretStr("synthetic-password"),
            auth_allowed_origins=origins,
            session_cookie_secure=secure,
        )


@pytest.mark.parametrize(
    "path,status,route",
    [
        ("/api/health?token=private", 200, "/api/health"),
        ("/api/private-token?password=secret", 404, "unmatched"),
    ],
)
async def test_request_logs_exclude_query_and_unmatched_paths(
    client: httpx.AsyncClient,
    caplog: pytest.LogCaptureFixture,
    path: str,
    status: int,
    route: str,
) -> None:
    with caplog.at_level(logging.INFO, logger="app.requests"):
        await client.get(path, headers={"Cookie": "secret-cookie"})
    records = [record for record in caplog.records if record.message == "HTTP_REQUEST"]
    assert len(records) == 1
    assert records[0].__dict__["route"] == route
    assert records[0].__dict__["status"] == status
    assert "private-token" not in caplog.text
    assert "secret-cookie" not in caplog.text


async def test_startup_failure_has_explicit_safe_diagnostics(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with socket.socket() as unavailable:
        unavailable.bind(("127.0.0.1", 0))
        settings = Settings(
            _env_file=None,
            database_password=SecretStr("unused-private-password"),
            database_host="127.0.0.1",
            database_port=unavailable.getsockname()[1],
        )
        app = create_app(settings)
        with caplog.at_level(logging.ERROR, logger="app.main"):
            with pytest.raises(OperationalError):
                async with app.router.lifespan_context(app):
                    raise AssertionError("Startup must fail before serving")
    records = [
        record
        for record in caplog.records
        if record.message == "BACKEND_LIFESPAN_FAILED"
    ]
    assert len(records) == 1
    assert records[0].exc_info and records[0].exc_info[0] is OperationalError
    serialized = JsonFormatter().format(records[0])
    assert '"error_type":"OperationalError"' in serialized
    assert "unused-private-password" not in serialized
