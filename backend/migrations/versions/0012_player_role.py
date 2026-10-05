"""Game-only player accounts without exercise permissions."""

import sqlalchemy as sa
from alembic import op

revision = "0012_player_role"
down_revision = "0011_game_rewards_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_users_role"), "users", type_="check")
    op.create_check_constraint(
        op.f("ck_users_role"), "users", "role IN ('manager', 'student', 'player')"
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM users WHERE role = 'player')")
    ):
        raise RuntimeError("PLAYER_ACCOUNTS_PREVENT_DOWNGRADE")
    op.drop_constraint(op.f("ck_users_role"), "users", type_="check")
    op.create_check_constraint(
        op.f("ck_users_role"), "users", "role IN ('manager', 'student')"
    )
