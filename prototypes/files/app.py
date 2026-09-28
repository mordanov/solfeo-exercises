import secrets
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="FILES_", extra="forbid"
    )

    username: str = Field(default="prototype", pattern=r"^[A-Za-z0-9._-]+$")
    password: SecretStr = Field(min_length=32)
    port: int = Field(default=18085, ge=1024, le=65535)
    media_dir: Path = Path("media")
    output_dir: Path = Path("output")
    source_audio: Path = Path("../../examples/ejercicio_1.opus")
    ffmpeg_timeout_seconds: int = Field(default=60, gt=0)
    audio_bitrate: str = Field(default="128k", pattern=r"^[1-9][0-9]*k$")

    @field_validator("password")
    @classmethod
    def require_generated_password(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value() == "GENERATE_A_RANDOM_LOCAL_TOKEN_BEFORE_USE":
            raise ValueError("Generate a random local credential before running")
        return value


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    basic = HTTPBasic(auto_error=False)
    challenge = {"WWW-Authenticate": 'Basic realm="files-prototype", charset="UTF-8"'}

    def require_access(
        credentials: Annotated[HTTPBasicCredentials | None, Depends(basic)],
    ) -> None:
        if credentials is None:
            raise HTTPException(status_code=401, headers=challenge)
        valid_username = secrets.compare_digest(
            credentials.username.encode(), config.username.encode()
        )
        valid_password = secrets.compare_digest(
            credentials.password.encode(), config.password.get_secret_value().encode()
        )
        if not (valid_username and valid_password):
            raise HTTPException(status_code=401, headers=challenge)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = (
            "AUTH_REQUIRED"
            if exc.status_code == 401
            else "NOT_FOUND"
            if exc.status_code == 404
            else "HTTP_ERROR"
        )
        return JSONResponse(
            {"error": code},
            status_code=exc.status_code,
            headers=challenge if exc.status_code == 401 else exc.headers,
        )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.api_route(
        "/api/audio", methods=["GET", "HEAD"], dependencies=[Depends(require_access)]
    )
    def audio() -> Response:
        return Response(
            headers={
                "X-Accel-Redirect": "/_protected/sample.m4a",
                "Cache-Control": "private, no-store",
            },
            media_type="audio/mp4",
        )

    return app
