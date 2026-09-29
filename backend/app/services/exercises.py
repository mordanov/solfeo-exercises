from datetime import UTC, datetime
from typing import BinaryIO

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import Exercise, MediaFile
from app.services.auth import ServiceError
from app.services.media import Kind, prepare_media
from app.settings import Settings


def lock(session: Session) -> None:
    session.execute(text("SELECT pg_advisory_xact_lock(710024002)"))


def get_exercise(session: Session, identifier: int) -> Exercise:
    result = session.scalar(
        select(Exercise)
        .where(Exercise.id == identifier, Exercise.deleted_at.is_(None))
        .execution_options(populate_existing=True)
    )
    if result is None:
        raise ServiceError("EXERCISE_NOT_FOUND", 404)
    return result


def list_exercises(
    session: Session, offset: int, limit: int
) -> tuple[list[Exercise], int]:
    query = select(Exercise).where(Exercise.deleted_at.is_(None))
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    return list(
        session.scalars(
            query.order_by(Exercise.position, Exercise.id).offset(offset).limit(limit)
        )
    ), total


def save_exercise(
    session: Session,
    settings: Settings,
    identifier: int | None,
    *,
    title: str,
    description: str,
    category: str | None,
    image: BinaryIO | None,
    audio: BinaryIO | None,
    remove_image: bool,
    remove_audio: bool,
) -> Exercise:
    if (image is not None and remove_image) or (audio is not None and remove_audio):
        raise ServiceError("VALIDATION_ERROR", 422)
    if identifier is not None:
        get_exercise(session, identifier)
    prepared: dict[Kind, MediaFile] = {}
    try:
        for kind, source in (("image", image), ("audio", audio)):
            if source is not None:
                typed_kind: Kind = "image" if kind == "image" else "audio"
                prepared[typed_kind] = prepare_media(source, typed_kind, settings)
        lock(session)
        session.add_all(prepared.values())
        session.flush()
        row = (
            get_exercise(session, identifier)
            if identifier is not None
            else Exercise(
                position=session.scalar(
                    select(func.count())
                    .select_from(Exercise)
                    .where(Exercise.deleted_at.is_(None))
                )
                or 0,
            )
        )
        row.title, row.description, row.category = title, description, category
        if remove_image:
            row.image_id = None
        if remove_audio:
            row.audio_id = None
        if "image" in prepared:
            row.image_id = prepared["image"].id
        if "audio" in prepared:
            row.audio_id = prepared["audio"].id
        if row.image_id is None and row.audio_id is None:
            raise ServiceError("EXERCISE_MEDIA_REQUIRED", 422)
        session.add(row)
        session.commit()
        return row
    except BaseException:
        session.rollback()
        for media in prepared.values():
            (settings.media_root / media.filename).unlink(missing_ok=True)
        raise


def reorder(session: Session, identifiers: list[int]) -> None:
    lock(session)
    rows = list(session.scalars(select(Exercise).where(Exercise.deleted_at.is_(None))))
    if len(identifiers) != len(set(identifiers)) or set(identifiers) != {
        row.id for row in rows
    }:
        raise ServiceError("EXERCISE_ORDER_CONFLICT", 409)
    positions = {identifier: index for index, identifier in enumerate(identifiers)}
    for row in rows:
        row.position = positions[row.id]
    session.commit()


def delete_exercise(session: Session, identifier: int) -> None:
    lock(session)
    get_exercise(session, identifier).deleted_at = datetime.now(UTC)
    session.flush()
    for index, row in enumerate(
        session.scalars(
            select(Exercise)
            .where(Exercise.deleted_at.is_(None))
            .order_by(Exercise.position, Exercise.id)
        )
    ):
        row.position = index
    session.commit()


def get_media(session: Session, identifier: int, kind: Kind) -> MediaFile:
    row = get_exercise(session, identifier)
    media_id = row.image_id if kind == "image" else row.audio_id
    media = session.get(MediaFile, media_id) if media_id else None
    if media is None:
        raise ServiceError("FILE_NOT_FOUND", 404)
    return media
