"""versioned OMR jobs and manager review

Revision ID: 0006_omr
Revises: 0005_telegram
Create Date: 2026-09-30 06:52:54.107806

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_omr"
down_revision: str | Sequence[str] | None = "0005_telegram"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "omr_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("image_id", sa.String(length=36), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.String(length=36), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=64), nullable=True),
        sa.Column("score_filename", sa.String(length=64), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN "
            "('pending','processing','needs_review','approved','rejected','failed')",
            name=op.f("ck_omr_jobs_status"),
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_omr_jobs_exercise_id_exercises"),
        ),
        sa.ForeignKeyConstraint(
            ["image_id"],
            ["media_files.id"],
            name=op.f("fk_omr_jobs_image_id_media_files"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"], ["users.id"], name=op.f("fk_omr_jobs_reviewed_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_omr_jobs")),
    )
    op.create_index(
        op.f("ix_omr_jobs_exercise_id"), "omr_jobs", ["exercise_id"], unique=False
    )
    op.create_index(op.f("ix_omr_jobs_status"), "omr_jobs", ["status"], unique=False)
    op.create_index(
        "uq_omr_jobs_current",
        "omr_jobs",
        ["exercise_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_omr_jobs_current",
        table_name="omr_jobs",
        postgresql_where=sa.text("is_current"),
    )
    op.drop_index(op.f("ix_omr_jobs_status"), table_name="omr_jobs")
    op.drop_index(op.f("ix_omr_jobs_exercise_id"), table_name="omr_jobs")
    op.drop_table("omr_jobs")
