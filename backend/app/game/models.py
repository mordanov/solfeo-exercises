from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    avatar_animal: Mapped[str | None] = mapped_column(String(20), nullable=True)
    custom_avatar_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "custom_avatars.id",
            use_alter=True,
            name="fk_players_custom_avatar_id_custom_avatars",
        ),
        nullable=True,
    )
    xp: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint("length(name) >= 1", name="ck_players_name_length"),
        Index("uq_players_account_id_name", "account_id", "name", unique=True),
    )


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index(
            "uq_seasons_player_id_active",
            "player_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
    )


class Round(Base):
    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id"), nullable=False
    )
    season_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("seasons.id"), nullable=False
    )
    difficulty: Mapped[str] = mapped_column(String(6), nullable=False)
    note_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    note_naming: Mapped[str] = mapped_column(String(7), nullable=False)
    show_sound_hint: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    show_correct_answer: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    rules_version: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("1")
    )
    status: Mapped[str] = mapped_column(
        String(9), nullable=False, server_default=text("'active'")
    )
    score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    correct_count: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "difficulty IN ('easy','medium','hard')", name="ck_rounds_difficulty"
        ),
        CheckConstraint("note_count IN (1,2,3,4)", name="ck_rounds_note_count"),
        CheckConstraint(
            "status IN ('active','completed','expired')", name="ck_rounds_status"
        ),
        Index(
            "ix_rounds_player_season_diff_count",
            "player_id",
            "season_id",
            "difficulty",
            "note_count",
        ),
    )


class TaskAttempt(Base):
    __tablename__ = "task_attempts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    round_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("rounds.id"), nullable=False
    )
    season_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("seasons.id"), nullable=False
    )
    task_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    clef: Mapped[str] = mapped_column(String(6), nullable=False)
    expected_notes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    given_notes: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    timed_out: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    __table_args__ = (
        CheckConstraint("clef IN ('treble','bass')", name="ck_task_attempts_clef"),
        Index("uq_task_attempts_round_task", "round_id", "task_index", unique=True),
        Index("ix_task_attempts_season_player", "season_id", "round_id"),
    )


class TrophyAwarded(Base):
    __tablename__ = "trophies_awarded"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id"), nullable=False
    )
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "uq_trophies_awarded_player_threshold",
            "player_id",
            "threshold",
            unique=True,
        ),
    )


class CustomAvatar(Base):
    __tablename__ = "custom_avatars"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(7), nullable=False, server_default=text("'pending'")
    )
    base_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    happy_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    sad_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','ready','failed')", name="ck_custom_avatars_status"
        ),
    )


class AvatarGenerationLog(Base):
    __tablename__ = "avatar_generation_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    flagged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    billable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "ix_avatar_generation_log_account_created",
            "account_id",
            "created_at",
        ),
    )
