import hashlib
import json
import logging
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import BinaryIO
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.orm import Session

from app.models import (
    MediaFile,
    TelegramLink,
    TelegramLinkCode,
    TelegramUpdate,
    User,
)
from app.services import exercises
from app.services.auth import ServiceError
from app.services.media import prepare_media
from app.settings import Settings

logger = logging.getLogger(__name__)


class Sender(BaseModel):
    id: int = Field(gt=0)
    language_code: str = ""


class Chat(BaseModel):
    id: int
    type: str


class Attachment(BaseModel):
    file_id: str = Field(min_length=1, max_length=512)
    file_size: int | None = Field(default=None, ge=0)
    file_name: str = ""
    title: str = ""


class Message(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    sender: Sender = Field(alias="from")
    chat: Chat
    text: str = ""
    caption: str = ""
    audio: Attachment | None = None
    voice: Attachment | None = None
    document: Attachment | None = None


class Update(BaseModel):
    update_id: int = Field(ge=0)
    message: Message | None = None


def manager(session: Session, user_id: int) -> User:
    user = session.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        user is None
        or not user.is_active
        or user.role != "manager"
        or user.must_change_password
    ):
        raise ServiceError("FORBIDDEN", 403)
    return user


def linking_lock(session: Session) -> None:
    session.execute(text("SELECT pg_advisory_xact_lock(710024004)"))


def create_code(
    session: Session, user_id: int, settings: Settings
) -> tuple[str, datetime]:
    linking_lock(session)
    manager(session, user_id)
    code = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(seconds=settings.telegram_link_seconds)
    session.execute(delete(TelegramLinkCode).where(TelegramLinkCode.user_id == user_id))
    session.add(
        TelegramLinkCode(
            user_id=user_id,
            token_hash=hashlib.sha256(code.encode()).hexdigest(),
            expires_at=expires,
        )
    )
    session.commit()
    return code, expires


def unlink(session: Session, user_id: int) -> None:
    linking_lock(session)
    manager(session, user_id)
    revoke_link(session, user_id)
    session.commit()


def revoke_link(session: Session, user_id: int) -> None:
    session.execute(delete(TelegramLinkCode).where(TelegramLinkCode.user_id == user_id))
    session.execute(delete(TelegramLink).where(TelegramLink.user_id == user_id))


def receive(session: Session, payload: object) -> TelegramUpdate | None:
    try:
        update = Update.model_validate(payload)
    except ValidationError:
        logger.warning("TELEGRAM_INVALID_UPDATE")
        return None
    message = update.message
    if (
        message is None
        or message.chat.type != "private"
        or message.chat.id != message.sender.id
    ):
        logger.warning("TELEGRAM_PRIVATE_CHAT_REQUIRED")
        return None
    linking_lock(session)
    existing = session.get(TelegramUpdate, update.update_id)
    if existing is not None:
        session.commit()
        return existing
    row = TelegramUpdate(id=update.update_id, chat_id=message.chat.id, status="message")
    language = message.sender.language_code.split("-")[0]
    row.language = language if language in {"en", "ru", "es"} else "en"
    if message.text.startswith("/start "):
        token = message.text.removeprefix("/start ").strip()
        code = session.scalar(
            select(TelegramLinkCode).where(
                TelegramLinkCode.token_hash
                == hashlib.sha256(token.encode()).hexdigest(),
                TelegramLinkCode.expires_at > datetime.now(UTC),
            )
        )
        row.reply_code = "invalid_link"
        if code is not None:
            try:
                user = manager(session, code.user_id)
            except ServiceError:
                logger.warning("TELEGRAM_ACCESS_DENIED")
            else:
                taken = session.scalar(
                    select(TelegramLink).where(
                        TelegramLink.sender_id == message.sender.id
                    )
                )
                if taken is None or taken.user_id == user.id:
                    session.execute(
                        delete(TelegramLink).where(TelegramLink.user_id == user.id)
                    )
                    session.add(
                        TelegramLink(user_id=user.id, sender_id=message.sender.id)
                    )
                    session.delete(code)
                    row.user_id, row.language, row.reply_code = (
                        user.id,
                        user.ui_language,
                        "linked",
                    )
    else:
        binding = session.scalar(
            select(TelegramLink).where(TelegramLink.sender_id == message.sender.id)
        )
        if binding is None:
            logger.warning("TELEGRAM_ACCESS_DENIED")
            row.reply_code = "link_required"
            session.add(row)
            session.commit()
            return row
        try:
            user = manager(session, binding.user_id)
        except ServiceError:
            logger.warning("TELEGRAM_ACCESS_DENIED")
            row.reply_code = "access_denied"
            session.add(row)
            session.commit()
            return row
        row.user_id, row.language = user.id, user.ui_language
        attachment = message.audio or message.voice or message.document
        if attachment is None:
            row.reply_code = "help"
        else:
            row.file_id = attachment.file_id
            row.title = (
                message.caption.splitlines()[0]
                if message.caption
                else attachment.title or attachment.file_name
            )[:200]
            row.description = message.caption[:10000]
            row.status = "pending"
            if attachment.file_size is not None and attachment.file_size > 20000000:
                row.status, row.last_error, row.reply_code = (
                    "failed",
                    "FILE_TOO_LARGE",
                    "error",
                )
    session.add(row)
    session.commit()
    return row


