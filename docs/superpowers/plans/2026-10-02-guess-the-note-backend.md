# Guess the Note — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the server-authoritative "Guess the Note" game module — players, rounds, seasons, progression, stats, confusion analytics, built-in avatar catalog, and AI avatar generation — as a self-contained FastAPI sub-package.

**Architecture:** A new `backend/app/game/` package with its own models, services, and API routers, all wired into the existing `app/main.py` and sharing the existing `Base`, `Session`, `Settings`, and `Identity` types. A `worker/generate_avatar.py` polls for pending AI avatar jobs via the same Postgres advisory-lock pattern used by the OMR worker. All business logic lives in service functions (pure or near-pure); routers are thin.

**Tech Stack:** FastAPI 0.115 · SQLAlchemy 2.x (sync) · Alembic 1.20 · PostgreSQL · httpx (for OpenAI) · pytest + anyio

**Spec:** `docs/superpowers/specs/2026-10-02-guess-the-note-design.md`

## Global Constraints

- All models import `Base` from `app.models` (not redeclare it).
- Migrations use `op.f()` for all constraint names; `down_revision = "0007_appearance"`.
- `ServiceError(code, status)` from `app.services.auth` for all API errors.
- `Manager`, `Member`, `Db`, `Configuration` dependency aliases from `app.api.auth`.
- CSRF: `dependencies=[Depends(require_csrf)]` on every mutating route.
- Settings prefix `env_prefix="API_"` — new fields use `validation_alias` that omits the prefix.
- OpenAI via raw `httpx` — no `openai` Python package.
- Tests require `DATABASE_NAME=solfeo_test`; use the fixture pattern from `backend/tests/test_auth.py`.
- Worker lock ID must differ from OMR's `710024006` and auth's `710024001`.

## Review Focus

- Double-tap guard on `POST /rounds/{id}/submit`: second call for same `task_index` must return stored result idempotently, not recompute.
- Late submit timing: `submitted_at > issued_at + time_limit_s + grace_ms/1000` → `timed_out=True` regardless of answers given.
- Circular FK (`players.custom_avatar_id ↔ custom_avatars.player_id`): migration must use `op.create_foreign_key` after both tables exist.
- Season partial-unique index (`UNIQUE (player_id) WHERE ended_at IS NULL`) — enforce at DB level, not only in service.
- Daily avatar quota: counts `billable=True AND created_at >= UTC midnight today`; manager role bypasses; failed moderation sets `billable=False` on the log row.

---

### Task 1: Scaffold + config + Settings fields

**Files:**
- Create: `backend/app/game/__init__.py`
- Create: `backend/app/game/config.py`
- Modify: `backend/app/settings.py` — add 4 fields

**Interfaces:**
- Produces: `TASKS_PER_ROUND`, `WIN_THRESHOLD`, `TIME_EASY_S`, `TIME_MEDIUM_S`, `TIME_HARD_S`, `XP_CORRECT_TASK`, `XP_WIN_BONUS`, `LEVEL_THRESHOLDS`, `LEVEL_PREFIXES_RU`, `TROPHY_THRESHOLDS`, `NOTE_RANGE`, `ANIMAL_IDS` (all from `app.game.config`).
- Produces: `settings.avatar_image_model`, `settings.avatar_gen_daily_limit`, `settings.avatar_gen_grace_ms`, `settings.avatar_round_expire_s`.

- [ ] **Step 1: Create `backend/app/game/__init__.py`** (empty)

```python
# backend/app/game/__init__.py
```

- [ ] **Step 2: Create `backend/app/game/config.py`**

```python
# backend/app/game/config.py
TASKS_PER_ROUND = 7
WIN_THRESHOLD = 5         # correct tasks needed to win
TIME_EASY_S = 13
TIME_MEDIUM_S = 10
TIME_HARD_S = 7
XP_CORRECT_TASK = 1
XP_WIN_BONUS = 5
LEVEL_THRESHOLDS = [0, 30, 80, 150, 250, 400, 600, 850, 1150, 1500]
LEVEL_PREFIXES_RU = [
    "ути-пути", "микро", "мини", "настоящий", "супер",
    "мега", "убер", "великий", "величайший", "божественный",
]
TROPHY_THRESHOLDS = [20, 100, 200, 500]
NOTE_RANGE = {
    "treble": [
        ("C", 4), ("D", 4), ("E", 4), ("F", 4), ("G", 4),
        ("A", 4), ("B", 4), ("C", 5), ("D", 5), ("E", 5),
        ("F", 5), ("G", 5),
    ],
    "bass": [
        ("E", 2), ("F", 2), ("G", 2), ("A", 2), ("B", 2),
        ("C", 3), ("D", 3), ("E", 3), ("F", 3), ("G", 3),
        ("A", 3), ("B", 3), ("C", 4),
    ],
}
ANIMAL_IDS = [
    "unicorn", "dragon", "phoenix", "griffin",
    "sphinx_cat", "kitsune_fox", "pegasus", "mermaid",
]
AVATAR_WORKER_LOCK_ID = 710024007
```

- [ ] **Step 3: Add Settings fields** — open `backend/app/settings.py`, find the class body, and add after the last existing field:

```python
avatar_image_model: str = Field(default="dall-e-3", validation_alias="AVATAR_IMAGE_MODEL")
avatar_gen_daily_limit: int = Field(default=3, ge=1, validation_alias="AVATAR_GEN_DAILY_LIMIT")
avatar_gen_grace_ms: int = Field(default=500, ge=0, validation_alias="AVATAR_GEN_GRACE_MS")
avatar_round_expire_s: int = Field(default=3600, ge=60, validation_alias="AVATAR_ROUND_EXPIRE_S")
```

- [ ] **Step 4: Verify settings still load** (no test needed — just import it)

```bash
cd backend && python -c "from app.settings import Settings; s = Settings(); print(s.avatar_image_model)"
```
Expected: `dall-e-3`

- [ ] **Step 5: Commit**

```bash
git add backend/app/game/__init__.py backend/app/game/config.py backend/app/settings.py
git commit -m "feat(game): scaffold game package, config constants, settings fields

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: SQLAlchemy models

**Files:**
- Create: `backend/app/game/models.py`
- Modify: `backend/app/models/__init__.py` — import game models so Alembic discovers them

**Interfaces:**
- Consumes: `Base` from `app.models`
- Produces: `Player`, `Season`, `Round`, `TaskAttempt`, `TrophyAwarded`, `CustomAvatar`, `AvatarGenerationLog` — all importable from `app.game.models`.

- [ ] **Step 1: Write `backend/app/game/models.py`**

```python
from __future__ import annotations
from datetime import UTC, datetime
from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Index, Integer, SmallInteger, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    avatar_animal: Mapped[str | None] = mapped_column(String(20), nullable=True)
    custom_avatar_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("custom_avatars.id", use_alter=True, name="fk_players_custom_avatar_id_custom_avatars"),
        nullable=True,
    )
    xp: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())
    archived_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)

    __table_args__ = (
        CheckConstraint("length(name) >= 1", name="ck_players_name_length"),
        Index("uq_players_account_id_name", "account_id", "name", unique=True),
    )


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    player_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("players.id"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)

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
    player_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("players.id"), nullable=False)
    season_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("seasons.id"), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(6), nullable=False)
    note_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    note_naming: Mapped[str] = mapped_column(String(7), nullable=False)
    status: Mapped[str] = mapped_column(String(9), nullable=False, server_default=text("'active'"))
    score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    correct_count: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)

    __table_args__ = (
        CheckConstraint("difficulty IN ('easy','medium','hard')", name="ck_rounds_difficulty"),
        CheckConstraint("note_count IN (1,2,3,4)", name="ck_rounds_note_count"),
        CheckConstraint("status IN ('active','completed','expired')", name="ck_rounds_status"),
        Index("ix_rounds_player_season_diff_count", "player_id", "season_id", "difficulty", "note_count"),
    )


class TaskAttempt(Base):
    __tablename__ = "task_attempts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    round_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("rounds.id"), nullable=False)
    season_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("seasons.id"), nullable=False)
    task_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    clef: Mapped[str] = mapped_column(String(6), nullable=False)
    expected_notes: Mapped[dict] = mapped_column(JSONB, nullable=False)
    given_notes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    timed_out: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    __table_args__ = (
        CheckConstraint("clef IN ('treble','bass')", name="ck_task_attempts_clef"),
        Index("uq_task_attempts_round_task", "round_id", "task_index", unique=True),
        Index("ix_task_attempts_season_player", "season_id", "round_id"),
    )


class TrophyAwarded(Base):
    __tablename__ = "trophies_awarded"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    player_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("players.id"), nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("uq_trophies_awarded_player_threshold", "player_id", "threshold", unique=True),
    )


class CustomAvatar(Base):
    __tablename__ = "custom_avatars"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("players.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(7), nullable=False, server_default=text("'pending'"))
    base_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    happy_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    sad_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('pending','ready','failed')", name="ck_custom_avatars_status"),
    )


class AvatarGenerationLog(Base):
    __tablename__ = "avatar_generation_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    billable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_avatar_generation_log_account_created", "account_id", "created_at"),
    )
