"""Add numbered exercise chapters and saved listening runs."""

import sqlalchemy as sa
from alembic import op

revision = "0013_exercise_chapters"
down_revision = "0012_player_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE chapter_number_seq START WITH 2")
    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "number",
            sa.Integer(),
            server_default=sa.text("nextval('chapter_number_seq')"),
            nullable=False,
        ),
        sa.CheckConstraint("number > 0", name="ck_chapters_number_positive"),
        sa.UniqueConstraint("number", name="uq_chapters_number"),
    )
    op.execute("INSERT INTO chapters (number) VALUES (1)")

    op.add_column(
        "exercises",
        sa.Column("chapter_id", sa.Integer(), server_default="1", nullable=True),
    )
    op.execute(
        "UPDATE exercises SET chapter_id = (SELECT id FROM chapters WHERE number = 1)"
    )
    op.alter_column(
        "exercises",
        "chapter_id",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="1",
    )
    op.create_foreign_key(
        "fk_exercises_chapter_id_chapters",
        "exercises",
        "chapters",
        ["chapter_id"],
        ["id"],
    )
    op.create_index("ix_exercises_chapter_id", "exercises", ["chapter_id"])

    op.add_column(
        "listening_sessions",
        sa.Column("chapter_number", sa.Integer(), server_default="1", nullable=True),
    )
    op.execute("UPDATE listening_sessions SET chapter_number = 1")
    op.alter_column(
        "listening_sessions",
        "chapter_number",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="1",
    )
    op.create_index(
        "ix_listening_sessions_chapter_number",
        "listening_sessions",
        ["chapter_number"],
    )

    op.create_table(
        "listening_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("current_index", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'cancelled')",
            name="ck_listening_runs_status",
        ),
        sa.CheckConstraint(
            "current_index >= 0",
            name="ck_listening_runs_current_index_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_listening_runs_user_id_users",
        ),
    )
    op.create_index("ix_listening_runs_user_id", "listening_runs", ["user_id"])
    op.create_index(
        "uq_listening_runs_one_active_per_user",
        "listening_runs",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "listening_run_chapters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["listening_runs.id"],
            name="fk_listening_run_chapters_run_id_listening_runs",
        ),
        sa.UniqueConstraint(
            "run_id", "chapter_number", name="uq_listening_run_chapters_run_chapter"
        ),
    )
    op.create_index(
        "ix_listening_run_chapters_chapter_number",
        "listening_run_chapters",
        ["chapter_number"],
    )

    op.create_table(
        "listening_run_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name="fk_listening_run_items_exercise_id_exercises",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["listening_runs.id"],
            name="fk_listening_run_items_run_id_listening_runs",
        ),
        sa.UniqueConstraint(
            "run_id", "position", name="uq_listening_run_items_run_position"
        ),
        sa.UniqueConstraint(
            "run_id", "exercise_id", name="uq_listening_run_items_run_exercise"
        ),
    )


def downgrade() -> None:
    unsafe_data = op.get_bind().scalar(
        sa.text(
            "SELECT (SELECT is_called FROM chapter_number_seq) "
            "OR EXISTS (SELECT 1 FROM chapters WHERE number <> 1) "
            "OR EXISTS (SELECT 1 FROM exercises WHERE chapter_id <> "
            "(SELECT id FROM chapters WHERE number = 1)) "
            "OR EXISTS (SELECT 1 FROM listening_sessions WHERE chapter_number <> 1) "
            "OR EXISTS (SELECT 1 FROM listening_runs)"
        )
    )
    if unsafe_data:
        raise RuntimeError("CHAPTER_DATA_PREVENTS_DOWNGRADE")

    op.drop_table("listening_run_items")
    op.drop_index(
        "ix_listening_run_chapters_chapter_number",
        table_name="listening_run_chapters",
    )
    op.drop_table("listening_run_chapters")
    op.drop_index("uq_listening_runs_one_active_per_user", table_name="listening_runs")
    op.drop_index("ix_listening_runs_user_id", table_name="listening_runs")
    op.drop_table("listening_runs")

    op.drop_index(
        "ix_listening_sessions_chapter_number", table_name="listening_sessions"
    )
    op.drop_column("listening_sessions", "chapter_number")
    op.drop_index("ix_exercises_chapter_id", table_name="exercises")
    op.drop_constraint(
        "fk_exercises_chapter_id_chapters", "exercises", type_="foreignkey"
    )
    op.drop_column("exercises", "chapter_id")
    op.drop_table("chapters")
    op.execute("DROP SEQUENCE chapter_number_seq")