def process_one(
    session: Session, settings: Settings, download: Callable[[str], BinaryIO]
) -> bool:
    candidate = session.scalar(
        select(TelegramUpdate)
        .where(
            TelegramUpdate.status == "pending",
            or_(
                TelegramUpdate.next_attempt_at.is_(None),
                TelegramUpdate.next_attempt_at <= datetime.now(UTC),
            ),
        )
        .order_by(TelegramUpdate.id)
        .limit(1)
    )
    if candidate is None:
        session.rollback()
        return False
    try:
        if candidate.user_id is None:
            raise ServiceError("FORBIDDEN", 403)
        manager(session, candidate.user_id)
        binding = session.get(TelegramLink, candidate.user_id)
        if binding is None or binding.sender_id != candidate.chat_id:
            raise ServiceError("FORBIDDEN", 403)
    except ServiceError:
        candidate = session.scalar(
            select(TelegramUpdate)
            .where(
                TelegramUpdate.id == candidate.id, TelegramUpdate.status == "pending"
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if candidate is None:
            session.rollback()
            return False
        candidate.status, candidate.last_error, candidate.reply_code = (
            "failed",
            "FORBIDDEN",
            "error",
        )
        candidate.notified = False
        session.commit()
        return True
    row = session.scalar(
        select(TelegramUpdate)
        .where(TelegramUpdate.id == candidate.id, TelegramUpdate.status == "pending")
        .with_for_update(skip_locked=True)
        .execution_options(populate_existing=True)
    )
    if row is None:
        session.rollback()
        return False
    row.attempts += 1
    row.locked_at = datetime.now(UTC)
    try:
        if row.file_id is None:
            raise ServiceError("INVALID_MEDIA", 422)
        with download(row.file_id) as source:
            media = prepare_media(
                source,
                "audio",
                settings,
                uuid5(NAMESPACE_URL, f"solfeo:telegram:{row.id}"),
            )
        session.add(media)
        session.flush()
        row.media_id, row.status, row.last_error = media.id, "ready", None
        row.reply_code, row.notified = "ready", False
    except ServiceError as error:
        logger.warning("TELEGRAM_IMPORT_FAILED:%s", error.code)
        row.last_error = error.code
        if error.status >= 500 and row.attempts < settings.telegram_max_attempts:
            row.next_attempt_at = datetime.now(UTC) + timedelta(
                seconds=settings.telegram_retry_seconds
            )
        else:
            row.status, row.reply_code, row.notified = "failed", "error", False
    row.locked_at = None
    session.commit()
    return True


def owned_import(session: Session, user_id: int, identifier: int) -> TelegramUpdate:
    row = session.scalar(
        select(TelegramUpdate)
        .where(
            TelegramUpdate.id == identifier,
            TelegramUpdate.user_id == user_id,
            TelegramUpdate.file_id.is_not(None),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise ServiceError("IMPORT_NOT_FOUND", 404)
    return row


def list_imports(
    session: Session, user_id: int, offset: int, limit: int
) -> tuple[list[TelegramUpdate], int]:
    query = select(TelegramUpdate).where(
        TelegramUpdate.user_id == user_id, TelegramUpdate.file_id.is_not(None)
    )
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    return list(
        session.scalars(
            query.order_by(TelegramUpdate.id.desc()).offset(offset).limit(limit)
        )
    ), total


def apply_import(
    session: Session,
    user_id: int,
    identifier: int,
    exercise_id: int | None,
    title: str,
    description: str,
) -> int:
    manager(session, user_id)
    row = owned_import(session, user_id, identifier)
    request_hash = hashlib.sha256(
        json.dumps([exercise_id, title, description]).encode()
    ).hexdigest()
    if row.status == "applied" and row.exercise_id is not None:
        if row.applied_request != request_hash:
            raise ServiceError("IMPORT_ALREADY_APPLIED", 409)
        session.commit()
        return row.exercise_id
    if row.status != "ready" or row.media_id is None:
        raise ServiceError("IMPORT_NOT_READY", 409)
    exercises.lock(session)
    exercise = (
        exercises.get_exercise(session, exercise_id)
        if exercise_id
        else exercises.new_exercise(session)
    )
    exercise.title, exercise.description, exercise.audio_id = (
        title,
        description,
        row.media_id,
    )
    session.add(exercise)
    session.flush()
    row.exercise_id, row.applied_request, row.status = (
        exercise.id,
        request_hash,
        "applied",
    )
    session.commit()
    return exercise.id


def retry_import(session: Session, user_id: int, identifier: int) -> None:
    manager(session, user_id)
    row = owned_import(session, user_id, identifier)
    if row.status != "failed":
        raise ServiceError("IMPORT_NOT_READY", 409)
    row.status, row.attempts, row.next_attempt_at, row.last_error = (
        "pending",
        0,
        None,
        None,
    )
    session.commit()


def import_media(session: Session, user_id: int, identifier: int) -> MediaFile:
    row = owned_import(session, user_id, identifier)
    media = session.get(MediaFile, row.media_id) if row.media_id else None
    if media is None or row.status not in {"ready", "applied"}:
        raise ServiceError("FILE_NOT_FOUND", 404)
    return media
