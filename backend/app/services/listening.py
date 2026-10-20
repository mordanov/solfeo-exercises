from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import (
    Chapter,
    Exercise,
    ListeningRun,
    ListeningRunItem,
    ListeningSession,
    MediaFile,
    User,
)
from app.services.auth import ServiceError
from app.services.exercises import get_exercise

Event = Literal["start", "heartbeat", "end", "ended"]


def record_event(
    session: Session,
    user_id: int,
    run_id: int,
    exercise_id: int,
    session_id: UUID,
    event: Event,
    position: float,
    audio_id: UUID | None,
) -> ListeningSession:
    session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": session_id.int & ((1 << 63) - 1)},
    )
    run = session.scalar(
        select(ListeningRun).where(ListeningRun.id == run_id).with_for_update()
    )
    if run is None:
        raise ServiceError("LISTENING_RUN_NOT_FOUND", 404)
    if run.user_id != user_id:
        raise ServiceError("FORBIDDEN", 403)
    if run.status != "active":
        raise ServiceError("LISTENING_RUN_NOT_ACTIVE", 409)
    item = session.scalar(
        select(ListeningRunItem).where(
            ListeningRunItem.run_id == run.id,
            ListeningRunItem.position == run.current_index,
        )
    )
    if item is None or item.exercise_id != exercise_id:
        raise ServiceError("RUN_ITEM_NOT_CURRENT", 409)

    row = session.scalar(
        select(ListeningSession).where(ListeningSession.session_id == str(session_id))
    )
    now = datetime.now(UTC)
    if row is None:
        exercise = get_exercise(session, exercise_id)
        media = session.get(MediaFile, exercise.audio_id) if exercise.audio_id else None
        if media is None or media.duration_seconds is None:
            raise ServiceError("EXERCISE_HAS_NO_AUDIO", 422)
        if audio_id is not None and str(audio_id) != media.id:
            raise ServiceError("AUDIO_CHANGED", 409)
        row = ListeningSession(
            user_id=user_id,
            exercise_id=exercise_id,
            audio_id=media.id,
            exercise_title=exercise.title,
            session_id=str(session_id),
            started_at=now,
            last_heartbeat_at=now,
            max_position_sec=0,
            audio_duration_sec=media.duration_seconds,
            completed=False,
            chapter_number=item.chapter_number,
        )
        session.add(row)
    elif row.user_id != user_id:
        raise ServiceError("FORBIDDEN", 403)
    elif row.exercise_id != exercise_id or (
        audio_id is not None and row.audio_id != str(audio_id)
    ):
        raise ServiceError("LISTENING_SESSION_CONFLICT", 409)
    row.max_position_sec = max(
        row.max_position_sec, min(position, row.audio_duration_sec)
    )
    row.last_heartbeat_at = now
    row.completed = (
        row.completed
        or event == "ended"
        or row.max_position_sec >= 0.9 * row.audio_duration_sec
    )
    if event in ("end", "ended") and row.ended_at is None:
        row.ended_at = now
    session.commit()
    return row


def journal(
    session: Session,
    student_id: int | None,
    exercise_id: int | None,
    chapter_number: int | None,
    started_from: datetime | None,
    started_to: datetime | None,
    offset: int,
    limit: int,
) -> tuple[list[tuple[ListeningSession, User, Exercise]], int]:
    if started_from and started_to and started_from >= started_to:
        raise ServiceError("VALIDATION_ERROR", 422)
    query = (
        select(ListeningSession, User, Exercise)
        .join(User, User.id == ListeningSession.user_id)
        .join(Exercise, Exercise.id == ListeningSession.exercise_id)
    )
    if student_id is not None:
        query = query.where(ListeningSession.user_id == student_id)
    if exercise_id is not None:
        query = query.where(ListeningSession.exercise_id == exercise_id)
    if chapter_number is not None:
        query = query.where(ListeningSession.chapter_number == chapter_number)
    if started_from:
        query = query.where(ListeningSession.started_at >= started_from)
    if started_to:
        query = query.where(ListeningSession.started_at < started_to)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.execute(
        query.order_by(ListeningSession.started_at.desc(), ListeningSession.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return [(row, user, exercise) for row, user, exercise in rows], total


def journal_options(
    session: Session,
) -> tuple[list[User], list[Exercise], list[int]]:
    users = list(
        session.scalars(
            select(User)
            .join(ListeningSession, ListeningSession.user_id == User.id)
            .distinct()
            .order_by(User.username)
        )
    )
    exercises = list(
        session.scalars(
            select(Exercise)
            .join(ListeningSession, ListeningSession.exercise_id == Exercise.id)
            .distinct()
            .order_by(Exercise.title)
        )
    )
    chapters = set(session.scalars(select(Chapter.number).order_by(Chapter.number)))
    historical_chapters = set(
        session.scalars(
            select(ListeningSession.chapter_number)
            .distinct()
            .order_by(ListeningSession.chapter_number)
        )
    )
    return users, exercises, sorted(chapters | historical_chapters)