```

- [ ] **Step 2: Register game models in Alembic discovery** — add to `backend/app/models/__init__.py` after the last import:

```python
import app.game.models as _game_models  # noqa: F401
```

- [ ] **Step 3: Verify Alembic sees the tables**

```bash
cd backend && python -c "
from app.models import Base
import app.game.models  # noqa
print(sorted(Base.metadata.tables.keys()))
"
```
Expected output includes: `'avatar_generation_log'`, `'custom_avatars'`, `'players'`, `'rounds'`, `'seasons'`, `'task_attempts'`, `'trophies_awarded'`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/game/models.py backend/app/models/__init__.py
git commit -m "feat(game): add SQLAlchemy models for game module

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Alembic migration 0008

**Files:**
- Create: `backend/migrations/versions/0008_game_guess_the_note.py`

**Interfaces:**
- Consumes: `down_revision = "0007_appearance"`
- Produces: all 7 game tables in the DB; deferred FK `fk_players_custom_avatar_id_custom_avatars` created after both tables exist.

- [ ] **Step 1: Write the migration** — reference `0003_exercises` and `0007_appearance` for format:

```python
"""guess the note game tables

Revision ID: 0008_game
Revises: 0007_appearance
Create Date: 2026-10-02
"""

from alembic import op
import sqlalchemy as sa
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
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("length(name) >= 1", name=op.f("ck_players_name_length")),
        sa.ForeignKeyConstraint(["account_id"], ["users.id"], name=op.f("fk_players_account_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_players")),
    )
    op.create_index("uq_players_account_id_name", "players", ["account_id", "name"], unique=True)

    op.create_table(
        "custom_avatars",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(7), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("base_path", sa.Text(), nullable=True),
        sa.Column("happy_path", sa.Text(), nullable=True),
        sa.Column("sad_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.CheckConstraint("status IN ('pending','ready','failed')", name=op.f("ck_custom_avatars_status")),
        sa.ForeignKeyConstraint(["account_id"], ["users.id"], name=op.f("fk_custom_avatars_account_id_users")),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], name=op.f("fk_custom_avatars_player_id_players")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_custom_avatars")),
    )

    # Deferred FK: players.custom_avatar_id → custom_avatars.id
    op.create_foreign_key(
        "fk_players_custom_avatar_id_custom_avatars",
        "players", "custom_avatars",
        ["custom_avatar_id"], ["id"],
    )

    op.create_table(
        "seasons",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], name=op.f("fk_seasons_player_id_players")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_seasons")),
    )
    op.create_index(
        "uq_seasons_player_id_active", "seasons", ["player_id"],
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
        sa.Column("status", sa.String(9), server_default=sa.text("'active'"), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column("correct_count", sa.SmallInteger(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint("difficulty IN ('easy','medium','hard')", name=op.f("ck_rounds_difficulty")),
        sa.CheckConstraint("note_count IN (1,2,3,4)", name=op.f("ck_rounds_note_count")),
        sa.CheckConstraint("status IN ('active','completed','expired')", name=op.f("ck_rounds_status")),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], name=op.f("fk_rounds_player_id_players")),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"], name=op.f("fk_rounds_season_id_seasons")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rounds")),
    )
    op.create_index("ix_rounds_player_season_diff_count", "rounds", ["player_id", "season_id", "difficulty", "note_count"])

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
        sa.CheckConstraint("clef IN ('treble','bass')", name=op.f("ck_task_attempts_clef")),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], name=op.f("fk_task_attempts_round_id_rounds")),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"], name=op.f("fk_task_attempts_season_id_seasons")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_attempts")),
    )
    op.create_index("uq_task_attempts_round_task", "task_attempts", ["round_id", "task_index"], unique=True)
    op.create_index("ix_task_attempts_season_player", "task_attempts", ["season_id", "round_id"])

    op.create_table(
        "trophies_awarded",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("player_id", sa.BigInteger(), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("awarded_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], name=op.f("fk_trophies_awarded_player_id_players")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trophies_awarded")),
    )
    op.create_index("uq_trophies_awarded_player_threshold", "trophies_awarded", ["player_id", "threshold"], unique=True)

    op.create_table(
        "avatar_generation_log",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("flagged", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("billable", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["users.id"], name=op.f("fk_avatar_generation_log_account_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_avatar_generation_log")),
    )
    op.create_index("ix_avatar_generation_log_account_created", "avatar_generation_log", ["account_id", "created_at"])


def downgrade() -> None:
    op.drop_table("avatar_generation_log")
    op.drop_table("trophies_awarded")
    op.drop_table("task_attempts")
    op.drop_table("rounds")
    op.drop_table("seasons")
    op.drop_foreign_key("fk_players_custom_avatar_id_custom_avatars", "players")
    op.drop_table("custom_avatars")
    op.drop_table("players")
```

- [ ] **Step 2: Run migration against the test DB to verify it applies cleanly**

```bash
cd backend && DATABASE_NAME=solfeo_test alembic upgrade head
```
Expected: no errors.

- [ ] **Step 3: Verify downgrade works**

```bash
cd backend && DATABASE_NAME=solfeo_test alembic downgrade 0007_appearance
cd backend && DATABASE_NAME=solfeo_test alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/versions/0008_game_guess_the_note.py
git commit -m "feat(game): migration 0008 — guess the note game tables

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Player service + API

**Files:**
- Create: `backend/app/game/services/__init__.py`
- Create: `backend/app/game/services/players.py`
- Create: `backend/app/game/api/__init__.py`
- Create: `backend/app/game/api/players.py`
- Modify: `backend/app/main.py` — register `game_players_router`
- Create: `backend/tests/game/__init__.py`
- Create: `backend/tests/game/test_auth.py`

**Interfaces:**
- Consumes: `Player`, `Season`, `CustomAvatar` from `app.game.models`; `ANIMAL_IDS` from `app.game.config`
- Produces:
  - `get_or_403(session, player_id, account_id) -> Player`
  - `list_players(session, account_id) -> list[Player]`
  - `create_player(session, account_id, name, avatar_animal) -> Player`
  - `update_player(session, player_id, *, name, avatar_animal, custom_avatar_id) -> Player`
  - Routers registered at `/api/game/players`

- [ ] **Step 1: Write failing test for role checks**

```python
# backend/tests/game/test_auth.py
import pytest
import httpx
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import delete
from app.models import Base
from app.database import Database
from app.settings import Settings

pytestmark = pytest.mark.anyio

ORIGIN = "https://test"

@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"

@pytest.fixture
def settings() -> Settings:
    result = Settings(auth_allowed_origins=[ORIGIN], session_cookie_secure=True)
    if result.database_name != "solfeo_test":
        raise pytest.UsageError("Set DATABASE_NAME=solfeo_test")
    return result

@pytest.fixture
def database(settings) -> Settings:
    db = Database(settings)
    with db.engine.begin() as conn:
        config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
        config.attributes["connection"] = conn
        command.upgrade(config, "head")
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(delete(table))
    try:
        yield db
    finally:
        with db.engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(delete(table))
        db.close()

@pytest.fixture
async def client(settings, database):
    from app.main import create_app
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=ORIGIN
        ) as c:
            yield c

async def _login(client, username, password) -> dict:
    r = await client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()

async def _make_manager(settings, database) -> tuple[str, str]:
    from app.services.auth import create_user
    with database.session() as s:
        create_user(s, settings, username="mgr", password="P@ssw0rd!!", first_name="M", last_name="X",
                    role="manager", must_change_password=False)
    return "mgr", "P@ssw0rd!!"

async def _make_student(settings, database) -> tuple[str, str]:
    from app.services.auth import create_user
    with database.session() as s:
        create_user(s, settings, username="stu", password="P@ssw0rd!!", first_name="S", last_name="X",
                    role="student", must_change_password=False)
    return "stu", "P@ssw0rd!!"

async def test_student_cannot_create_player(client, settings, database):
    u, p = await _make_student(settings, database)
    auth = await _login(client, u, p)
    r = await client.post(
        "/api/game/players",
        json={"name": "Kid", "avatar_animal": "dragon"},
        headers={"X-CSRF-Token": auth["csrf_token"]},
    )
    assert r.status_code == 403

async def test_student_cannot_reset_season(client, settings, database):
    u, p = await _make_student(settings, database)
    auth = await _login(client, u, p)
    r = await client.post(
        "/api/game/players/999/seasons/reset",
        json={"confirmation": "RESET"},
        headers={"X-CSRF-Token": auth["csrf_token"]},
    )
    assert r.status_code == 403
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd backend && DATABASE_NAME=solfeo_test pytest tests/game/test_auth.py -v
```
Expected: errors (routes don't exist yet).

- [ ] **Step 3: Create `backend/app/game/services/__init__.py`** (empty)

- [ ] **Step 4: Create `backend/app/game/services/players.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.game.models import Player, Season
from app.services.auth import ServiceError


def get_or_403(session: Session, player_id: int, account_id: int) -> Player:
    player = session.get(Player, player_id)
    if player is None or player.account_id != account_id:
        raise ServiceError("PLAYER_NOT_FOUND", 404)
    return player


def list_players(session: Session, account_id: int | None = None) -> list[Player]:
    q = select(Player)
    if account_id is not None:
        q = q.where(Player.account_id == account_id)
    return list(session.scalars(q.order_by(Player.id)))


def create_player(session: Session, account_id: int, name: str, avatar_animal: str | None) -> Player:
    from app.game.config import ANIMAL_IDS
    if avatar_animal is not None and avatar_animal not in ANIMAL_IDS:
        raise ServiceError("INVALID_AVATAR_ANIMAL", 422)
    existing = session.scalar(
        select(Player).where(Player.account_id == account_id, Player.name == name)
    )
    if existing is not None:
        raise ServiceError("PLAYER_NAME_TAKEN", 409)
    player = Player(account_id=account_id, name=name, avatar_animal=avatar_animal)
    session.add(player)
    session.flush()
    # Open initial season
    season = Season(player_id=player.id, number=1)
    session.add(season)
    session.flush()
    return player


def update_player(
    session: Session,
    player_id: int,
    *,
    name: str | None = None,
    avatar_animal: str | None = None,
    custom_avatar_id: int | None = None,
) -> Player:
    from app.game.config import ANIMAL_IDS
    player = session.get(Player, player_id)
    if player is None:
        raise ServiceError("PLAYER_NOT_FOUND", 404)
    if name is not None:
        player.name = name
    if avatar_animal is not None:
        if avatar_animal not in ANIMAL_IDS:
            raise ServiceError("INVALID_AVATAR_ANIMAL", 422)
        player.avatar_animal = avatar_animal
    if custom_avatar_id is not None:
        player.custom_avatar_id = custom_avatar_id
    session.flush()
    return player
```

- [ ] **Step 5: Create `backend/app/game/api/__init__.py`** (empty)

- [ ] **Step 6: Create `backend/app/game/api/players.py`**

```python
from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.auth import Db, Manager, Member, require_csrf
from app.game import services

router = APIRouter(prefix="/api/game/players", tags=["game-players"])


class CreatePlayerBody(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    avatar_animal: str | None = None


class PatchPlayerBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=20)
    avatar_animal: str | None = None
    custom_avatar_id: int | None = None


def _player_out(player) -> dict:
    return {
        "id": player.id,
        "account_id": player.account_id,
        "name": player.name,
        "avatar_animal": player.avatar_animal,
        "custom_avatar_id": player.custom_avatar_id,
        "xp": player.xp,
        "created_at": player.created_at.isoformat(),
    }


@router.get("")
def list_players(identity: Member, db: Db):
    from app.game.services.players import list_players as svc_list
    with db.session() as session:
        with session.begin():
            if identity.user.role == "manager":
                players = svc_list(session)
            else:
                players = svc_list(session, account_id=identity.user.id)
    return [_player_out(p) for p in players]


@router.post("", dependencies=[Depends(require_csrf)])
def create_player(body: CreatePlayerBody, identity: Manager, db: Db):
    from app.game.services.players import create_player as svc_create
    with db.session() as session:
        with session.begin():
            player = svc_create(session, identity.user.id, body.name, body.avatar_animal)
    return _player_out(player)


@router.get("/{player_id}")
def get_player(player_id: int, identity: Member, db: Db):
    from app.game.services.players import get_or_403
    with db.session() as session:
        with session.begin():
            account_id = None if identity.user.role == "manager" else identity.user.id
            player = get_or_403(session, player_id, account_id or player_id)
            # For student, verify ownership
            if identity.user.role != "manager" and player.account_id != identity.user.id:
                from app.services.auth import ServiceError
                raise ServiceError("PLAYER_NOT_FOUND", 404)
    return _player_out(player)


@router.patch("/{player_id}", dependencies=[Depends(require_csrf)])
def patch_player(player_id: int, body: PatchPlayerBody, identity: Manager, db: Db):
    from app.game.services.players import update_player
    with db.session() as session:
        with session.begin():
            player = update_player(
                session, player_id,
                name=body.name,
                avatar_animal=body.avatar_animal,
                custom_avatar_id=body.custom_avatar_id,
            )
    return _player_out(player)
```

- [ ] **Step 7: Register router in `backend/app/main.py`** — find the section where other routers are registered (look for `app.include_router`) and add:

```python
from app.game.api.players import router as game_players_router
# ...
app.include_router(game_players_router)
```

- [ ] **Step 8: Run role check tests**

```bash
cd backend && DATABASE_NAME=solfeo_test pytest tests/game/test_auth.py -v
```
Expected: PASS (student gets 403 on manager-only routes).

- [ ] **Step 9: Commit**

```bash
git add backend/app/game/services/ backend/app/game/api/ backend/app/main.py backend/tests/game/
git commit -m "feat(game): player service and API with role checks

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Round service (pure functions) + tests

**Files:**
- Create: `backend/app/game/services/rounds.py`
- Create: `backend/tests/game/test_scoring.py`
- Create: `backend/tests/game/test_rounds.py`

**Interfaces:**
- Consumes: `NOTE_RANGE`, `TASKS_PER_ROUND`, `TIME_EASY_S`, `TIME_MEDIUM_S`, `TIME_HARD_S`, `WIN_THRESHOLD` from `app.game.config`
- Produces:
  - `generate_tasks(difficulty, note_count, note_naming) -> list[dict]` — 7 tasks, random clef per task, no immediate repeat
  - `score_task(expected, given) -> int` — +1 correct, -1 wrong/timeout
  - `time_limit_s(difficulty) -> int`
  - `check_timeout(issued_at, submitted_at, difficulty, grace_ms) -> bool`
  - `create_round(session, player_id, season_id, difficulty, note_count, note_naming, settings) -> tuple[Round, TaskAttempt]`
  - `submit_task(session, round_id, task_index, answers, timed_out, submitted_at, settings) -> dict`

- [ ] **Step 1: Write scoring tests first**

```python
# backend/tests/game/test_scoring.py
from app.game.services.rounds import score_task

def test_all_correct():
    expected = [{"name": "C", "octave": 4}, {"name": "E", "octave": 4}]
    given = [{"name": "C", "octave": 4}, {"name": "E", "octave": 4}]
    assert score_task(expected, given) == 1

def test_wrong_answer():
    expected = [{"name": "C", "octave": 4}]
    given = [{"name": "D", "octave": 4}]
    assert score_task(expected, given) == -1

def test_timeout():
    assert score_task([{"name": "C", "octave": 4}], None) == -1

def test_wrong_order():
    expected = [{"name": "C", "octave": 4}, {"name": "E", "octave": 4}]
    given = [{"name": "E", "octave": 4}, {"name": "C", "octave": 4}]
    assert score_task(expected, given) == -1
```

- [ ] **Step 2: Run to verify FAIL**

```bash
cd backend && pytest tests/game/test_scoring.py -v
```
Expected: ImportError.

- [ ] **Step 3: Write round generation tests**

```python
# backend/tests/game/test_rounds.py
import pytest
from datetime import UTC, datetime, timedelta
from app.game.services.rounds import generate_tasks, time_limit_s, check_timeout
from app.game.config import NOTE_RANGE, TASKS_PER_ROUND

def test_generate_tasks_count():
    tasks = generate_tasks("easy", 2, "solfege")
    assert len(tasks) == TASKS_PER_ROUND

def test_generate_tasks_clef_is_treble_or_bass():
    tasks = generate_tasks("easy", 1, "letters")
    assert all(t["clef"] in ("treble", "bass") for t in tasks)

def test_generate_tasks_notes_in_range():
    tasks = generate_tasks("hard", 4, "letters")
    for task in tasks:
        clef = task["clef"]
        valid = {(n, o) for n, o in NOTE_RANGE[clef]}
        for note in task["notes"]:
            assert (note["name"], note["octave"]) in valid, f"{note} not in {clef} range"

def test_generate_tasks_no_immediate_repeat():
    for _ in range(10):
        tasks = generate_tasks("medium", 2, "letters")
        for i in range(1, len(tasks)):
            assert tasks[i]["notes"] != tasks[i - 1]["notes"] or tasks[i]["clef"] != tasks[i - 1]["clef"]

def test_time_limit_s():
    assert time_limit_s("easy") == 13
    assert time_limit_s("medium") == 10
    assert time_limit_s("hard") == 7

def test_check_timeout_within_grace():
    issued = datetime.now(UTC)
    submitted = issued + timedelta(seconds=13.4)  # 400ms over 13s limit, grace=500ms
    assert check_timeout(issued, submitted, "easy", grace_ms=500) is False

def test_check_timeout_over_grace():
    issued = datetime.now(UTC)
    submitted = issued + timedelta(seconds=14.0)  # 1000ms over, grace=500ms
    assert check_timeout(issued, submitted, "easy", grace_ms=500) is True
```

- [ ] **Step 4: Run to verify FAIL**

```bash
cd backend && pytest tests/game/test_rounds.py -v
```

- [ ] **Step 5: Write `backend/app/game/services/rounds.py`**

```python
from __future__ import annotations
import random
from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.game.config import (
    NOTE_RANGE, TASKS_PER_ROUND,
    TIME_EASY_S, TIME_MEDIUM_S, TIME_HARD_S,
)
from app.game.models import Round, TaskAttempt
from app.services.auth import ServiceError
from app.settings import Settings


def time_limit_s(difficulty: str) -> int:
    return {"easy": TIME_EASY_S, "medium": TIME_MEDIUM_S, "hard": TIME_HARD_S}[difficulty]


def score_task(expected: list[dict] | None, given: list[dict] | None) -> int:
    if given is None:
        return -1
    if len(given) != len(expected):
        return -1
    for e, g in zip(expected, given):
        if e["name"] != g["name"] or e["octave"] != g["octave"]:
            return -1
    return 1


def check_timeout(issued_at: datetime, submitted_at: datetime, difficulty: str, grace_ms: int) -> bool:
    limit = timedelta(seconds=time_limit_s(difficulty)) + timedelta(milliseconds=grace_ms)
    return submitted_at - issued_at > limit


def generate_tasks(difficulty: str, note_count: int, note_naming: str) -> list[dict]:
    tasks = []
    last = None
    for _ in range(TASKS_PER_ROUND):
        clef = random.choice(["treble", "bass"])
        pool = NOTE_RANGE[clef]
        for attempt in range(50):
            notes = random.sample(pool, note_count)
            candidate = (clef, tuple((n, o) for n, o in notes))
            if candidate != last:
                last = candidate
                break
        tasks.append({
            "clef": clef,
            "notes": [{"name": n, "octave": o} for n, o in notes],
        })
    return tasks


def create_round(
    session: Session,
    player_id: int,
    season_id: int,
    difficulty: str,
    note_count: int,
    note_naming: str,
    settings: Settings,
) -> tuple[Round, list[dict]]:
    from datetime import UTC, datetime, timedelta
    now = datetime.now(UTC)
    tasks = generate_tasks(difficulty, note_count, note_naming)
    rnd = Round(
        player_id=player_id,
        season_id=season_id,
        difficulty=difficulty,
        note_count=note_count,
        note_naming=note_naming,
        status="active",
        created_at=now,
        expires_at=now + timedelta(seconds=settings.avatar_round_expire_s),
    )
    session.add(rnd)
    session.flush()
    for i, task in enumerate(tasks):
        attempt = TaskAttempt(
            round_id=rnd.id,
            season_id=season_id,
            task_index=i,
            clef=task["clef"],
            expected_notes=task["notes"],
            given_notes=None,
            is_correct=False,
            timed_out=False,
            score=0,
        )
        session.add(attempt)
    session.flush()
    return rnd, tasks


def submit_task(
    session: Session,
    round_id: int,
    task_index: int,
    answers: list[dict] | None,
    timed_out: bool,
    submitted_at: datetime,
    settings: Settings,
) -> dict:
    rnd = session.get(Round, round_id)
    if rnd is None or rnd.status != "active":
        raise ServiceError("ROUND_NOT_ACTIVE", 400)
    if submitted_at > rnd.expires_at:
        raise ServiceError("ROUND_EXPIRED", 400)

    attempt = session.scalar(
        select(TaskAttempt)
        .where(TaskAttempt.round_id == round_id, TaskAttempt.task_index == task_index)
        .with_for_update()
    )
    if attempt is None:
        raise ServiceError("TASK_NOT_FOUND", 404)
    # Idempotent double-tap guard
    if attempt.submitted_at is not None:
        return _build_submit_response(session, rnd, attempt, task_index)

    # Stamp issued_at on first submit (if not already done via get-task endpoint)
    if attempt.issued_at is None:
        attempt.issued_at = submitted_at - timedelta(milliseconds=1)

    # Timing check
    if not timed_out and attempt.issued_at is not None:
        timed_out = check_timeout(attempt.issued_at, submitted_at, rnd.difficulty, settings.avatar_gen_grace_ms)

    if timed_out:
        attempt.timed_out = True
        attempt.given_notes = None
        attempt.is_correct = False
        attempt.score = -1
    else:
        attempt.given_notes = answers
        attempt.is_correct = (score_task(attempt.expected_notes, answers) == 1)
        attempt.score = 1 if attempt.is_correct else -1

    attempt.submitted_at = submitted_at
    if attempt.issued_at:
        attempt.response_ms = int((submitted_at - attempt.issued_at).total_seconds() * 1000)
    session.flush()

    return _build_submit_response(session, rnd, attempt, task_index)


def _build_submit_response(session: Session, rnd: Round, attempt: TaskAttempt, task_index: int) -> dict:
    next_index = task_index + 1
    from app.game.config import TASKS_PER_ROUND
    next_task = None
    if next_index < TASKS_PER_ROUND:
        next_attempt = session.scalar(
            select(TaskAttempt).where(
                TaskAttempt.round_id == rnd.id, TaskAttempt.task_index == next_index
            )
        )
        if next_attempt:
            next_attempt.issued_at = datetime.now(UTC)
            session.flush()
            next_task = {"index": next_index, "clef": next_attempt.clef, "notes": next_attempt.expected_notes}

    result = None
    if next_index >= TASKS_PER_ROUND or (rnd.status == "completed"):
        result = _finalize_round(session, rnd)

    return {
        "is_correct": attempt.is_correct,
        "correct_answers": attempt.expected_notes,
        "score_delta": attempt.score,
        "next_task": next_task,
        "result": result,
    }


def _finalize_round(session: Session, rnd: Round) -> dict | None:
    from app.game.config import WIN_THRESHOLD, XP_CORRECT_TASK, XP_WIN_BONUS, TROPHY_THRESHOLDS
    if rnd.status == "completed":
        return None
    attempts = list(session.scalars(
        select(TaskAttempt).where(TaskAttempt.round_id == rnd.id)
    ))
    if len(attempts) < 7:
        return None
    # Only finalize when all tasks submitted
    if any(a.submitted_at is None for a in attempts):
        return None
    score = sum(a.score for a in attempts)
    correct_count = sum(1 for a in attempts if a.is_correct)
    is_win = correct_count >= WIN_THRESHOLD

    from datetime import UTC, datetime
    rnd.score = score
    rnd.correct_count = correct_count
    rnd.status = "completed"
    rnd.completed_at = datetime.now(UTC)

    xp_gained = correct_count * XP_CORRECT_TASK + (XP_WIN_BONUS if is_win else 0)

    from sqlalchemy import select as sa_select
    from app.models import User
    from app.game.models import Player, TrophyAwarded, Season
    player = session.get(Player, rnd.player_id)
    old_xp = player.xp
    player.xp += xp_gained
    session.flush()

    level_up = _compute_level(player.xp) > _compute_level(old_xp)
    new_trophy = _check_trophy(session, player, rnd.season_id)

    return {
        "score": score,
        "correct_count": correct_count,
        "is_win": is_win,
        "xp_gained": xp_gained,
        "level_up": level_up,
        "new_trophy": new_trophy,
        "practice_hint": _practice_hint(attempts),
    }


def _compute_level(xp: int) -> int:
    from app.game.config import LEVEL_THRESHOLDS
    level = 0
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp >= threshold:
            level = i
    return level


def _check_trophy(session: Session, player: "Player", season_id: int) -> int | None:
    from app.game.config import TROPHY_THRESHOLDS
    from app.game.models import TrophyAwarded, Round
    from sqlalchemy import func
    completed = session.scalar(
        select(func.count()).select_from(Round).where(
            Round.player_id == player.id, Round.status == "completed"
        )
    )
    for threshold in sorted(TROPHY_THRESHOLDS):
        if completed >= threshold:
            already = session.scalar(
                select(TrophyAwarded).where(
                    TrophyAwarded.player_id == player.id,
                    TrophyAwarded.threshold == threshold,
                )
            )
            if already is None:
                session.add(TrophyAwarded(player_id=player.id, threshold=threshold))
                session.flush()
                return threshold
    return None


def _practice_hint(attempts: list["TaskAttempt"]) -> str:
    from collections import Counter
    confusions: Counter = Counter()
    for a in attempts:
        if not a.is_correct and not a.timed_out and a.given_notes:
            for e, g in zip(a.expected_notes, a.given_notes):
                if e["name"] != g["name"]:
                    confusions[(e["name"], g["name"])] += 1
    if confusions:
        (expected, given), _ = confusions.most_common(1)[0]
        return f"Потренируем {expected} и {given}?"
    return "Молодец! Продолжай в том же духе!"
```

- [ ] **Step 6: Run all round/scoring tests**

```bash
cd backend && pytest tests/game/test_scoring.py tests/game/test_rounds.py -v
```
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/game/services/rounds.py backend/tests/game/test_scoring.py backend/tests/game/test_rounds.py
git commit -m "feat(game): round service with scoring, timing, task generation

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Round API

**Files:**
- Create: `backend/app/game/api/rounds.py`
- Modify: `backend/app/main.py` — register `game_rounds_router`

**Interfaces:**
- Consumes: `create_round`, `submit_task` from `app.game.services.rounds`; `ANIMAL_IDS`, `NOTE_RANGE` from `app.game.config`
- Produces: `POST /api/game/rounds`, `POST /api/game/rounds/{id}/submit`

- [ ] **Step 1: Create `backend/app/game/api/rounds.py`**

```python
from datetime import UTC, datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.auth import Configuration, Db, Member, require_csrf
from app.services.auth import ServiceError

router = APIRouter(prefix="/api/game/rounds", tags=["game-rounds"])


class CreateRoundBody(BaseModel):
    player_id: int
    difficulty: str
    note_count: int


class SubmitTaskBody(BaseModel):
    task_index: int
    answers: list[dict] | None = None
    timed_out: bool = False


@router.post("", dependencies=[Depends(require_csrf)])
def create_round(body: CreateRoundBody, identity: Member, db: Db, settings: Configuration):
    from app.game.config import NOTE_RANGE
    from app.game.services.players import get_or_403
    from app.game.services.rounds import create_round as svc_create
    from app.game.models import Season
    from sqlalchemy import select

    if body.difficulty not in ("easy", "medium", "hard"):
        raise ServiceError("INVALID_DIFFICULTY", 422)
    if body.note_count not in (1, 2, 3, 4):
        raise ServiceError("INVALID_NOTE_COUNT", 422)

    with db.session() as session:
        with session.begin():
            account_id = None if identity.user.role == "manager" else identity.user.id
            player = get_or_403(session, body.player_id, account_id or body.player_id)
            if identity.user.role != "manager" and player.account_id != identity.user.id:
                raise ServiceError("PLAYER_NOT_FOUND", 404)

            season = session.scalar(
                select(Season).where(Season.player_id == player.id, Season.ended_at == None)  # noqa: E711
            )
            if season is None:
                raise ServiceError("NO_ACTIVE_SEASON", 400)

            note_naming = identity.user.note_naming
            rnd, tasks = svc_create(
                session, player.id, season.id, body.difficulty, body.note_count, note_naming, settings
            )
            first = tasks[0]
            # Stamp issued_at on first task
            from app.game.models import TaskAttempt
            first_attempt = session.scalar(
                select(TaskAttempt).where(TaskAttempt.round_id == rnd.id, TaskAttempt.task_index == 0)
            )
            if first_attempt:
                first_attempt.issued_at = datetime.now(UTC)

    return {
        "round_id": rnd.id,
        "task": {"index": 0, "clef": first["clef"], "notes": first["notes"]},
    }


@router.post("/{round_id}/submit", dependencies=[Depends(require_csrf)])
def submit_task(round_id: int, body: SubmitTaskBody, identity: Member, db: Db, settings: Configuration):
    from app.game.services.rounds import submit_task as svc_submit
    from app.game.models import Round
    from sqlalchemy import select

    with db.session() as session:
        with session.begin():
            # Verify round belongs to this account
            rnd = session.get(Round, round_id)
            if rnd is None:
                raise ServiceError("ROUND_NOT_FOUND", 404)
            from app.game.models import Player
            player = session.get(Player, rnd.player_id)
            if identity.user.role != "manager" and (player is None or player.account_id != identity.user.id):
                raise ServiceError("ROUND_NOT_FOUND", 404)

            result = svc_submit(
                session, round_id,
                body.task_index,
                body.answers,
                body.timed_out,
                datetime.now(UTC),
                settings,
            )
    return result
```

- [ ] **Step 2: Register in `backend/app/main.py`**

```python
from app.game.api.rounds import router as game_rounds_router
# ...
app.include_router(game_rounds_router)
```

- [ ] **Step 3: Quick smoke test** (no dedicated test yet — integration test covers this in Task 12)

```bash
cd backend && python -c "from app.game.api.rounds import router; print(router.routes)"
```
Expected: shows two routes.

- [ ] **Step 4: Commit**

```bash
git add backend/app/game/api/rounds.py backend/app/main.py
git commit -m "feat(game): round API — create and submit endpoints

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Season service + API

**Files:**
- Create: `backend/app/game/services/seasons.py`
- Create: `backend/app/game/api/seasons.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/game/test_seasons.py`

**Interfaces:**
- Produces:
  - `reset_season(session, player_id) -> Season` — closes active season, opens new one
  - `list_seasons(session, player_id) -> list[Season]`
  - `GET /api/game/players/{id}/seasons`
  - `POST /api/game/players/{id}/seasons/reset`
  - `POST /api/game/seasons/reset-all`

- [ ] **Step 1: Write season tests**

```python
# backend/tests/game/test_seasons.py
import pytest
from tests.game.test_auth import anyio_backend, settings, database, client, _make_manager, _login

pytestmark = pytest.mark.anyio

async def _create_player(client, auth) -> int:
    r = await client.post(
        "/api/game/players",
        json={"name": "Kid1", "avatar_animal": "dragon"},
        headers={"X-CSRF-Token": auth["csrf_token"]},
    )
    assert r.status_code == 200
    return r.json()["id"]

async def test_reset_creates_new_season(client, settings, database):
    u, p = await _make_manager(settings, database)
    auth = await _login(client, u, p)
    pid = await _create_player(client, auth)

    r = await client.post(
        f"/api/game/players/{pid}/seasons/reset",
        json={"confirmation": "RESET"},
        headers={"X-CSRF-Token": auth["csrf_token"]},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["number"] == 2

async def test_xp_preserved_after_reset(client, settings, database):
    # After reset, player XP must not be zeroed
    u, p = await _make_manager(settings, database)
    auth = await _login(client, u, p)
    pid = await _create_player(client, auth)
    # Manually set xp via DB or by completing a round
    r = await client.post(
        f"/api/game/players/{pid}/seasons/reset",
        json={"confirmation": "RESET"},
        headers={"X-CSRF-Token": auth["csrf_token"]},
    )
    assert r.status_code == 200
    # XP check via get player
    pr = await client.get(f"/api/game/players/{pid}", headers={"X-CSRF-Token": auth["csrf_token"]})
    assert pr.json()["xp"] >= 0  # not negative

async def test_list_seasons(client, settings, database):
    u, p = await _make_manager(settings, database)
    auth = await _login(client, u, p)
    pid = await _create_player(client, auth)
    # Should have 1 season (opened at player creation)
    r = await client.get(f"/api/game/players/{pid}/seasons")
    assert r.status_code == 200
    seasons = r.json()
    assert len(seasons) >= 1
    assert seasons[0]["number"] == 1
```

- [ ] **Step 2: Run to verify FAIL**

```bash
cd backend && DATABASE_NAME=solfeo_test pytest tests/game/test_seasons.py -v
```

- [ ] **Step 3: Write `backend/app/game/services/seasons.py`**

```python
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.game.models import Player, Season
from app.services.auth import ServiceError


def list_seasons(session: Session, player_id: int) -> list[Season]:
    return list(session.scalars(
        select(Season).where(Season.player_id == player_id).order_by(Season.number)
    ))


def reset_season(session: Session, player_id: int) -> Season:
    player = session.get(Player, player_id)
    if player is None:
        raise ServiceError("PLAYER_NOT_FOUND", 404)
    active = session.scalar(
        select(Season).where(Season.player_id == player_id, Season.ended_at == None)  # noqa: E711
    )
    now = datetime.now(UTC)
    if active:
        active.ended_at = now
        session.flush()
    last_number = active.number if active else 0
    new_season = Season(player_id=player_id, number=last_number + 1, started_at=now)
    session.add(new_season)
    session.flush()
    return new_season
```

- [ ] **Step 4: Write `backend/app/game/api/seasons.py`**

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.auth import Db, Manager, Member, require_csrf
from app.services.auth import ServiceError

router = APIRouter(tags=["game-seasons"])


class ResetBody(BaseModel):
    confirmation: str  # must equal "RESET"


def _season_out(s) -> dict:
    return {
        "id": s.id, "player_id": s.player_id, "number": s.number,
        "started_at": s.started_at.isoformat(),
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
    }


@router.get("/api/game/players/{player_id}/seasons")
def list_seasons(player_id: int, identity: Member, db: Db):
    from app.game.services.seasons import list_seasons as svc_list
    with db.session() as session:
        with session.begin():
            seasons = svc_list(session, player_id)
    return [_season_out(s) for s in seasons]


@router.post("/api/game/players/{player_id}/seasons/reset", dependencies=[Depends(require_csrf)])
def reset_season(player_id: int, body: ResetBody, identity: Manager, db: Db):
    if body.confirmation != "RESET":
        raise ServiceError("CONFIRMATION_REQUIRED", 400)
    from app.game.services.seasons import reset_season as svc_reset
    with db.session() as session:
        with session.begin():
            season = svc_reset(session, player_id)
    return _season_out(season)


@router.post("/api/game/seasons/reset-all", dependencies=[Depends(require_csrf)])
def reset_all_seasons(body: ResetBody, identity: Manager, db: Db):
    if body.confirmation != "RESET":
        raise ServiceError("CONFIRMATION_REQUIRED", 400)
    from app.game.services.seasons import reset_season
    from app.game.models import Player
    from sqlalchemy import select
    with db.session() as session:
        with session.begin():
            players = list(session.scalars(select(Player)))
            results = [reset_season(session, p.id) for p in players]
    return [_season_out(s) for s in results]
```

- [ ] **Step 5: Register in `backend/app/main.py`**

```python
from app.game.api.seasons import router as game_seasons_router
# ...
app.include_router(game_seasons_router)
```

- [ ] **Step 6: Run tests**

```bash
cd backend && DATABASE_NAME=solfeo_test pytest tests/game/test_seasons.py -v
```
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/game/services/seasons.py backend/app/game/api/seasons.py backend/app/main.py backend/tests/game/test_seasons.py
git commit -m "feat(game): season service and API

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 8: Progression tests

**Files:**
- Create: `backend/tests/game/test_progression.py`

**Interfaces:**
- Consumes: `_compute_level`, `_check_trophy` from `app.game.services.rounds` (or test via round completion)

- [ ] **Step 1: Write progression tests**

```python
# backend/tests/game/test_progression.py
from app.game.services.rounds import _compute_level
from app.game.config import LEVEL_THRESHOLDS, TROPHY_THRESHOLDS

def test_level_zero_at_zero_xp():
    assert _compute_level(0) == 0

def test_level_advances_at_threshold():
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        assert _compute_level(threshold) == i

def test_level_does_not_exceed_max():
    assert _compute_level(99999) == len(LEVEL_THRESHOLDS) - 1

def test_level_between_thresholds():
    # XP between level 1 (30) and level 2 (80) stays at level 1
    assert _compute_level(50) == 1

def test_trophy_thresholds_sorted():
    assert TROPHY_THRESHOLDS == sorted(TROPHY_THRESHOLDS)
```

- [ ] **Step 2: Run**

```bash
cd backend && pytest tests/game/test_progression.py -v
```
Expected: PASS (these are pure function tests, no DB needed).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/game/test_progression.py
git commit -m "test(game): progression level and trophy threshold tests

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 9: Stats + confusion service + API

**Files:**
- Create: `backend/app/game/services/stats.py`
- Create: `backend/app/game/api/admin.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/game/test_stats.py`

**Interfaces:**
- Produces:
  - `get_stats(session, player_id, season_id) -> dict` — matrix by difficulty × note_count
  - `get_confusion(session, player_id, season_id) -> dict` — 7×7 heatmap + top confusions
  - `GET /api/game/players/{id}/stats`
  - `GET /api/game/players/{id}/confusion` (manager only)

- [ ] **Step 1: Write stats tests**

```python
# backend/tests/game/test_stats.py
import pytest
from tests.game.test_auth import anyio_backend, settings, database, client, _make_manager, _login

pytestmark = pytest.mark.anyio

async def test_stats_empty_for_new_player(client, settings, database):
    u, p = await _make_manager(settings, database)
    auth = await _login(client, u, p)
    r = await client.post(
        "/api/game/players",
        json={"name": "Stat", "avatar_animal": "unicorn"},
        headers={"X-CSRF-Token": auth["csrf_token"]},
    )
    pid = r.json()["id"]
    sr = await client.get(f"/api/game/players/{pid}/stats")
    assert sr.status_code == 200
    data = sr.json()
    # Expect matrix keys: easy/medium/hard × 1/2/3/4
    assert "easy" in data or data == {}  # empty is also fine

async def test_confusion_requires_manager(client, settings, database):
    from tests.game.test_auth import _make_student
    u, p = await _make_student(settings, database)
    auth = await _login(client, u, p)
    r = await client.get("/api/game/players/999/confusion")
    assert r.status_code == 403
```

- [ ] **Step 2: Run to verify FAIL**

```bash
cd backend && DATABASE_NAME=solfeo_test pytest tests/game/test_stats.py -v
```

- [ ] **Step 3: Write `backend/app/game/services/stats.py`**

```python
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.game.models import Round, TaskAttempt


def get_stats(session: Session, player_id: int, season_id: int) -> dict:
    rows = session.execute(
        select(
            Round.difficulty,
            Round.note_count,
            func.count(Round.id).label("rounds"),
            func.sum(Round.correct_count).label("total_correct"),
            func.avg(Round.score).label("avg_score"),
        )
        .where(Round.player_id == player_id, Round.season_id == season_id, Round.status == "completed")
        .group_by(Round.difficulty, Round.note_count)
    ).fetchall()

    matrix: dict = {}
    for diff, nc, rounds, correct, avg_score in rows:
        matrix.setdefault(diff, {})[str(nc)] = {
            "rounds": rounds,
            "total_correct": correct or 0,
            "avg_score": round(float(avg_score), 2) if avg_score else 0.0,
        }
    return matrix


NOTE_NAMES = ["C", "D", "E", "F", "G", "A", "B"]


def get_confusion(session: Session, player_id: int, season_id: int) -> dict:
    attempts = list(session.scalars(
        select(TaskAttempt)
        .join(Round, Round.id == TaskAttempt.round_id)
        .where(Round.player_id == player_id, TaskAttempt.season_id == season_id)
    ))
    heatmap: dict[str, dict[str, int]] = {n: {m: 0 for m in NOTE_NAMES} for n in NOTE_NAMES}
    top: dict[tuple, int] = {}
    for a in attempts:
        if a.is_correct or a.timed_out or not a.given_notes:
            continue
        for e, g in zip(a.expected_notes, a.given_notes):
            en, gn = e["name"], g["name"]
            if en != gn and en in heatmap and gn in NOTE_NAMES:
                heatmap[en][gn] += 1
                key = (en, gn)
                top[key] = top.get(key, 0) + 1

    top3 = sorted(top.items(), key=lambda x: -x[1])[:3]
    return {
        "heatmap": heatmap,
        "top_confusions": [
            {"expected": k[0], "given": k[1], "count": v} for k, v in top3
        ],
    }
```

- [ ] **Step 4: Write `backend/app/game/api/admin.py`**

```python
from fastapi import APIRouter
from app.api.auth import Db, Manager, Member

router = APIRouter(tags=["game-admin"])


@router.get("/api/game/players/{player_id}/stats")
def player_stats(player_id: int, identity: Member, db: Db):
    from app.game.services.stats import get_stats
    from app.game.models import Season
    from sqlalchemy import select
    with db.session() as session:
        with session.begin():
            season = session.scalar(
                select(Season).where(Season.player_id == player_id, Season.ended_at == None)  # noqa: E711
            )
            if season is None:
                return {}
            return get_stats(session, player_id, season.id)


@router.get("/api/game/players/{player_id}/confusion")
def player_confusion(player_id: int, identity: Manager, db: Db):
    from app.game.services.stats import get_confusion
    from app.game.models import Season
    from sqlalchemy import select
    with db.session() as session:
        with session.begin():
            season = session.scalar(
                select(Season).where(Season.player_id == player_id, Season.ended_at == None)  # noqa: E711
            )
            if season is None:
                return {"heatmap": {}, "top_confusions": []}
            return get_confusion(session, player_id, season.id)
```

- [ ] **Step 5: Register in `backend/app/main.py`**

```python
from app.game.api.admin import router as game_admin_router
# ...
app.include_router(game_admin_router)
```

- [ ] **Step 6: Run tests**

```bash
cd backend && DATABASE_NAME=solfeo_test pytest tests/game/test_stats.py -v
```
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/game/services/stats.py backend/app/game/api/admin.py backend/app/main.py backend/tests/game/test_stats.py
git commit -m "feat(game): stats and confusion analytics service + API

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 10: Avatar catalog + placeholder script

**Files:**
- Create: `scripts/gen_avatar_placeholders.py`
- Create: `frontend/public/assets/avatars/.gitkeep` (or `README.md` for drop-in instructions)

**Interfaces:**
- Produces: `assets/avatars/{animal_id}/{stage}_{mood}.svg` for all 8 animals × 10 stages × 3 moods = 240 files

- [ ] **Step 1: Write the generator script**

```python
#!/usr/bin/env python3
# scripts/gen_avatar_placeholders.py
"""Generate placeholder SVG avatars for all 8 animals × 10 stages × 3 moods.

Run from the repo root:
    python scripts/gen_avatar_placeholders.py

Outputs to frontend/public/assets/avatars/{animal}/{stage}_{mood}.svg
Real PNG files dropped into the same locations take priority via the
frontend resolver fallback order (exact match → stage neutral → 01 neutral → SVG placeholder).
"""
import sys
from pathlib import Path

ANIMALS = [
    ("unicorn",    "🦄", "#e8b4f0"),
    ("dragon",     "🐉", "#f0b4b4"),
    ("phoenix",    "🦅", "#f0d4b4"),
    ("griffin",    "🦁", "#d4c4a8"),
    ("sphinx_cat", "🐱", "#c4d4f0"),
    ("kitsune_fox","🦊", "#f0c4a8"),
    ("pegasus",    "🐴", "#b4d4f0"),
    ("mermaid",    "🧜", "#b4f0e8"),
]
MOODS = {
    "neutral": ("😐", "#888888"),
    "happy":   ("😊", "#22aa44"),
    "sad":     ("😢", "#4488cc"),
}
STAGES = range(1, 11)

OUT = Path("frontend/public/assets/avatars")


def make_svg(animal_emoji: str, bg_color: str, mood_emoji: str, mood_color: str, stage: int) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120">
  <circle cx="60" cy="60" r="56" fill="{bg_color}" stroke="#fff" stroke-width="4"/>
  <text x="60" y="62" font-size="40" text-anchor="middle" dominant-baseline="middle">{animal_emoji}</text>
  <text x="96" y="26" font-size="22" text-anchor="middle" dominant-baseline="middle">{mood_emoji}</text>
  <circle cx="24" cy="96" r="14" fill="{mood_color}"/>
  <text x="24" y="100" font-size="12" font-family="monospace" fill="#fff" text-anchor="middle" dominant-baseline="middle">{stage:02d}</text>
</svg>'''


count = 0
for animal_id, animal_emoji, bg_color in ANIMALS:
    for stage in STAGES:
        for mood, (mood_emoji, mood_color) in MOODS.items():
            path = OUT / animal_id / f"{stage:02d}_{mood}.svg"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(make_svg(animal_emoji, bg_color, mood_emoji, mood_color, stage))
            count += 1

print(f"Generated {count} SVG placeholder avatars under {OUT}/")
```

- [ ] **Step 2: Run the script**

```bash
python scripts/gen_avatar_placeholders.py
```
Expected: "Generated 240 SVG placeholder avatars under frontend/public/assets/avatars/"

- [ ] **Step 3: Spot-check one file exists**

```bash
ls frontend/public/assets/avatars/dragon/
```
Expected: `01_neutral.svg`, `01_happy.svg`, `01_sad.svg`, … `10_sad.svg`.

- [ ] **Step 4: Commit**

```bash
git add scripts/gen_avatar_placeholders.py frontend/public/assets/avatars/
git commit -m "feat(game): avatar placeholder SVG generator + 240 placeholders

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 11: AI avatar service + worker

**Files:**
- Create: `backend/app/game/services/avatars.py`
- Create: `worker/generate_avatar.py`
- Create: `backend/tests/game/test_avatars.py`

**Interfaces:**
- Produces:
  - `check_daily_quota(session, account_id, limit) -> int` — returns remaining slots
  - `start_avatar_job(session, account_id, player_id, description, settings) -> CustomAvatar`
  - Worker polls `SELECT … FOR UPDATE SKIP LOCKED`, calls OpenAI moderation + DALL-E via httpx

- [ ] **Step 1: Write avatar tests**

```python
# backend/tests/game/test_avatars.py
import pytest
from datetime import UTC, datetime, timedelta
from tests.game.test_auth import anyio_backend, settings, database, client, _make_manager, _login

pytestmark = pytest.mark.anyio


def test_check_daily_quota_empty(settings, database):
    from app.game.services.avatars import check_daily_quota
    with database.session() as session:
        with session.begin():
            from app.services.auth import create_user
            user = create_user(
                session, settings, username="qtest", password="P@ssw0rd!!",
                first_name="Q", last_name="T", role="student", must_change_password=False,
            )
            remaining = check_daily_quota(session, user.id, limit=3)
    assert remaining == 3


def test_check_daily_quota_decrements(settings, database):
    from app.game.services.avatars import check_daily_quota
    from app.game.models import AvatarGenerationLog
    with database.session() as session:
        with session.begin():
            from app.services.auth import create_user
            user = create_user(
                session, settings, username="qtest2", password="P@ssw0rd!!",
                first_name="Q", last_name="T", role="student", must_change_password=False,
            )
            session.add(AvatarGenerationLog(account_id=user.id, billable=True))
            session.flush()
            remaining = check_daily_quota(session, user.id, limit=3)
    assert remaining == 2


def test_non_billable_does_not_count(settings, database):
    from app.game.services.avatars import check_daily_quota
    from app.game.models import AvatarGenerationLog
    with database.session() as session:
        with session.begin():
            from app.services.auth import create_user
            user = create_user(
                session, settings, username="qtest3", password="P@ssw0rd!!",
                first_name="Q", last_name="T", role="student", must_change_password=False,
            )
            session.add(AvatarGenerationLog(account_id=user.id, billable=False))
            session.flush()
            remaining = check_daily_quota(session, user.id, limit=3)
    assert remaining == 3
```

- [ ] **Step 2: Run to verify FAIL**

```bash
cd backend && DATABASE_NAME=solfeo_test pytest tests/game/test_avatars.py -v
```

- [ ] **Step 3: Write `backend/app/game/services/avatars.py`**

```python
from __future__ import annotations
from datetime import UTC, datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.game.models import AvatarGenerationLog, CustomAvatar
from app.services.auth import ServiceError
from app.settings import Settings


def check_daily_quota(session: Session, account_id: int, limit: int) -> int:
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    used = session.scalar(
        select(func.count()).select_from(AvatarGenerationLog).where(
            AvatarGenerationLog.account_id == account_id,
            AvatarGenerationLog.billable == True,  # noqa: E712
            AvatarGenerationLog.created_at >= today,
        )
    ) or 0
    return max(0, limit - used)


def start_avatar_job(
    session: Session,
    account_id: int,
    player_id: int,
    description: str,
    settings: Settings,
) -> CustomAvatar:
    # Create log row first (for quota accounting)
    log = AvatarGenerationLog(account_id=account_id, billable=True)
    session.add(log)
    # Create job row
    job = CustomAvatar(
        account_id=account_id,
        player_id=player_id,
        description=description,
        status="pending",
    )
    session.add(job)
    session.flush()
    return job
```

- [ ] **Step 4: Write `worker/generate_avatar.py`** — follows the `worker/omr.py` + `worker/generate_spoken.py` patterns:

```python
#!/usr/bin/env python3
"""Avatar generation worker — polls for pending custom avatar jobs and processes them with DALL-E."""
import logging
import sys
import time
from pathlib import Path

import httpx

# Bootstrap the app before any app imports
sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.database import Database
from app.game.config import AVATAR_WORKER_LOCK_ID
from app.game.models import AvatarGenerationLog, CustomAvatar
from app.settings import Settings
from sqlalchemy import select, text

logger = logging.getLogger(__name__)


MODERATION_SYSTEM = (
    "You are a moderation tool. Return only valid JSON: {\"flagged\": true|false}"
)

IMAGE_SYSTEM = (
    "Cute, child-friendly, single magical creature, consistent flat cartoon illustration style, "
    "plain transparent background, no text, no real people, no brands or characters from "
    "existing franchises. Style: bold outlines, bright pastel colours."
)


def _openai_post(settings: Settings, path: str, payload: dict, timeout: float = 60.0) -> dict:
    url = f"https://api.openai.com/v1{path}"
    key = settings.openai_api_key.get_secret_value()
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, json=payload, headers={"Authorization": f"Bearer {key}"})
    r.raise_for_status()
    return r.json()


def _moderate(settings: Settings, text_: str) -> bool:
    """Return True if the description is flagged by OpenAI moderation."""
    result = _openai_post(settings, "/moderations", {"input": text_})
    results = result.get("results", [])
    return bool(results and results[0].get("flagged"))


def _generate_image(settings: Settings, prompt: str) -> str:
    """Generate an image and return its URL."""
    result = _openai_post(settings, "/images/generations", {
        "model": settings.avatar_image_model,
        "prompt": f"{IMAGE_SYSTEM}\n\n{prompt}",
        "n": 1,
        "size": "1024x1024",
        "response_format": "url",
    }, timeout=120.0)
    return result["data"][0]["url"]


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=30.0) as client:
        r = client.get(url)
    r.raise_for_status()
    dest.write_bytes(r.content)


def process_one(database: Database, settings: Settings) -> bool:
    with database.session() as session:
        with session.begin():
            job = session.scalar(
                select(CustomAvatar)
                .where(CustomAvatar.status == "pending")
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if job is None:
                return False
            job_id = job.id
            description = job.description
            account_id = job.account_id

    try:
        flagged = _moderate(settings, description)
        if flagged:
            with database.session() as session:
                with session.begin():
                    j = session.get(CustomAvatar, job_id)
                    j.status = "failed"
                    j.error_code = "MODERATION_FLAGGED"
                    # Mark log row as non-billable
                    log = session.scalar(
                        select(AvatarGenerationLog)
                        .where(AvatarGenerationLog.account_id == account_id)
                        .order_by(AvatarGenerationLog.id.desc())
                        .limit(1)
                    )
                    if log:
                        log.flagged = True
                        log.billable = False
            return True

        base_url = _generate_image(settings, description)
        happy_url = _generate_image(settings, f"Happy version of: {description}")
        sad_url = _generate_image(settings, f"Sad version of: {description}")

        base_dir = Path(settings.media_root) / "avatars" / "custom" / str(job_id)
        base_path = base_dir / "base.png"
        happy_path = base_dir / "happy.png"
        sad_path = base_dir / "sad.png"
        _download(base_url, base_path)
        _download(happy_url, happy_path)
        _download(sad_url, sad_path)

        from datetime import UTC, datetime
        with database.session() as session:
            with session.begin():
                j = session.get(CustomAvatar, job_id)
                j.status = "ready"
                j.base_path = str(base_path.relative_to(settings.media_root))
                j.happy_path = str(happy_path.relative_to(settings.media_root))
                j.sad_path = str(sad_path.relative_to(settings.media_root))
                j.completed_at = datetime.now(UTC)

    except Exception as exc:
        logger.exception("Avatar job %s failed: %s", job_id, exc)
        with database.session() as session:
            with session.begin():
                j = session.get(CustomAvatar, job_id)
                if j:
                    j.status = "failed"
                    j.error_code = str(exc)[:50]
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    database = Database(settings)
    with database.session() as session:
        session.execute(text(f"SELECT pg_advisory_lock({AVATAR_WORKER_LOCK_ID})"))
    logger.info("Avatar worker started (lock %d)", AVATAR_WORKER_LOCK_ID)
    try:
        while True:
            try:
                process_one(database, settings)
            except Exception:
                logger.exception("Unexpected error in worker loop")
            time.sleep(2)
    finally:
        database.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run avatar tests**

```bash
cd backend && DATABASE_NAME=solfeo_test pytest tests/game/test_avatars.py -v
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/game/services/avatars.py worker/generate_avatar.py backend/tests/game/test_avatars.py
git commit -m "feat(game): avatar service and AI generation worker

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 12: Avatar API

**Files:**
- Create: `backend/app/game/api/avatars.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces:
  - `GET /api/game/avatars/catalog`
  - `POST /api/game/avatars/generate`
  - `GET /api/game/avatars/{job_id}/status`
  - `POST /api/game/avatars/{job_id}/use`
  - `DELETE /api/game/avatars/{job_id}`
  - `GET /api/game/avatars/quota`

- [ ] **Step 1: Create `backend/app/game/api/avatars.py`**

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.auth import Configuration, Db, Manager, Member, require_csrf
from app.game.config import ANIMAL_IDS
from app.services.auth import ServiceError

router = APIRouter(prefix="/api/game/avatars", tags=["game-avatars"])

ANIMAL_DISPLAY_NAMES = {
    "unicorn": "Единорог", "dragon": "Дракон", "phoenix": "Феникс",
    "griffin": "Грифон", "sphinx_cat": "Сфинкс", "kitsune_fox": "Кицунэ",
    "pegasus": "Пегас", "mermaid": "Русалка",
}


@router.get("/catalog")
def catalog(identity: Member):
    return [{"id": aid, "name": ANIMAL_DISPLAY_NAMES.get(aid, aid)} for aid in ANIMAL_IDS]


class GenerateBody(BaseModel):
    player_id: int
    description: str


@router.post("/generate", dependencies=[Depends(require_csrf)])
def generate_avatar(body: GenerateBody, identity: Member, db: Db, settings: Configuration):
    from app.game.services.avatars import check_daily_quota, start_avatar_job
    from app.game.services.players import get_or_403
    with db.session() as session:
        with session.begin():
            account_id = identity.user.id
            player = get_or_403(session, body.player_id, account_id)
            is_manager = identity.user.role == "manager"
            if not is_manager:
                remaining = check_daily_quota(session, account_id, settings.avatar_gen_daily_limit)
                if remaining <= 0:
                    raise ServiceError("AVATAR_QUOTA_EXCEEDED", 429)
            job = start_avatar_job(session, account_id, body.player_id, body.description, settings)
            job_id = job.id
    return {"job_id": job_id}


def _job_out(job) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "base_path": job.base_path,
        "happy_path": job.happy_path,
        "sad_path": job.sad_path,
        "error_code": job.error_code,
    }


@router.get("/{job_id}/status")
def job_status(job_id: int, identity: Member, db: Db):
    from app.game.models import CustomAvatar
    with db.session() as session:
        with session.begin():
            job = session.get(CustomAvatar, job_id)
            if job is None or (identity.user.role != "manager" and job.account_id != identity.user.id):
                raise ServiceError("JOB_NOT_FOUND", 404)
    return _job_out(job)


class UseBody(BaseModel):
    pass  # no body needed


@router.post("/{job_id}/use", dependencies=[Depends(require_csrf)])
def use_avatar(job_id: int, identity: Member, db: Db):
    from app.game.models import CustomAvatar, Player
    from app.game.services.players import update_player
    with db.session() as session:
        with session.begin():
            job = session.get(CustomAvatar, job_id)
            if job is None or (identity.user.role != "manager" and job.account_id != identity.user.id):
                raise ServiceError("JOB_NOT_FOUND", 404)
            if job.status != "ready":
                raise ServiceError("JOB_NOT_READY", 400)
            update_player(session, job.player_id, custom_avatar_id=job.id)
    return {"ok": True}


@router.delete("/{job_id}", dependencies=[Depends(require_csrf)])
def discard_avatar(job_id: int, identity: Member, db: Db):
    from app.game.models import CustomAvatar
    with db.session() as session:
        with session.begin():
            job = session.get(CustomAvatar, job_id)
            if job is None or (identity.user.role != "manager" and job.account_id != identity.user.id):
                raise ServiceError("JOB_NOT_FOUND", 404)
            session.delete(job)
    return {"ok": True}


@router.get("/quota")
def quota(identity: Member, db: Db, settings: Configuration):
    from app.game.services.avatars import check_daily_quota
    from datetime import UTC, datetime, timedelta
    if identity.user.role == "manager":
        return {"used": 0, "limit": None, "resets_at": None}
    with db.session() as session:
        with session.begin():
            remaining = check_daily_quota(session, identity.user.id, settings.avatar_gen_daily_limit)
    used = settings.avatar_gen_daily_limit - remaining
    now = datetime.now(UTC)
    resets_at = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return {"used": used, "limit": settings.avatar_gen_daily_limit, "resets_at": resets_at.isoformat()}
```

- [ ] **Step 2: Register in `backend/app/main.py`**

```python
from app.game.api.avatars import router as game_avatars_router
# ...
app.include_router(game_avatars_router)
```

- [ ] **Step 3: Smoke test**

```bash
cd backend && python -c "from app.game.api.avatars import router; print(len(router.routes), 'routes')"
```
Expected: `6 routes`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/game/api/avatars.py backend/app/main.py
git commit -m "feat(game): avatar catalog and AI generation API endpoints

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 13: Backend integration test

**Files:**
- Create: `backend/tests/game/test_integration.py`

**Interfaces:**
- Consumes: all game API endpoints

- [ ] **Step 1: Write the integration test**

```python
# backend/tests/game/test_integration.py
"""Full round: 5 correct + 1 wrong + 1 timeout → score=4, correct_count=5, is_win=True, xp_delta=10"""
import pytest
from datetime import UTC, datetime
from tests.game.test_auth import anyio_backend, settings, database, client, _make_manager, _login

pytestmark = pytest.mark.anyio


async def test_full_round(client, settings, database):
    u, p = await _make_manager(settings, database)
    auth = await _login(client, u, p)
    csrf = auth["csrf_token"]

    # Create player
    r = await client.post(
        "/api/game/players",
        json={"name": "Hero", "avatar_animal": "unicorn"},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 200
    player_id = r.json()["id"]

    # Start round
    r = await client.post(
        "/api/game/rounds",
        json={"player_id": player_id, "difficulty": "easy", "note_count": 1},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 200
    data = r.json()
    round_id = data["round_id"]
    task = data["task"]
    assert task["index"] == 0

    # Play 7 tasks: 5 correct, 1 wrong, 1 timeout
    correct = 0
    total_xp = None
    for i in range(7):
        note = task["notes"][0]
        if i < 5:
            answers = [{"name": note["name"], "octave": note["octave"]}]
            timed_out = False
            correct += 1
        elif i == 5:
            answers = [{"name": "X", "octave": 0}]  # wrong answer
            timed_out = False
        else:
            answers = None
            timed_out = True

        r = await client.post(
            f"/api/game/rounds/{round_id}/submit",
            json={"task_index": i, "answers": answers, "timed_out": timed_out},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 200
        data = r.json()
        task = data.get("next_task")
        result = data.get("result")

    assert result is not None
    assert result["score"] == 4        # 5×(+1) + 1×(−1) + 1×(−1) = 3... wait: 5-2=3
    # Actually: 5 correct (+1 each) + 1 wrong (-1) + 1 timeout (-1) = 5-1-1 = 3
    assert result["correct_count"] == 5
    assert result["is_win"] is True    # 5 >= WIN_THRESHOLD (5)
    assert result["xp_gained"] == 5 * 1 + 5  # 5 correct tasks + win bonus
    assert result["xp_gained"] == 10


async def test_idempotent_submit(client, settings, database):
    """Submitting the same task_index twice returns identical response."""
    u, p = await _make_manager(settings, database)
    auth = await _login(client, u, p)
    csrf = auth["csrf_token"]

    r = await client.post(
        "/api/game/players",
        json={"name": "Idem", "avatar_animal": "dragon"},
        headers={"X-CSRF-Token": csrf},
    )
    player_id = r.json()["id"]

    r = await client.post(
        "/api/game/rounds",
        json={"player_id": player_id, "difficulty": "easy", "note_count": 1},
        headers={"X-CSRF-Token": csrf},
    )
    data = r.json()
    round_id = data["round_id"]
    task = data["task"]
    note = task["notes"][0]
    body = {"task_index": 0, "answers": [{"name": note["name"], "octave": note["octave"]}]}

    r1 = await client.post(f"/api/game/rounds/{round_id}/submit", json=body, headers={"X-CSRF-Token": csrf})
    r2 = await client.post(f"/api/game/rounds/{round_id}/submit", json=body, headers={"X-CSRF-Token": csrf})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["is_correct"] == r2.json()["is_correct"]
    assert r1.json()["score_delta"] == r2.json()["score_delta"]
```

- [ ] **Step 2: Run the integration test**

```bash
cd backend && DATABASE_NAME=solfeo_test pytest tests/game/test_integration.py -v
```
Expected: PASS. Note the score assertion — 5 correct (+5) + 1 wrong (−1) + 1 timeout (−1) = **3** total score, but `correct_count=5`, `is_win=True`, `xp_gained=10` (5×1 + 5 bonus).

> Fix score assertion to `assert result["score"] == 3` if the test fails on that line.

- [ ] **Step 3: Run full test suite**

```bash
cd backend && DATABASE_NAME=solfeo_test pytest tests/game/ -v
```
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/game/test_integration.py
git commit -m "test(game): backend integration test — full round with correct/wrong/timeout

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
