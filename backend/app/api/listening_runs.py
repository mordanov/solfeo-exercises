from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.auth import Db, Input, Member, require_csrf
from app.api.chapters import ChapterListOutput
from app.api.chapters import output as chapter_output
from app.api.exercises import ExerciseOutput
from app.api.exercises import output as exercise_output
from app.models import Exercise, ListeningRun, ListeningRunChapter, ListeningRunItem
from app.services import chapters, listening_runs
from app.services.auth import Identity, ServiceError
from app.services.listening import Event

router = APIRouter(prefix="/api/listening")
RunStatus = Literal["active", "completed", "cancelled"]


class RunStartInput(Input):
    chapter_ids: list[int] = Field(min_length=1)


class RunNavigationInput(Input):
    direction: Literal["next", "previous"]


class RunItemOutput(BaseModel):
    position: int
    chapter_number: int
    exercise: ExerciseOutput


class ListeningRunOutput(BaseModel):
    id: int
    status: RunStatus
    chapter_numbers: list[int]
    current_index: int
    items: list[RunItemOutput]


class JournalChapterOption(BaseModel):
    chapter_number: int


class RunEventInput(Input):
    run_id: int = Field(gt=0)
    session_id: UUID
    exercise_id: int = Field(gt=0)
    audio_id: UUID | None = None
    event: Event
    position_seconds: float = Field(ge=0, allow_inf_nan=False)
    csrf_token: str = Field(min_length=1, max_length=128, repr=False)


def require_student(member: Member) -> Identity:
    if member.user.role != "student":
        raise ServiceError("FORBIDDEN", 403)
    return member


Student = Annotated[Identity, Depends(require_student)]


def run_output(run: ListeningRun, session: Db) -> ListeningRunOutput:
    chapter_numbers = list(
        session.scalars(
            select(ListeningRunChapter.chapter_number)
            .where(ListeningRunChapter.run_id == run.id)
            .order_by(ListeningRunChapter.chapter_number)
        )
    )
    rows = session.execute(
        select(ListeningRunItem, Exercise)
        .join(Exercise, Exercise.id == ListeningRunItem.exercise_id)
        .where(
            ListeningRunItem.run_id == run.id,
            Exercise.deleted_at.is_(None),
        )
        .order_by(ListeningRunItem.position)
    )
    items = [
        RunItemOutput(
            position=item.position,
            chapter_number=item.chapter_number,
            exercise=exercise_output(exercise, session, item.chapter_number),
        )
        for item, exercise in rows
    ]
    return ListeningRunOutput(
        id=run.id,
        status=cast(RunStatus, run.status),
        chapter_numbers=chapter_numbers,
        current_index=run.current_index,
        items=items,
    )


@router.get("/chapters", response_model=ChapterListOutput)
def listening_chapters(_student: Student, session: Db) -> ChapterListOutput:
    rows = chapters.list_chapters(session, nonempty_only=True)
    counts = chapters.exercise_counts(session, [row.id for row in rows])
    return ChapterListOutput(
        chapters=[chapter_output(row, counts.get(row.id, (0, 0))) for row in rows]
    )


@router.get("/run", response_model=ListeningRunOutput | None)
def current_run(_student: Student, session: Db) -> ListeningRunOutput | None:
    run = listening_runs.active_run(session, _student.user.id)
    return run_output(run, session) if run is not None else None


@router.post(
    "/run",
    response_model=ListeningRunOutput,
    dependencies=[Depends(require_csrf)],
)
def start_run(data: RunStartInput, student: Student, session: Db) -> ListeningRunOutput:
    run = listening_runs.start_run(session, student.user.id, data.chapter_ids)
    return run_output(run, session)


@router.post(
    "/run/{run_id}/navigate",
    response_model=ListeningRunOutput,
    dependencies=[Depends(require_csrf)],
)
def navigate_run(
    run_id: int,
    data: RunNavigationInput,
    student: Student,
    session: Db,
) -> ListeningRunOutput:
    run = listening_runs.move_run(session, student.user.id, run_id, data.direction)
    return run_output(run, session)


@router.post(
    "/run/{run_id}/cancel",
    response_model=ListeningRunOutput,
    dependencies=[Depends(require_csrf)],
)
def cancel_run(run_id: int, student: Student, session: Db) -> ListeningRunOutput:
    run = listening_runs.cancel_run(session, student.user.id, run_id)
    return run_output(run, session)
