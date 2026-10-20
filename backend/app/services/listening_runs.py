import secrets
from typing import Literal, NoReturn

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Chapter,
    Exercise,
    ListeningRun,
    ListeningRunChapter,
    ListeningRunItem,
    User,
)
from app.services.auth import ServiceError


def _active_positions(session: Session, run_id: int, minimum: int = 0) -> list[int]:
    return list(
        session.scalars(
            select(ListeningRunItem.position)
            .join(Exercise, Exercise.id == ListeningRunItem.exercise_id)
            .where(
                ListeningRunItem.run_id == run_id,
                ListeningRunItem.position >= minimum,
                Exercise.deleted_at.is_(None),
            )
            .order_by(ListeningRunItem.position)
        )
    )


def _skip_deleted_current(session: Session, run: ListeningRun) -> bool:
    positions = _active_positions(session, run.id, run.current_index)
    if positions:
        if run.current_index != positions[0]:
            run.current_index = positions[0]
            return True
        return False

    item_count = (
        session.scalar(
            select(func.count())
            .select_from(ListeningRunItem)
            .where(ListeningRunItem.run_id == run.id)
        )
        or 0
    )
    run.current_index = item_count
    run.status = "completed"
    return True


def _locked_run(session: Session, user_id: int, run_id: int) -> ListeningRun:
    run = session.scalar(
        select(ListeningRun).where(ListeningRun.id == run_id).with_for_update()
    )
    if run is None:
        raise ServiceError("LISTENING_RUN_NOT_FOUND", 404)
    if run.user_id != user_id:
        raise ServiceError("FORBIDDEN", 403)
    if run.status != "active":
        raise ServiceError("LISTENING_RUN_NOT_ACTIVE", 409)
    return run


def _raise_after_completing_run(
    session: Session, error: ServiceError, completed_existing: bool
) -> NoReturn:
    if completed_existing:
        session.commit()
    raise error


def active_run(session: Session, user_id: int) -> ListeningRun | None:
    run = session.scalar(
        select(ListeningRun)
        .where(ListeningRun.user_id == user_id, ListeningRun.status == "active")
        .with_for_update()
    )
    if run is None:
        return None
    if _skip_deleted_current(session, run):
        session.commit()
    return run if run.status == "active" else None


def start_run(session: Session, user_id: int, chapter_ids: list[int]) -> ListeningRun:
    student = session.scalar(select(User).where(User.id == user_id).with_for_update())
    if student is None or student.role != "student":
        raise ServiceError("FORBIDDEN", 403)
    completed_existing = False
    existing = session.scalar(
        select(ListeningRun)
        .where(ListeningRun.user_id == user_id, ListeningRun.status == "active")
        .with_for_update()
    )
    if existing is not None:
        if _skip_deleted_current(session, existing):
            completed_existing = existing.status == "completed"
            if not completed_existing:
                session.commit()
        if existing.status == "active":
            return existing
    if not chapter_ids or any(chapter_id <= 0 for chapter_id in chapter_ids):
        _raise_after_completing_run(
            session, ServiceError("VALIDATION_ERROR", 422), completed_existing
        )
    if len(set(chapter_ids)) != len(chapter_ids):
        _raise_after_completing_run(
            session, ServiceError("DUPLICATE_CHAPTER_ID", 422), completed_existing
        )

    chapters = list(
        session.scalars(
            select(Chapter).where(Chapter.id.in_(chapter_ids)).order_by(Chapter.number)
        )
    )
    if {chapter.id for chapter in chapters} != set(chapter_ids):
        _raise_after_completing_run(
            session, ServiceError("CHAPTER_NOT_FOUND", 404), completed_existing
        )

    pool = list(
        session.execute(
            select(Exercise.id, Exercise.chapter_id, Chapter.number)
            .join(Chapter, Chapter.id == Exercise.chapter_id)
            .where(
                Exercise.chapter_id.in_(chapter_ids),
                Exercise.deleted_at.is_(None),
            )
        )
    )
    if {chapter_id for _, chapter_id, _ in pool} != set(chapter_ids):
        _raise_after_completing_run(
            session, ServiceError("CHAPTER_UNAVAILABLE", 409), completed_existing
        )

    chapter_number_by_exercise = {
        exercise_id: chapter_number for exercise_id, _, chapter_number in pool
    }
    exercise_ids = [exercise_id for exercise_id, _, _ in pool]
    selected_ids = secrets.SystemRandom().sample(
        exercise_ids, k=min(10, len(exercise_ids))
    )

    run = ListeningRun(user_id=user_id, status="active", current_index=0)
    session.add(run)
    session.flush()
    session.add_all(
        ListeningRunChapter(run_id=run.id, chapter_number=chapter.number)
        for chapter in chapters
    )
    session.add_all(
        ListeningRunItem(
            run_id=run.id,
            position=position,
            exercise_id=exercise_id,
            chapter_number=chapter_number_by_exercise[exercise_id],
        )
        for position, exercise_id in enumerate(selected_ids)
    )
    session.commit()
    return run


def move_run(
    session: Session,
    user_id: int,
    run_id: int,
    direction: Literal["next", "previous"],
) -> ListeningRun:
    run = _locked_run(session, user_id, run_id)
    skipped_current = _skip_deleted_current(session, run)
    if run.status != "active":
        session.commit()
        return run
    if skipped_current and direction == "next":
        session.commit()
        return run

    if direction == "next":
        candidate = _active_positions(session, run.id, run.current_index + 1)
        if candidate:
            run.current_index = candidate[0]
        else:
            item_count = (
                session.scalar(
                    select(func.count())
                    .select_from(ListeningRunItem)
                    .where(ListeningRunItem.run_id == run.id)
                )
                or 0
            )
            run.current_index = item_count
            run.status = "completed"
    else:
        previous_positions = list(
            session.scalars(
                select(ListeningRunItem.position)
                .join(Exercise, Exercise.id == ListeningRunItem.exercise_id)
                .where(
                    ListeningRunItem.run_id == run.id,
                    ListeningRunItem.position < run.current_index,
                    Exercise.deleted_at.is_(None),
                )
                .order_by(ListeningRunItem.position.desc())
            )
        )
        if previous_positions:
            run.current_index = previous_positions[0]
    session.commit()
    return run


def cancel_run(session: Session, user_id: int, run_id: int) -> ListeningRun:
    run = _locked_run(session, user_id, run_id)
    run.status = "cancelled"
    session.commit()
    return run
