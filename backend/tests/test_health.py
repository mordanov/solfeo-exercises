from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from app.main import create_app
from app.settings import Settings

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app()),
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
    settings = Settings(_env_file=config)
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
        Settings(port=port, _env_file=None)
