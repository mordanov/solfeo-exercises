import logging
import sys
import time

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import Database
from app.logging import configure_logging
from app.services import omr
from app.services.auth import ServiceError
from app.services.omr_engine import AudiverisEngine, OmrEngine
from app.settings import Settings

logger = logging.getLogger("worker.omr")


def cycle(database: Database, settings: Settings, engine: OmrEngine) -> bool:
    with database.session() as session:
        job = omr.claim(session, settings)
        if job is None:
            return False
        try:
            score = engine.recognize(settings.media_root / job.filename)
            omr.complete(session, settings, job, score)
            logger.info("OMR_JOB_COMPLETED", extra={"job_id": job.id})
        except ServiceError as error:
            omr.fail(session, settings, job, error.code, retryable=error.status >= 500)
            logger.warning(error.code, extra={"job_id": job.id})
        return True


def healthy(settings: Settings) -> bool:
    return (
        settings.omr_health_file.is_file()
        and (time.time() - settings.omr_health_file.stat().st_mtime)
        < settings.omr_health_seconds
    )


def main() -> None:
    settings = Settings()
    configure_logging("debug" if settings.log_level == "trace" else settings.log_level)
    if "--health" in sys.argv:
        raise SystemExit(0 if healthy(settings) else 1)
    database = Database(settings)
    settings.omr_health_file.unlink(missing_ok=True)
    try:
        engine = AudiverisEngine(settings)
        with database.engine.connect() as leader:
            if not leader.scalar(text("SELECT pg_try_advisory_lock(710024006)")):
                raise ServiceError("OMR_WORKER_ALREADY_RUNNING", 503)
            leader.commit()
            logger.info("OMR_WORKER_STARTED")
            if not settings.omr_enabled:
                logger.warning("OMR_DISABLED")
            while True:
                leader.execute(text("SELECT 1"))
                leader.commit()
                if settings.omr_enabled:
                    cycle(database, settings, engine)
                settings.omr_health_file.touch()
                time.sleep(settings.omr_poll_seconds)
    except (ServiceError, SQLAlchemyError, OSError) as error:
        logger.exception(
            error.code if isinstance(error, ServiceError) else "OMR_WORKER_STOPPED"
        )
        raise SystemExit(1) from None
    finally:
        settings.omr_health_file.unlink(missing_ok=True)
        database.close()


if __name__ == "__main__":
    main()
