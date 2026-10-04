"""Durable game replies, achievements, and manager avatar review."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_game_rewards_review"
down_revision = "0010_round_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "task_attempts", sa.Column("submit_response", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "custom_avatars",
        sa.Column(
            "review_status", sa.String(8), nullable=False, server_default="pending"
        ),
    )
    op.add_column(
        "custom_avatars",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "custom_avatars", sa.Column("reviewed_by", sa.BigInteger(), nullable=True)
    )
    op.create_foreign_key(
        "fk_custom_avatars_reviewed_by_users",
        "custom_avatars",
        "users",
        ["reviewed_by"],
        ["id"],
    )
    op.execute(
        "UPDATE custom_avatars SET review_status = 'approved' WHERE status = 'ready'"
    )
    op.create_check_constraint(
        "ck_custom_avatars_review_status",
        "custom_avatars",
        "review_status IN ('pending','approved','rejected')",
    )
    op.add_column(
        "players", sa.Column("avatar_review_job_id", sa.BigInteger(), nullable=True)
    )
    op.create_foreign_key(
        "fk_players_avatar_review_job",
        "players",
        "custom_avatars",
        ["avatar_review_job_id"],
        ["id"],
    )
    op.execute("UPDATE rounds SET score = 0 WHERE score < 0")
    op.create_table(
        "achievements_awarded",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "player_id", sa.BigInteger(), sa.ForeignKey("players.id"), nullable=False
        ),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column(
            "awarded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "uq_achievements_player_code",
        "achievements_awarded",
        ["player_id", "code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("achievements_awarded")
    op.drop_constraint("fk_players_avatar_review_job", "players", type_="foreignkey")
    op.drop_column("players", "avatar_review_job_id")
    op.drop_constraint(
        "ck_custom_avatars_review_status", "custom_avatars", type_="check"
    )
    op.drop_constraint(
        "fk_custom_avatars_reviewed_by_users", "custom_avatars", type_="foreignkey"
    )
    for name in ("reviewed_by", "reviewed_at", "review_status"):
        op.drop_column("custom_avatars", name)
    op.drop_column("task_attempts", "submit_response")
