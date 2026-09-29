import secrets
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import Exercise, ListeningSession, MediaFile, StudentProgress, User
from app.services.auth import ServiceError
from app.services.exercises import get_exercise

Mode = Literal["sequential", "random"]
Direction = Literal["current", "next", "previous"]
Event = Literal["start", "heartbeat", "end", "ended"]


def progress_lock(session: Session, user_id: int) -> StudentProgress:
    session.execute(
        text("SELECT pg_advisory_xact_lock(710024003, :user_id)"), {"user_id": user_id}
    )
    progress = session.get(StudentProgress, user_id)
    if progress is None:
        progress = StudentProgress(user_id=user_id)
        session.add(progress)
    return progress


def active_ids(session: Session) -> list[int]:
    return list(
        session.scalars(
            select(Exercise.id)
            .where(Exercise.deleted_at.is_(None))
            .order_by(Exercise.position, Exercise.id)
        )
    )


def current(session: Session, user_id: int) -> Exercise | None:
    ids = active_ids(session)
    if not ids:
        return None
    progress = session.get(StudentProgress, user_id)
    identifier = progress.next_exercise_id if progress else None
    return get_exercise(session, identifier if identifier in ids else ids[0])


def choose(
    session: Session,
    user_id: int,
    mode: Mode,
    direction: Direction,
    current_id: int | None,
    previous_id: int | None,
) -> Exercise | None:
    progress = progress_lock(session, user_id)
    ids = active_ids(session)
    if not ids:
        progress.next_exercise_id = None
        progress.last_random_id = None
        session.commit()
        return None
    if mode == "random":
        if direction == "previous":
            if previous_id not in ids:
                raise ServiceError("EXERCISE_NOT_FOUND", 404)
            selected = previous_id
        else:
            last = current_id if current_id is not None else progress.last_random_id
            candidates = [identifier for identifier in ids if identifier != last]
            selected = secrets.choice(candidates or ids)
        progress.last_random_id = selected
    else:
        anchor = current_id if current_id in ids else progress.next_exercise_id
        if anchor in ids:
            index = ids.index(anchor)
            if direction != "current":
                index = (index + (1 if direction == "next" else -1)) % len(ids)
        else:
            index = 0
        selected = ids[index]
        progress.next_exercise_id = selected
    session.commit()
    return get_exercise(session, selected)


def record_event(
    session: Session,
    user_id: int,
    exercise_id: int,
    session_id: UUID,
    event: Event,
    position: float,
    mode: Mode,
    audio_id: UUID | None,
) -> ListeningSession:
    session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": session_id.int & ((1 << 63) - 1)},
    )
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
        )
        session.add(row)
    elif row.user_id != user_id:
        raise ServiceError("FORBIDDEN", 403)
    elif row.exercise_id != exercise_id or (
        audio_id is not None and row.audio_id != str(audio_id)
    ):
        raise ServiceError("LISTENING_SESSION_CONFLICT", 409)
    was_completed = row.completed
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
    if row.completed and not was_completed and mode == "sequential":
        progress = progress_lock(session, user_id)
        ids = active_ids(session)
        if exercise_id in ids and (
            progress.next_exercise_id not in ids
            or progress.next_exercise_id == exercise_id
        ):
            progress.next_exercise_id = ids[(ids.index(exercise_id) + 1) % len(ids)]
    session.commit()
    return row


def journal(
    session: Session,
    student_id: int | None,
    exercise_id: int | None,
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


def journal_options(session: Session) -> tuple[list[User], list[Exercise]]:
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
    return users, exercises
