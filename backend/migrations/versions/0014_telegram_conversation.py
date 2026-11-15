"""telegram conversation state

Revision ID: 0014
Revises: 0013_exercise_chapters
Create Date: 2026-11-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013_exercise_chapters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "telegram_links", sa.Column("conv_step", sa.String(20), nullable=True)
    )
    op.add_column(
        "telegram_links", sa.Column("conv_chapter_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "telegram_links", sa.Column("conv_update_id", sa.BigInteger(), nullable=True)
    )
    op.add_column(
        "telegram_updates", sa.Column("chapter_id", sa.Integer(), nullable=True)
    )
    op.add_column("telegram_updates", sa.Column("reply_text", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_telegram_links_conv_chapter_id_chapters",
        "telegram_links",
        "chapters",
        ["conv_chapter_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_telegram_updates_chapter_id_chapters",
        "telegram_updates",
        "chapters",
        ["chapter_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_telegram_updates_chapter_id_chapters",
        "telegram_updates",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_telegram_links_conv_chapter_id_chapters",
        "telegram_links",
        type_="foreignkey",
    )
    op.drop_column("telegram_updates", "reply_text")
    op.drop_column("telegram_updates", "chapter_id")
    op.drop_column("telegram_links", "conv_update_id")
    op.drop_column("telegram_links", "conv_chapter_id")
    op.drop_column("telegram_links", "conv_step")
