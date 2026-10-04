from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from app.api.auth import Configuration, Db, Member, require_csrf
from app.game.models import Player, Round, Season, TaskAttempt
from app.services.auth import ServiceError

router = APIRouter(prefix="/api/game/rounds", tags=["game-rounds"])


class CreateRoundBody(BaseModel):
    player_id: int
    difficulty: str
    note_count: int
    show_sound_hint: bool = True
    show_correct_answer: bool = False


class NoteAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Literal["C", "D", "E", "F", "G", "A", "B"]
    octave: Annotated[int, Field(strict=True, ge=2, le=5)]


class SubmitTaskBody(BaseModel):
    task_index: Annotated[int, Field(strict=True, ge=0, le=6)]
    answers: Annotated[list[NoteAnswer], Field(min_length=1, max_length=4)] | None = (
        None
    )
    timed_out: bool = False

    @model_validator(mode="after")
    def require_answers(self) -> Self:
        if not self.timed_out and self.answers is None:
            raise ValueError("INVALID_ANSWERS")
        return self


@router.post("", dependencies=[Depends(require_csrf)])
def create_round(
    body: CreateRoundBody,
    identity: Member,
    session: Db,
    settings: Configuration,
) -> dict[str, object]:
    from app.game.services.players import get_or_403
    from app.game.services.rounds import create_round as svc_create
    from app.game.services.rounds import task_payload

    if body.difficulty not in ("easy", "medium", "hard"):
        raise ServiceError("INVALID_DIFFICULTY", 422)
    if body.note_count not in (1, 2, 3, 4):
        raise ServiceError("INVALID_NOTE_COUNT", 422)

    with session.begin():
        if identity.user.role == "manager":
            player = session.get(Player, body.player_id)
            if player is None:
                raise ServiceError("PLAYER_NOT_FOUND", 404)
        else:
            player = get_or_403(session, body.player_id, identity.user.id)

        season = session.scalar(
            select(Season).where(
                Season.player_id == player.id, Season.ended_at.is_(None)
            )
        )
        if season is None:
            raise ServiceError("NO_ACTIVE_SEASON", 400)

        note_naming: str = identity.user.note_naming
        rnd, tasks = svc_create(
            session,
            player.id,
            season.id,
            body.difficulty,
            body.note_count,
            note_naming,
            settings,
            show_sound_hint=body.show_sound_hint,
            show_correct_answer=body.show_correct_answer,
        )
        first_attempt = session.scalar(
            select(TaskAttempt).where(
                TaskAttempt.round_id == rnd.id, TaskAttempt.task_index == 0
            )
        )
        if first_attempt is not None:
            first_task = task_payload(first_attempt, rnd.difficulty, rnd.created_at)
        else:
            raise ServiceError("TASK_NOT_FOUND", 404)

    return {
        "round_id": rnd.id,
        "task": first_task,
    }


@router.post("/{round_id}/submit", dependencies=[Depends(require_csrf)])
def submit_task(
    round_id: int,
    body: SubmitTaskBody,
    identity: Member,
    session: Db,
    settings: Configuration,
) -> dict[str, object]:
    from app.game.services.rounds import submit_task as svc_submit

    with session.begin():
        rnd = session.get(Round, round_id)
        if rnd is None:
            raise ServiceError("ROUND_NOT_FOUND", 404)
        player = session.get(Player, rnd.player_id)
        if identity.user.role != "manager" and (
            player is None or player.account_id != identity.user.id
        ):
            raise ServiceError("ROUND_NOT_FOUND", 404)

        result = svc_submit(
            session,
            round_id,
            body.task_index,
            [note.model_dump() for note in body.answers]
            if body.answers is not None
            else None,
            body.timed_out,
            datetime.now(UTC),
            settings,
        )
    return result
