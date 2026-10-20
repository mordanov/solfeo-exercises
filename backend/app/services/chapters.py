from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Chapter, Exercise
from app.services.auth import ServiceError


def list_chapters(session: Session, *, nonempty_only: bool) -> list[Chapter]:
    query = select(Chapter).order_by(Chapter.number)
    if nonempty_only:
        query = query.where(
            Chapter.id.in_(
                select(Exercise.chapter_id).where(Exercise.deleted_at.is_(None))
            )
        )
    return list(session.scalars(query))


def exercise_counts(
    session: Session, chapter_ids: list[int]
) -> dict[int, tuple[int, int]]:
    if not chapter_ids:
        return {}
    rows = session.execute(
        select(
            Exercise.chapter_id,
            func.count(Exercise.id).filter(Exercise.deleted_at.is_(None)),
            func.count(Exercise.id),
        )
        .where(Exercise.chapter_id.in_(chapter_ids))
        .group_by(Exercise.chapter_id)
    )
    return {
        chapter_id: (active_count, assigned_count)
        for chapter_id, active_count, assigned_count in rows
    }


def create_chapter(session: Session) -> Chapter:
    number = session.execute(text("SELECT nextval('chapter_number_seq')")).scalar_one()
    chapter = Chapter(number=number)
    session.add(chapter)
    session.commit()
    return chapter


def delete_chapter(session: Session, chapter_id: int) -> None:
    chapter = session.get(Chapter, chapter_id)
    if chapter is None:
        raise ServiceError("CHAPTER_NOT_FOUND", 404)
    assigned_count = (
        session.scalar(
            select(func.count())
            .select_from(Exercise)
            .where(Exercise.chapter_id == chapter_id)
        )
        or 0
    )
    if assigned_count:
        raise ServiceError("CHAPTER_NOT_EMPTY", 409)
    session.delete(chapter)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        if constraint == "fk_exercises_chapter_id_chapters":
            raise ServiceError("CHAPTER_NOT_EMPTY", 409) from error
        raise
