"""guess the note game tables

Revision ID: 0008_game
Revises: 0007_appearance
Create Date: 2026-10-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_game"
down_revision = "0007_appearance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "players",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(20), nullable=False),
        sa.Column("avatar_animal", sa.String(20), nullable=True),
        sa.Column("custom_avatar_id", sa.BigInteger(), nullable=True),
        sa.Column("xp", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("length(name) >= 1", name=op.f("ck_players_name_length")),
        sa.ForeignKeyConstraint(
            ["account_id"], ["users.id"], name=op.f("fk_players_account_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_players")),
    )
    op.create_index(
        "uq_players_account_id_name", "players", ["account_id", "name"], unique=True
    )

    op.create_table(
        "custom_avatars",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(7),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("base_path", sa.Text(), nullable=True),
        sa.Column("happy_path", sa.Text(), nullable=True),
        sa.Column("sad_path", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','ready','failed')",
            name=op.f("ck_custom_avatars_status"),
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["users.id"],
            name=op.f("fk_custom_avatars_account_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name=op.f("fk_custom_avatars_player_id_players"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_custom_avatars")),
    )

    # Deferred FK: players.custom_avatar_id → custom_avatars.id (circular reference)
    op.create_foreign_key(
        "fk_players_custom_avatar_id_custom_avatars",
        "players",
        "custom_avatars",
        ["custom_avatar_id"],
        ["id"],
    )

    op.create_table(
        "seasons",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["player_id"], ["players.id"], name=op.f("fk_seasons_player_id_players")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_seasons")),
    )
    op.create_index(
        "uq_seasons_player_id_active",
        "seasons",
        ["player_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )

    op.create_table(
        "rounds",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("season_id", sa.BigInteger(), nullable=False),
        sa.Column("difficulty", sa.String(6), nullable=False),
        sa.Column("note_count", sa.SmallInteger(), nullable=False),
        sa.Column("note_naming", sa.String(7), nullable=False),
        sa.Column(
            "status",
            sa.String(9),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column("correct_count", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint(
            "difficulty IN ('easy','medium','hard')",
            name=op.f("ck_rounds_difficulty"),
        ),
        sa.CheckConstraint(
            "note_count IN (1,2,3,4)", name=op.f("ck_rounds_note_count")
        ),
        sa.CheckConstraint(
            "status IN ('active','completed','expired')",
            name=op.f("ck_rounds_status"),
        ),
        sa.ForeignKeyConstraint(
            ["player_id"], ["players.id"], name=op.f("fk_rounds_player_id_players")
        ),
        sa.ForeignKeyConstraint(
            ["season_id"], ["seasons.id"], name=op.f("fk_rounds_season_id_seasons")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rounds")),
    )
    op.create_index(
        "ix_rounds_player_season_diff_count",
        "rounds",
        ["player_id", "season_id", "difficulty", "note_count"],
    )

    op.create_table(
        "task_attempts",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("round_id", sa.BigInteger(), nullable=False),
        sa.Column("season_id", sa.BigInteger(), nullable=False),
        sa.Column("task_index", sa.SmallInteger(), nullable=False),
        sa.Column("clef", sa.String(6), nullable=False),
        sa.Column("expected_notes", postgresql.JSONB(), nullable=False),
        sa.Column("given_notes", postgresql.JSONB(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("timed_out", sa.Boolean(), nullable=False),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column("issued_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            "clef IN ('treble','bass')", name=op.f("ck_task_attempts_clef")
        ),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name=op.f("fk_task_attempts_round_id_rounds"),
        ),
        sa.ForeignKeyConstraint(
            ["season_id"],
            ["seasons.id"],
            name=op.f("fk_task_attempts_season_id_seasons"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_attempts")),
    )
    op.create_index(
        "uq_task_attempts_round_task",
        "task_attempts",
        ["round_id", "task_index"],
        unique=True,
    )
    op.create_index(
        "ix_task_attempts_season_player", "task_attempts", ["season_id", "round_id"]
    )

    op.create_table(
        "trophies_awarded",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column(
            "awarded_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name=op.f("fk_trophies_awarded_player_id_players"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trophies_awarded")),
    )
    op.create_index(
        "uq_trophies_awarded_player_threshold",
        "trophies_awarded",
        ["player_id", "threshold"],
        unique=True,
    )

    op.create_table(
        "avatar_generation_log",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "flagged", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "billable", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["users.id"],
            name=op.f("fk_avatar_generation_log_account_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_avatar_generation_log")),
    )
    op.create_index(
        "ix_avatar_generation_log_account_created",
        "avatar_generation_log",
        ["account_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("avatar_generation_log")
    op.drop_table("trophies_awarded")
    op.drop_table("task_attempts")
    op.drop_table("rounds")
    op.drop_table("seasons")
    op.drop_constraint(
        "fk_players_custom_avatar_id_custom_avatars", "players", type_="foreignkey"
    )
    op.drop_table("custom_avatars")
    op.drop_table("players")
