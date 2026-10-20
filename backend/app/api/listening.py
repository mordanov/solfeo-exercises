import hmac
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import AwareDatetime, BaseModel

from app.api.auth import (
    Configuration,
    Db,
    Manager,
    Member,
    require_origin,
)
from app.api.listening_runs import RunEventInput
from app.models import ListeningSession
from app.services import listening
from app.services.auth import Identity, ServiceError

router = APIRouter(prefix="/api")


def require_student(member: Member) -> Identity:
    if member.user.role != "student":
        raise ServiceError("FORBIDDEN", 403)
    return member


Student = Annotated[Identity, Depends(require_student)]


class EventOutput(BaseModel):
    session_id: str
    completed: bool
    ended_at: datetime | None


class JournalOutput(BaseModel):
    id: int
    session_id: str
    user_id: int
    username: str
    first_name: str
    last_name: str
    exercise_id: int
    exercise_title: str
    exercise_deleted: bool
    started_at: datetime
    last_heartbeat_at: datetime
    ended_at: datetime | None
    max_position_sec: float
    audio_duration_sec: float
    completed: bool


class JournalListOutput(BaseModel):
    sessions: list[JournalOutput]
    total: int


class OptionOutput(BaseModel):
    id: int
    label: str
    deleted: bool = False


class OptionsOutput(BaseModel):
    students: list[OptionOutput]
    exercises: list[OptionOutput]


@router.post("/listening/events")
def event(
    data: RunEventInput,
    student: Student,
    session: Db,
    request: Request,
    settings: Configuration,
) -> EventOutput:
    require_origin(request, settings)
    if not hmac.compare_digest(
        data.csrf_token.encode(), student.session.csrf_token.encode()
    ):
        raise ServiceError("CSRF_FAILED", 403)
    row = listening.record_event(
        session,
        student.user.id,
        data.run_id,
        data.exercise_id,
        data.session_id,
        data.event,
        data.position_seconds,
        data.audio_id,
    )
    return EventOutput(
        session_id=row.session_id, completed=row.completed, ended_at=row.ended_at
    )


@router.get("/journal")
def journal(
    _manager: Manager,
    session: Db,
    student_id: Annotated[int | None, Query(gt=0)] = None,
    exercise_id: Annotated[int | None, Query(gt=0)] = None,
    started_from: AwareDatetime | None = None,
    started_to: AwareDatetime | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> JournalListOutput:
    rows, total = listening.journal(
        session, student_id, exercise_id, started_from, started_to, offset, limit
    )
    entries = []
    for row, user, exercise in rows:
        values = {
            key: getattr(row, key)
            for key in ListeningSession.__mapper__.columns.keys()
            if key in JournalOutput.model_fields
        }
        entries.append(
            JournalOutput.model_validate(
                {
                    **values,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "exercise_deleted": exercise.deleted_at is not None,
                }
            )
        )
    return JournalListOutput(sessions=entries, total=total)


@router.get("/journal/options")
def options(_manager: Manager, session: Db) -> OptionsOutput:
    users, exercises = listening.journal_options(session)
    return OptionsOutput(
        students=[
            OptionOutput(
                id=user.id,
                label=f"{user.first_name} {user.last_name} ({user.username})",
            )
            for user in users
        ],
        exercises=[
            OptionOutput(id=row.id, label=row.title, deleted=row.deleted_at is not None)
            for row in exercises
        ],
    )
