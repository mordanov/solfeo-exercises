from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_prefix="API_",
        extra="ignore",
        hide_input_in_errors=True,
        populate_by_name=True,
    )

    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=18081, ge=1, le=65535)
    log_level: Literal["critical", "error", "warning", "info", "debug", "trace"] = (
        "info"
    )

    database_host: str = Field(
        default="127.0.0.1", min_length=1, validation_alias="DATABASE_HOST"
    )
    database_port: int = Field(
        default=15432, ge=1, le=65535, validation_alias="DATABASE_PORT"
    )
    database_name: str = Field(
        default="solfeo", min_length=1, validation_alias="DATABASE_NAME"
    )
    database_user: str = Field(
        default="solfeo", min_length=1, validation_alias="DATABASE_USER"
    )
    database_password: SecretStr = Field(validation_alias="DATABASE_PASSWORD")
    database_pool_size: int = Field(
        default=5, ge=1, validation_alias="DATABASE_POOL_SIZE"
    )
    database_max_overflow: int = Field(
        default=5, ge=0, validation_alias="DATABASE_MAX_OVERFLOW"
    )
    database_pool_timeout_seconds: int = Field(
        default=10, ge=1, validation_alias="DATABASE_POOL_TIMEOUT_SECONDS"
    )
    database_connect_timeout_seconds: int = Field(
        default=5, ge=1, validation_alias="DATABASE_CONNECT_TIMEOUT_SECONDS"
    )

    @field_validator("database_password")
    @classmethod
    def require_database_password(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("DATABASE_PASSWORD must not be empty")
        return value

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.database_user,
            password=self.database_password.get_secret_value(),
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        )
