import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from app.models import Exercise, MediaFile, OmrJob
from app.services.auth import ServiceError
from app.settings import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Claim:
    id: str
    token: str
    exercise_id: int
    image_id: str
    filename: str


def active_exercise(session: Session, identifier: int) -> Exercise:
    exercise = session.scalar(
        select(Exercise)
        .where(Exercise.id == identifier, Exercise.deleted_at.is_(None))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if exercise is None:
        raise ServiceError("EXERCISE_NOT_FOUND", 404)
    return exercise


def current(session: Session, exercise: Exercise) -> OmrJob | None:
    if exercise.image_id is None:
        return None
    return session.scalar(
        select(OmrJob)
        .where(
            OmrJob.exercise_id == exercise.id,
            OmrJob.image_id == exercise.image_id,
            OmrJob.is_current.is_(True),
        )
        .execution_options(populate_existing=True)
    )


def enqueue(session: Session, exercise: Exercise) -> OmrJob | None:
    session.execute(
        update(OmrJob)
        .where(OmrJob.exercise_id == exercise.id, OmrJob.is_current.is_(True))
        .values(is_current=False)
    )
    if exercise.image_id is None:
        return None
    job = OmrJob(
        id=str(uuid4()),
        exercise_id=exercise.id,
        image_id=exercise.image_id,
        status="pending",
    )
    session.add(job)
    session.flush()
    return job


def rerun(session: Session, identifier: int) -> OmrJob:
    exercise = active_exercise(session, identifier)
    if exercise.image_id is None:
        raise ServiceError("OMR_IMAGE_REQUIRED", 422)
    job = current(session, exercise)
    if job is None or job.status not in {"pending", "processing"}:
        job = enqueue(session, exercise)
    assert job is not None
    session.commit()
    return job


def claim(session: Session, settings: Settings) -> Claim | None:
    now = datetime.now(UTC)
    job = session.scalar(
        select(OmrJob)
        .where(
            OmrJob.is_current.is_(True),
            or_(
                and_(
                    OmrJob.status == "pending",
                    or_(
                        OmrJob.next_attempt_at.is_(None), OmrJob.next_attempt_at <= now
                    ),
                ),
                and_(
                    OmrJob.status == "processing",
                    OmrJob.locked_at
                    <= now - timedelta(seconds=settings.omr_lease_seconds),
                ),
            ),
        )
        .order_by(OmrJob.created_at, OmrJob.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if job is None:
        session.rollback()
        return None
    exercise = session.get(Exercise, job.exercise_id)
    if (
        exercise is None
        or exercise.deleted_at is not None
        or exercise.image_id != job.image_id
    ):
        job.is_current, job.status, job.last_error = False, "failed", "OMR_SUPERSEDED"
        session.commit()
        return None
    if job.attempts >= settings.omr_max_attempts:
        job.status, job.last_error = "failed", "OMR_LEASE_EXPIRED"
        session.commit()
        return None
    image = session.get(MediaFile, job.image_id)
    if image is None:
        job.status, job.last_error = "failed", "FILE_NOT_FOUND"
        session.commit()
        return None
    job.attempts += 1
    job.status, job.locked_at, job.lease_token = "processing", now, str(uuid4())
    result = Claim(
        job.id, job.lease_token, job.exercise_id, job.image_id, image.filename
    )
    session.commit()
    return result


def validate_musicxml(data: bytes, maximum: int) -> bytes:
    try:
        if not data or len(data) > maximum:
            raise ValueError("SIZE")
        content = data.decode("utf-8")
        if "<!ENTITY" in content.upper():
            raise ValueError("ENTITY")
        root = ET.fromstring(content)
        if root.tag != "score-partwise" or root.find("part-list") is None:
            raise ValueError("ROOT")
        notes = root.findall("./part/measure/note")
        if not notes or len(notes) > 2000:
            raise ValueError("NOTES")
        for note in notes:
            pitch = note.find("pitch")
            if pitch is not None:
                if not re.fullmatch("[A-G]", pitch.findtext("step", "")):
                    raise ValueError("PITCH")
                if not re.fullmatch("[0-9]", pitch.findtext("octave", "")):
                    raise ValueError("OCTAVE")
            elif note.find("rest") is None:
                raise ValueError("UNSUPPORTED_NOTE")
        for element in root.iter():
            if element.tag in {"script", "image", "credit-image", "link"}:
                raise ValueError("EXTERNAL_CONTENT")
            if any("href" in name or name == "source" for name in element.attrib):
                raise ValueError("EXTERNAL_CONTENT")
    except (ET.ParseError, ValueError, UnicodeError):
        raise ServiceError("OMR_INVALID_SCORE", 422) from None
    return ET.tostring(root, encoding="unicode", xml_declaration=True).encode("utf-8")


def owned_claim(session: Session, work: Claim) -> OmrJob | None:
    exercise = session.scalar(
        select(Exercise)
        .where(Exercise.id == work.exercise_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    job = session.scalar(
        select(OmrJob)
        .where(
            OmrJob.id == work.id,
            OmrJob.lease_token == work.token,
            OmrJob.status == "processing",
            OmrJob.is_current.is_(True),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        job is None
        or exercise is None
        or exercise.deleted_at is not None
        or exercise.image_id != work.image_id
    ):
        return None
    return job


def complete(session: Session, settings: Settings, work: Claim, data: bytes) -> bool:
    validated = validate_musicxml(data, settings.omr_max_xml_bytes)
    job = owned_claim(session, work)
    if job is None:
        session.rollback()
        return False
    root = settings.media_root / "scores"
    root.mkdir(parents=True, exist_ok=True)
    filename = work.token + ".musicxml"
    destination = root / filename
    destination.write_bytes(validated)
    destination.chmod(0o644)
    job.score_filename, job.status = filename, "needs_review"
    job.last_error, job.locked_at, job.lease_token = None, None, None
    session.commit()
    return True


def fail(
    session: Session, settings: Settings, work: Claim, code: str, *, retryable: bool
) -> None:
    job = owned_claim(session, work)
    if job is None:
        session.rollback()
        return
    logger.warning("OMR_JOB_FAILED:%s", code)
    job.last_error, job.locked_at, job.lease_token = code, None, None
    job.status = (
        "pending"
        if retryable and job.attempts < settings.omr_max_attempts
        else "failed"
    )
    job.next_attempt_at = datetime.now(UTC) + timedelta(
        seconds=settings.omr_retry_seconds
    )
    session.commit()


def review(
    session: Session, identifier: int, job_id: str, user_id: int, action: str
) -> OmrJob:
    exercise = active_exercise(session, identifier)
    job = current(session, exercise)
    if job is None or job.id != job_id:
        raise ServiceError("OMR_STALE", 409)
    if job.score_filename is None or job.status not in {
        "needs_review",
        "approved",
        "rejected",
    }:
        raise ServiceError("OMR_NOT_READY", 409)
    job.status = "approved" if action == "approve" else "rejected"
    job.reviewed_by, job.reviewed_at = user_id, datetime.now(UTC)
    session.commit()
    return job


def score_file(
    session: Session,
    identifier: int,
    version: str,
    is_manager: bool,
    settings: Settings,
) -> Path:
    exercise = active_exercise(session, identifier)
    job = current(session, exercise)
    if job is None or job.id != version:
        raise ServiceError("OMR_STALE", 409)
    if not is_manager and job.status != "approved":
        raise ServiceError("FORBIDDEN", 403)
    if job.score_filename is None or job.status not in {
        "needs_review",
        "approved",
        "rejected",
    }:
        raise ServiceError("OMR_NOT_READY", 409)
    path = settings.media_root / "scores" / job.score_filename
    if not path.is_file():
        raise ServiceError("FILE_NOT_FOUND", 404)
    return path
