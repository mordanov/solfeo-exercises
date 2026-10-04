"""Persistent thirty-frame custom avatars and worker progress."""

import sqlalchemy as sa
from alembic import op

revision = "0009_avatar_sheets"
down_revision = "0008_game"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "custom_avatars",
        sa.Column("asset_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "custom_avatars",
        sa.Column("phase", sa.String(16), server_default="queued", nullable=False),
    )
    op.add_column(
        "custom_avatars",
        sa.Column("completed_images", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "custom_avatars",
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("custom_avatars", sa.Column("started_at", sa.DateTime(timezone=True)))
    op.add_column("custom_avatars", sa.Column("locked_at", sa.DateTime(timezone=True)))
    op.add_column("custom_avatars", sa.Column("lease_token", sa.String(36)))
    op.add_column("custom_avatars", sa.Column("generation_log_id", sa.BigInteger()))
    op.create_foreign_key(
        "fk_custom_avatars_generation_log_id",
        "custom_avatars",
        "avatar_generation_log",
        ["generation_log_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_custom_avatars_completed_images",
        "custom_avatars",
        "completed_images BETWEEN 0 AND 30",
    )
    op.execute(
        "UPDATE custom_avatars SET phase='complete', completed_images=3 "
        "WHERE status='ready'"
    )
    op.execute("UPDATE custom_avatars SET phase='failed' WHERE status='failed'")
    op.execute(
        "UPDATE custom_avatars SET status='failed', phase='failed', "
        "error_code='AVATAR_GENERATION_INTERRUPTED', completed_at=now() "
        "WHERE status='pending'"
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_custom_avatars_completed_images", "custom_avatars", type_="check"
    )
    op.drop_constraint(
        "fk_custom_avatars_generation_log_id", "custom_avatars", type_="foreignkey"
    )
    for name in (
        "generation_log_id",
        "lease_token",
        "locked_at",
        "started_at",
        "attempts",
        "completed_images",
        "phase",
        "asset_version",
    ):
        op.drop_column("custom_avatars", name)
