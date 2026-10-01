import logging
import sys
import time
from datetime import UTC, datetime

import httpx
from pydantic import ValidationError
from sqlalchemy import or_, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.database import Database
from app.logging import configure_logging
from app.models import TelegramState, TelegramUpdate
from app.services.auth import ServiceError
from app.services.telegram import Update, process_one, receive
from app.services.telegram_api import TelegramApi
from app.settings import Settings

logger = logging.getLogger("worker.telegram")
TEXTS = {
    "en": {
        "link_required": (
            "Open Telegram imports in your manager account on the website. "
            "Create a linking code and send its command here."
        ),
        "access_denied": "Access denied. An active manager account is required.",
        "linked": "Telegram linked. Send audio, voice, or an audio document.",
        "invalid_link": "Invalid or expired code. Create a new code on the website.",
        "help": "Send an audio attachment, not a link. Maximum: 20 MB.",
        "received": "Audio queued. Open Telegram imports on the website.",
        "ready": "Audio saved. Open Telegram imports to create or update an exercise.",
        "error": "Import failed. Open Telegram imports for the error and retry.",
    },
    "ru": {
        "link_required": (
            "Откройте импорт Telegram в кабинете менеджера на сайте. "
            "Создайте код привязки и отправьте его команду сюда."
        ),
        "access_denied": "Доступ запрещён. Нужен активный аккаунт менеджера.",
        "linked": (
            "Telegram привязан. Отправьте аудио, голосовое сообщение или аудиофайл."
        ),
        "invalid_link": "Код неверен или истёк. Создайте новый код на сайте.",
        "help": "Отправьте аудиовложение, а не ссылку. Максимум: 20 МБ.",
        "received": "Аудио в очереди. Откройте импорт Telegram на сайте.",
        "ready": (
            "Аудио сохранено. Откройте импорт Telegram "
            "для создания или изменения упражнения."
        ),
        "error": (
            "Импорт не выполнен. Откройте импорт Telegram "
            "для просмотра ошибки и повтора."
        ),
    },
    "es": {
        "link_required": (
            "Abre las importaciones de Telegram en tu cuenta de gestor. "
            "Crea un código de vinculación y envía su comando aquí."
        ),
        "access_denied": "Acceso denegado. Se requiere una cuenta de gestor activa.",
        "linked": (
            "Telegram vinculado. Envía audio, una nota de voz o un archivo de audio."
        ),
        "invalid_link": "Código inválido o caducado. Crea otro código en el sitio web.",
        "help": "Envía un archivo de audio, no un enlace. Máximo: 20 MB.",
        "received": (
            "Audio en cola. Abre las importaciones de Telegram en el sitio web."
        ),
        "ready": (
            "Audio guardado. Abre las importaciones "
            "para crear o actualizar un ejercicio."
        ),
        "error": (
            "La importación falló. Abre las importaciones "
            "para ver el error y reintentar."
        ),
    },
}


def healthy(settings: Settings, database: Database) -> bool:
    if not settings.telegram_token.get_secret_value():
        return True
    if not settings.telegram_health_file.is_file():
        return False
    with database.session() as session:
        state = session.get(TelegramState, 1)
        return (
            state is not None
            and (datetime.now(UTC) - state.heartbeat_at).total_seconds()
            < settings.telegram_health_seconds
        )


def cycle(database: Database, settings: Settings, api: TelegramApi) -> None:
    with database.session() as session:
        state = session.get(TelegramState, 1)
        if state is None:
            raise ServiceError("TELEGRAM_STATE_MISSING", 503)
        offset = state.next_offset
        pending = (
            session.scalar(
                select(TelegramUpdate.id)
                .where(
                    TelegramUpdate.status == "pending",
                    or_(
                        TelegramUpdate.next_attempt_at.is_(None),
                        TelegramUpdate.next_attempt_at <= datetime.now(UTC),
                    ),
                )
                .limit(1)
            )
            is not None
        )
        session.rollback()
        updates = api.updates(offset, 0 if pending else settings.telegram_poll_seconds)
        for payload in updates:
            try:
                update = Update.model_validate(payload)
            except ValidationError:
                raise ServiceError("TELEGRAM_INVALID_RESPONSE", 503) from None
            receive(session, payload)
            state = session.get(TelegramState, 1)
            if state is None:
                raise ServiceError("TELEGRAM_STATE_MISSING", 503)
            state.next_offset = max(state.next_offset, update.update_id + 1)
            session.commit()
        process_one(session, settings, api.download)
        for row in session.scalars(
            select(TelegramUpdate)
            .where(TelegramUpdate.notified.is_(False))
            .order_by(TelegramUpdate.id)
            .limit(20)
        ):
            try:
                api.reply(row.chat_id, TEXTS[row.language][row.reply_code])
            except ServiceError as error:
                if error.status >= 500:
                    raise
                logger.warning("TELEGRAM_REPLY_REJECTED")
            row.notified = True
            session.commit()
        state = session.get(TelegramState, 1)
        if state is None:
            raise ServiceError("TELEGRAM_STATE_MISSING", 503)
        state.heartbeat_at = datetime.now(UTC)
        session.commit()


def main() -> None:
    settings = Settings()
    configure_logging("debug" if settings.log_level == "trace" else settings.log_level)
    database = Database(settings)
    try:
        if "--health" in sys.argv:
            raise SystemExit(0 if healthy(settings, database) else 1)
        if not settings.telegram_token.get_secret_value():
            logger.info("TELEGRAM_DISABLED")
            while True:
                time.sleep(settings.telegram_poll_seconds)
        settings.telegram_health_file.unlink(missing_ok=True)
        with database.engine.connect() as leader:
            if not leader.scalar(text("SELECT pg_try_advisory_lock(710024005)")):
                raise ServiceError("TELEGRAM_WORKER_ALREADY_RUNNING", 503)
            leader.commit()
            with httpx.Client() as client:
                api = TelegramApi(settings, client)
                bot_id = api.verify()
                with database.session() as session:
                    state = session.get(TelegramState, 1)
                    if state is not None and state.bot_id != bot_id:
                        raise ServiceError("TELEGRAM_BOT_CHANGED", 503)
                    if state is None:
                        session.add(
                            TelegramState(
                                id=1,
                                bot_id=bot_id,
                                next_offset=0,
                                heartbeat_at=datetime.now(UTC),
                            )
                        )
                    session.commit()
                logger.info("TELEGRAM_BOT_VERIFIED")
                while True:
                    try:
                        leader.execute(text("SELECT 1"))
                        leader.commit()
                        cycle(database, settings, api)
                        settings.telegram_health_file.touch()
                    except ServiceError as error:
                        logger.error("%s", error.code)
                        time.sleep(
                            max(settings.telegram_retry_seconds, error.retry_after or 0)
                        )
    except (ServiceError, SQLAlchemyError, OSError) as error:
        logger.exception(
            error.code if isinstance(error, ServiceError) else "TELEGRAM_WORKER_STOPPED"
        )
        raise SystemExit(1) from None
    finally:
        database.close()


if __name__ == "__main__":
    main()
