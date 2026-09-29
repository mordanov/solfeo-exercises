import re
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
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
    forwarded_allow_ips: str = "127.0.0.1"

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
    alembic_version_schema: str = Field(
        default="public",
        pattern=r"^[a-z_][a-z0-9_]*$",
        max_length=63,
        validation_alias="ALEMBIC_VERSION_SCHEMA",
    )
    auth_allowed_origins: list[str] = Field(
        default=["http://127.0.0.1:18080", "http://localhost:18080"],
        validation_alias="AUTH_ALLOWED_ORIGINS",
    )
    session_cookie_secure: bool = Field(
        default=True, validation_alias="SESSION_COOKIE_SECURE"
    )
    session_lifetime_days: int = Field(
        default=90, ge=1, le=365, validation_alias="SESSION_LIFETIME_DAYS"
    )
    password_min_length: int = Field(
        default=12, ge=8, le=128, validation_alias="PASSWORD_MIN_LENGTH"
    )
    login_username_limit: int = Field(
        default=5, ge=1, le=100, validation_alias="LOGIN_USERNAME_LIMIT"
    )
    login_ip_limit: int = Field(
        default=30, ge=1, le=1000, validation_alias="LOGIN_IP_LIMIT"
    )
    login_window_seconds: int = Field(
        default=900, ge=1, le=86400, validation_alias="LOGIN_WINDOW_SECONDS"
    )
    default_language: Literal["ru", "en", "es"] = Field(
        default="en", validation_alias="DEFAULT_LANGUAGE"
    )
    emergency_manager_username: str = Field(
        default="", validation_alias="EMERGENCY_MANAGER_USERNAME"
    )
    emergency_manager_password: SecretStr = Field(
        default=SecretStr(""), validation_alias="EMERGENCY_MANAGER_PASSWORD"
    )
    emergency_manager_first_name: str = Field(
        default="Emergency",
        min_length=1,
        max_length=100,
        validation_alias="EMERGENCY_MANAGER_FIRST_NAME",
    )
    emergency_manager_last_name: str = Field(
        default="Manager",
        min_length=1,
        max_length=100,
        validation_alias="EMERGENCY_MANAGER_LAST_NAME",
    )

    @field_validator("auth_allowed_origins")
    @classmethod
    def validate_origins(cls, origins: list[str]) -> list[str]:
        if not origins:
            raise ValueError("AUTH_ALLOWED_ORIGINS must not be empty")
        for origin in origins:
            parsed = urlsplit(origin)
            port = parsed.port
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
                or port == 0
            ):
                raise ValueError(
                    "AUTH_ALLOWED_ORIGINS must contain plain HTTP(S) origins"
                )
        return origins

    @model_validator(mode="after")
    def validate_emergency(self) -> Self:
        username = self.emergency_manager_username
        password = self.emergency_manager_password.get_secret_value()
        if bool(username) != bool(password):
            raise ValueError("Set both emergency manager credentials or neither")
        if username and (
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,63}", username)
            or not self.password_min_length <= len(password) <= 256
        ):
            raise ValueError("Invalid emergency manager credentials")
        return self

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
