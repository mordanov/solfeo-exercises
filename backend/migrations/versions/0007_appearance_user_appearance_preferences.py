"""user appearance preferences

Revision ID: 0007_appearance
Revises: 0006_omr
Create Date: 2026-10-02 12:16:42.962690

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_appearance"
down_revision: str | Sequence[str] | None = "0006_omr"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "light_scheme", sa.String(8), nullable=False, server_default="classic"
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "dark_scheme", sa.String(8), nullable=False, server_default="classic"
        ),
    )
    op.add_column(
        "users",
        sa.Column("ui_font", sa.String(8), nullable=False, server_default="roboto"),
    )
    op.add_column(
        "users",
        sa.Column("ui_font_size", sa.Integer(), nullable=False, server_default="16"),
    )
    for column in ("light_scheme", "dark_scheme"):
        op.create_check_constraint(
            op.f("ck_users_" + column),
            "users",
            column + " IN ('classic', 'forest', 'warm', 'plum')",
        )
    op.create_check_constraint(
        op.f("ck_users_ui_font"), "users", "ui_font IN ('roboto', 'system', 'serif')"
    )
    op.create_check_constraint(
        op.f("ck_users_ui_font_size"), "users", "ui_font_size IN (16, 18, 20)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    for column in ("ui_font_size", "ui_font", "dark_scheme", "light_scheme"):
        op.drop_constraint(op.f("ck_users_" + column), "users", type_="check")
        op.drop_column("users", column)
