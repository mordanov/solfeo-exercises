from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    MetaData,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.appearance import ColorScheme, UiFont


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('manager', 'student')", name="role"),
        CheckConstraint("ui_language IN ('ru', 'en', 'es')", name="ui_language"),
        CheckConstraint("note_naming IN ('letters', 'solfege')", name="note_naming"),
        CheckConstraint(
            "light_scheme IN ('classic', 'forest', 'warm', 'plum')", name="light_scheme"
        ),
        CheckConstraint(
            "dark_scheme IN ('classic', 'forest', 'warm', 'plum')", name="dark_scheme"
        ),
        CheckConstraint("ui_font IN ('roboto', 'system', 'serif')", name="ui_font"),
        CheckConstraint("ui_font_size IN (16, 18, 20)", name="ui_font_size"),
        CheckConstraint("username = lower(username)", name="canonical_username"),
        Index(
            "uq_users_emergency",
            "is_emergency",
            unique=True,
            postgresql_where=text("is_emergency"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(10))
    password_hash: Mapped[str] = mapped_column(String(256))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    is_emergency: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    ui_language: Mapped[str] = mapped_column(
        String(2), default="en", server_default="en"
    )
    note_naming: Mapped[str] = mapped_column(
        String(7), default="letters", server_default="letters"
    )
    light_scheme: Mapped[ColorScheme] = mapped_column(
        String(8), default="classic", server_default="classic"
    )
    dark_scheme: Mapped[ColorScheme] = mapped_column(
        String(8), default="classic", server_default="classic"
    )
    ui_font: Mapped[UiFont] = mapped_column(
        String(8), default="roboto", server_default="roboto"
    )
    ui_font_size: Mapped[int] = mapped_column(default=16, server_default="16")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LoginLimit(Base):
    __tablename__ = "login_limits"
    key: Mapped[str] = mapped_column(String(67), primary_key=True)
    attempts: Mapped[int]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class MediaFile(Base):
    __tablename__ = "media_files"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="size"),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds > 0", name="duration"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(50), unique=True)
    mime_type: Mapped[str] = mapped_column(String(50))
    size_bytes: Mapped[int]
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint(
            "image_id IS NOT NULL OR audio_id IS NOT NULL", name="media_required"
        ),
        CheckConstraint("position >= 0", name="position"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    category: Mapped[str | None] = mapped_column(String(100))
    position: Mapped[int] = mapped_column(index=True)
    image_id: Mapped[str | None] = mapped_column(ForeignKey("media_files.id"))
    audio_id: Mapped[str | None] = mapped_column(ForeignKey("media_files.id"))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StudentProgress(Base):
    __tablename__ = "student_progress"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    next_exercise_id: Mapped[int | None] = mapped_column(ForeignKey("exercises.id"))
    last_random_id: Mapped[int | None] = mapped_column(ForeignKey("exercises.id"))


class ListeningSession(Base):
    __tablename__ = "listening_sessions"
    __table_args__ = (
        CheckConstraint("audio_duration_sec > 0", name="duration"),
        CheckConstraint(
            "max_position_sec >= 0 AND max_position_sec <= audio_duration_sec",
            name="position",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    audio_id: Mapped[str] = mapped_column(ForeignKey("media_files.id"))
    exercise_title: Mapped[str] = mapped_column(String(200))
    session_id: Mapped[str] = mapped_column(String(36), unique=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_position_sec: Mapped[float] = mapped_column(Float, default=0)
    audio_duration_sec: Mapped[float] = mapped_column(Float)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)


class TelegramLink(Base):
    __tablename__ = "telegram_links"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    sender_id: Mapped[int] = mapped_column(BigInteger, unique=True)


class TelegramLinkCode(Base):
    __tablename__ = "telegram_link_codes"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TelegramUpdate(Base):
    __tablename__ = "telegram_updates"
    __table_args__ = (
        CheckConstraint(
            "status IN ('message','pending','ready','failed','applied','discarded')",
            name="status",
        ),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    file_id: Mapped[str | None] = mapped_column(String(512))
    title: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(2), default="en")
    status: Mapped[str] = mapped_column(String(10), index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(64))
    media_id: Mapped[str | None] = mapped_column(ForeignKey("media_files.id"))
    exercise_id: Mapped[int | None] = mapped_column(ForeignKey("exercises.id"))
    applied_request: Mapped[str | None] = mapped_column(String(64))
    reply_code: Mapped[str] = mapped_column(String(32), default="received")
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TelegramState(Base):
    __tablename__ = "telegram_state"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    bot_id: Mapped[int] = mapped_column(BigInteger)
    next_offset: Mapped[int] = mapped_column(BigInteger, default=0)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OmrJob(Base):
    __tablename__ = "omr_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN "
            "('pending','processing','needs_review','approved','rejected','failed')",
            name="status",
        ),
        Index(
            "uq_omr_jobs_current",
            "exercise_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    image_id: Mapped[str] = mapped_column(ForeignKey("media_files.id"))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[str | None] = mapped_column(String(36))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(64))
    score_filename: Mapped[str | None] = mapped_column(String(64))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


import app.game.models as _game_models  # noqa: E402, F401
