"""Persist assistance options and version note-only round scoring."""

import sqlalchemy as sa
from alembic import op

revision = "0010_round_rules"
down_revision = "0009_avatar_sheets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rounds",
        sa.Column(
            "show_sound_hint", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.add_column(
        "rounds",
        sa.Column(
            "show_correct_answer",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "rounds",
        sa.Column(
            "rules_version", sa.SmallInteger(), nullable=False, server_default="1"
        ),
    )


def downgrade() -> None:
    op.drop_column("rounds", "rules_version")
    op.drop_column("rounds", "show_correct_answer")
    op.drop_column("rounds", "show_sound_hint")
