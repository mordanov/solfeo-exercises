from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app import Settings, create_app

PASSWORD = "synthetic-test-credential-not-for-use"
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(username="tester", password=SecretStr(PASSWORD))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings)),
        base_url="http://test",
    ) as client:
        yield client


async def test_health_is_public(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/health")).json() == {"status": "ok"}


@pytest.mark.parametrize("method", ["GET", "HEAD"])
async def test_anonymous_cannot_access_audio(
    client: httpx.AsyncClient, method: str
) -> None:
    response = await client.request(method, "/api/audio")
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Basic ")
    assert "x-accel-redirect" not in response.headers


@pytest.mark.parametrize(
    "authorization", ["Bearer invalid", "Basic !!!", "Basic dXNlcg=="]
)
async def test_malformed_auth_uses_error_code(
    client: httpx.AsyncClient, authorization: str
) -> None:
    response = await client.get("/api/audio", headers={"Authorization": authorization})
    assert response.status_code == 401
    assert response.json() == {"error": "AUTH_REQUIRED"}


@pytest.mark.parametrize("auth", [("tester", "wrong"), ("wrong", PASSWORD)])
async def test_incorrect_credentials_are_rejected(
    client: httpx.AsyncClient, auth: tuple[str, str]
) -> None:
    response = await client.get("/api/audio", auth=auth)
    assert response.status_code == 401
    assert "x-accel-redirect" not in response.headers


@pytest.mark.parametrize("method", ["GET", "HEAD"])
async def test_authorized_backend_returns_only_internal_redirect(
    client: httpx.AsyncClient, method: str
) -> None:
    response = await client.request(
        method, "/api/audio", auth=("tester", PASSWORD), headers={"Range": "bytes=0-1"}
    )
    assert response.status_code == 200
    assert response.headers["x-accel-redirect"] == "/_protected/sample.m4a"
    assert response.headers["content-type"] == "audio/mp4"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.content == b""


async def test_client_cannot_choose_the_internal_path(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get(
        "/api/audio?path=/etc/passwd",
        auth=("tester", PASSWORD),
        headers={"X-Accel-Redirect": "/etc/passwd"},
    )
    assert response.headers["x-accel-redirect"] == "/_protected/sample.m4a"


async def test_authentication_does_not_depend_on_media_directory(
    client: httpx.AsyncClient,
) -> None:
    # The backend has no media mount; nginx alone reads the file.
    response = await client.get("/api/audio", auth=("tester", PASSWORD))
    assert response.status_code == 200
    assert response.content == b""


def test_config_requires_a_nontrivial_test_password(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FILES_PASSWORD", raising=False)
    with pytest.raises(ValidationError):
        Settings()
    with pytest.raises(ValidationError):
        Settings(password=SecretStr("short"))


def test_config_from_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text(f"FILES_USERNAME=example\nFILES_PASSWORD={PASSWORD}\n")
    settings = Settings()
    assert settings.username == "example"
    assert settings.password.get_secret_value() == PASSWORD


def test_placeholder_password_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Generate"):
        Settings(password=SecretStr("GENERATE_A_RANDOM_LOCAL_TOKEN_BEFORE_USE"))
