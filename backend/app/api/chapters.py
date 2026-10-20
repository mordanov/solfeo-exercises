from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.auth import (
    Db,
    ExerciseMember,
    Manager,
    StatusOutput,
    require_csrf,
)
from app.models import Chapter
from app.services import chapters

router = APIRouter(prefix="/api/chapters")


class ChapterOutput(BaseModel):
    id: int
    number: int
    active_exercise_count: int
    assigned_exercise_count: int


class ChapterListOutput(BaseModel):
    chapters: list[ChapterOutput]


def output(chapter: Chapter, counts: tuple[int, int] = (0, 0)) -> ChapterOutput:
    return ChapterOutput(
        id=chapter.id,
        number=chapter.number,
        active_exercise_count=counts[0],
        assigned_exercise_count=counts[1],
    )


@router.get("")
def listing(member: ExerciseMember, session: Db) -> ChapterListOutput:
    rows = chapters.list_chapters(session, nonempty_only=member.user.role == "student")
    counts = chapters.exercise_counts(session, [row.id for row in rows])
    return ChapterListOutput(
        chapters=[output(row, counts.get(row.id, (0, 0))) for row in rows]
    )


@router.post("", status_code=201, dependencies=[Depends(require_csrf)])
def create(_manager: Manager, session: Db) -> ChapterOutput:
    return output(chapters.create_chapter(session))


@router.delete("/{chapter_id}", dependencies=[Depends(require_csrf)])
def delete(chapter_id: int, _manager: Manager, session: Db) -> StatusOutput:
    chapters.delete_chapter(session, chapter_id)
    return StatusOutput()
