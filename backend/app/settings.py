import re
from ipaddress import ip_address
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from app.appearance import ColorScheme, UiFont


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
    media_root: Path = Field(default=Path("/app/media"), validation_alias="MEDIA_ROOT")
    image_max_bytes: int = Field(
        default=20971520, ge=1, validation_alias="IMAGE_MAX_BYTES"
    )
    audio_max_bytes: int = Field(
        default=52428800, ge=1, validation_alias="AUDIO_MAX_BYTES"
    )
    upload_max_bytes: int = Field(
        default=74448896, ge=1024, validation_alias="UPLOAD_MAX_BYTES"
    )
    image_max_pixels: int = Field(
        default=40000000, ge=1, validation_alias="IMAGE_MAX_PIXELS"
    )
    audio_max_seconds: int = Field(
        default=1800, ge=1, validation_alias="AUDIO_MAX_SECONDS"
    )
    media_timeout_seconds: int = Field(
        default=120, ge=1, validation_alias="MEDIA_TIMEOUT_SECONDS"
    )
    audio_bitrate_kbps: int = Field(
        default=128, ge=32, le=320, validation_alias="AUDIO_BITRATE_KBPS"
    )
    ffmpeg_binary: str = Field(default="ffmpeg", validation_alias="FFMPEG_BINARY")
    ffprobe_binary: str = Field(default="ffprobe", validation_alias="FFPROBE_BINARY")
    file_binary: str = Field(default="file", validation_alias="FILE_BINARY")
    openai_api_key: SecretStr = Field(
        default=SecretStr(""), validation_alias="OPENAI_API_KEY"
    )
    spoken_model: str = Field(
        default="gpt-4o-mini-tts", validation_alias="SPOKEN_MODEL"
    )
    spoken_voice: str = Field(default="coral", validation_alias="SPOKEN_VOICE")
    spoken_timeout_seconds: int = Field(
        default=60, ge=1, le=300, validation_alias="SPOKEN_TIMEOUT_SECONDS"
    )
    spoken_max_clip_bytes: int = Field(
        default=2097152, ge=1024, le=10485760, validation_alias="SPOKEN_MAX_CLIP_BYTES"
    )
    spoken_max_clip_seconds: int = Field(
        default=5, ge=1, le=30, validation_alias="SPOKEN_MAX_CLIP_SECONDS"
    )
    spoken_output: Path = Field(
        default=Path("frontend/public/solfege"), validation_alias="SPOKEN_OUTPUT"
    )
    omr_enabled: bool = Field(default=True, validation_alias="OMR_ENABLED")
    omr_detect_movements: bool = Field(
        default=False, validation_alias="OMR_DETECT_MOVEMENTS"
    )
    omr_faint_mean_coeff: float = Field(
        default=0.9,
        gt=0,
        le=1.5,
        allow_inf_nan=False,
        validation_alias="OMR_FAINT_MEAN_COEFF",
    )
    omr_binary: str = Field(
        default="/opt/audiveris/bin/Audiveris", validation_alias="OMR_BINARY"
    )
    omr_java_home: Path = Field(
        default=Path("/opt/java/openjdk"), validation_alias="OMR_JAVA_HOME"
    )
    omr_tessdata: Path = Field(
        default=Path("/usr/share/tesseract-ocr/5/tessdata"),
        validation_alias="OMR_TESSDATA",
    )
    omr_timeout_seconds: int = Field(
        default=300, ge=1, le=900, validation_alias="OMR_TIMEOUT_SECONDS"
    )
    omr_lease_seconds: int = Field(
        default=600, ge=60, le=1800, validation_alias="OMR_LEASE_SECONDS"
    )
    omr_poll_seconds: int = Field(
        default=2, ge=1, le=60, validation_alias="OMR_POLL_SECONDS"
    )
    omr_retry_seconds: int = Field(
        default=30, ge=1, le=600, validation_alias="OMR_RETRY_SECONDS"
    )
    omr_max_attempts: int = Field(
        default=3, ge=1, le=10, validation_alias="OMR_MAX_ATTEMPTS"
    )
    omr_max_xml_bytes: int = Field(
        default=5242880, ge=1024, le=20971520, validation_alias="OMR_MAX_XML_BYTES"
    )
    omr_java_heap_mb: int = Field(
        default=512, ge=128, le=4096, validation_alias="OMR_JAVA_HEAP_MB"
    )
    omr_health_file: Path = Field(
        default=Path("/tmp/omr-ready"), validation_alias="OMR_HEALTH_FILE"
    )
    omr_health_seconds: int = Field(
        default=600, ge=60, le=1800, validation_alias="OMR_HEALTH_SECONDS"
    )
    telegram_token: SecretStr = Field(
        default=SecretStr(""), validation_alias="TELEGRAM_TOKEN"
    )
    telegram_health_file: Path = Field(
        default=Path("/tmp/telegram-ready"), validation_alias="TELEGRAM_HEALTH_FILE"
    )
    telegram_bot_username: str = Field(
        default="solfeo_exercises_bot",
        pattern=r"^[A-Za-z0-9_]{5,32}$",
        validation_alias="TELEGRAM_BOT_USERNAME",
    )
    telegram_link_seconds: int = Field(
        default=600, ge=60, le=3600, validation_alias="TELEGRAM_LINK_SECONDS"
    )
    telegram_max_file_bytes: int = Field(
        default=20000000, ge=1, le=20000000, validation_alias="TELEGRAM_MAX_FILE_BYTES"
    )
    telegram_poll_seconds: int = Field(
        default=25, ge=1, le=50, validation_alias="TELEGRAM_POLL_SECONDS"
    )
    telegram_http_seconds: int = Field(
        default=15, ge=1, le=60, validation_alias="TELEGRAM_HTTP_SECONDS"
    )
    telegram_download_seconds: int = Field(
        default=90, ge=1, le=300, validation_alias="TELEGRAM_DOWNLOAD_SECONDS"
    )
    telegram_retry_seconds: int = Field(
        default=5, ge=1, le=300, validation_alias="TELEGRAM_RETRY_SECONDS"
    )
    telegram_max_attempts: int = Field(
        default=3, ge=1, le=10, validation_alias="TELEGRAM_MAX_ATTEMPTS"
    )
    telegram_health_seconds: int = Field(
        default=600, ge=60, le=3600, validation_alias="TELEGRAM_HEALTH_SECONDS"
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
        default=8, ge=8, le=128, validation_alias="PASSWORD_MIN_LENGTH"
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
    default_light_scheme: ColorScheme = Field(
        default="classic", validation_alias="DEFAULT_LIGHT_SCHEME"
    )
    default_dark_scheme: ColorScheme = Field(
        default="classic", validation_alias="DEFAULT_DARK_SCHEME"
    )
    default_ui_font: UiFont = Field(
        default="roboto", validation_alias="DEFAULT_UI_FONT"
    )
    default_ui_font_size: int = Field(
        default=16, validation_alias="DEFAULT_UI_FONT_SIZE"
    )

    @field_validator("default_ui_font_size")
    @classmethod
    def supported_font_size(cls, value: int) -> int:
        if value not in (16, 18, 20):
            raise ValueError("INVALID_UI_FONT_SIZE")
        return value

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
    avatar_image_model: str = Field(
        default="gpt-image-1-mini", validation_alias="AVATAR_IMAGE_MODEL"
    )
    avatar_image_quality: Literal["low", "medium", "high"] = Field(
        default="low", validation_alias="AVATAR_IMAGE_QUALITY"
    )
    avatar_gen_timeout_seconds: int = Field(
        default=180, ge=30, le=600, validation_alias="AVATAR_GEN_TIMEOUT_SECONDS"
    )
    avatar_gen_estimated_seconds: int = Field(
        default=120, ge=1, validation_alias="AVATAR_GEN_ESTIMATED_SECONDS"
    )
    avatar_gen_max_image_bytes: int = Field(
        default=16777216, ge=1024, validation_alias="AVATAR_GEN_MAX_IMAGE_BYTES"
    )
    avatar_gen_poll_seconds: float = Field(
        default=2, ge=0.1, validation_alias="AVATAR_GEN_POLL_SECONDS"
    )
    avatar_gen_daily_limit: int = Field(
        default=3, ge=1, validation_alias="AVATAR_GEN_DAILY_LIMIT"
    )
    avatar_gen_grace_ms: int = Field(
        default=500, ge=0, validation_alias="AVATAR_GEN_GRACE_MS"
    )
    avatar_round_expire_s: int = Field(
        default=3600, ge=60, validation_alias="AVATAR_ROUND_EXPIRE_S"
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
    def validate_auth_transport(self) -> Self:
        for origin in self.auth_allowed_origins:
            parsed = urlsplit(origin)
            if parsed.scheme == "https":
                if not self.session_cookie_secure:
                    raise ValueError("HTTPS origins require Secure session cookies")
            elif parsed.hostname != "localhost":
                try:
                    local = ip_address(parsed.hostname or "").is_loopback
                except ValueError:
                    local = False
                if not local:
                    raise ValueError("HTTP authentication is restricted to loopback")
        return self

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

    @model_validator(mode="after")
    def validate_omr_timeouts(self) -> Self:
        if self.omr_lease_seconds <= self.omr_timeout_seconds + 30:
            raise ValueError(
                "OMR lease must exceed engine timeout by more than 30 seconds"
            )
        if self.omr_health_seconds <= self.omr_timeout_seconds:
            raise ValueError("OMR health age must exceed engine timeout")
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
