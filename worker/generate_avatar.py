#!/usr/bin/env python3
"""Avatar generation worker.

Polls for pending custom avatar jobs and processes them with DALL-E.
"""

import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from sqlalchemy import select, text

from app.database import Database
from app.game.config import AVATAR_WORKER_LOCK_ID
from app.game.models import AvatarGenerationLog, CustomAvatar
from app.settings import Settings

logger = logging.getLogger(__name__)

IMAGE_SYSTEM = (
    "Cute, child-friendly, single magical creature, "
    "consistent flat cartoon illustration style, "
    "plain transparent background, no text, no real people, "
    "no brands or characters from existing franchises. "
    "Style: bold outlines, bright pastel colours."
)


def _openai_post(
    settings: Settings, path: str, payload: dict[str, object], timeout: float = 60.0
) -> dict[str, object]:
    url = f"https://api.openai.com/v1{path}"
    key = settings.openai_api_key.get_secret_value()
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, json=payload, headers={"Authorization": f"Bearer {key}"})
    r.raise_for_status()
    return r.json()  # type: ignore[no-any-return]


def _moderate(settings: Settings, text_: str) -> bool:
    result = _openai_post(settings, "/moderations", {"input": text_})
    results = result.get("results", [])
    return bool(results and isinstance(results, list) and results[0].get("flagged"))


def _generate_image(settings: Settings, prompt: str) -> str:
    result = _openai_post(
        settings,
        "/images/generations",
        {
            "model": settings.avatar_image_model,
            "prompt": f"{IMAGE_SYSTEM}\n\n{prompt}",
            "n": 1,
            "size": "1024x1024",
            "response_format": "url",
        },
        timeout=120.0,
    )
    data = result.get("data", [])
    if isinstance(data, list) and data:
        entry = data[0]
        if isinstance(entry, dict):
            return str(entry["url"])
    return ""


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=30.0) as client:
        r = client.get(url)
    r.raise_for_status()
    dest.write_bytes(r.content)


def process_one(database: Database, settings: Settings) -> bool:
    with database.session() as session:
        with session.begin():
            job = session.scalar(
                select(CustomAvatar)
                .where(CustomAvatar.status == "pending")
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if job is None:
                return False
            job_id = job.id
            description = job.description
            account_id = job.account_id

    try:
        flagged = _moderate(settings, description)
        if flagged:
            with database.session() as session:
                with session.begin():
                    j = session.get(CustomAvatar, job_id)
                    if j:
                        j.status = "failed"
                        j.error_code = "MODERATION_FLAGGED"
                    log = session.scalar(
                        select(AvatarGenerationLog)
                        .where(AvatarGenerationLog.account_id == account_id)
                        .order_by(AvatarGenerationLog.id.desc())
                        .limit(1)
                    )
                    if log:
                        log.flagged = True
                        log.billable = False
            return True

        base_url = _generate_image(settings, description)
        happy_url = _generate_image(settings, f"Happy version of: {description}")
        sad_url = _generate_image(settings, f"Sad version of: {description}")

        base_dir = Path(settings.media_root) / "avatars" / "custom" / str(job_id)
        base_path = base_dir / "base.png"
        happy_path = base_dir / "happy.png"
        sad_path = base_dir / "sad.png"
        _download(base_url, base_path)
        _download(happy_url, happy_path)
        _download(sad_url, sad_path)

        with database.session() as session:
            with session.begin():
                j = session.get(CustomAvatar, job_id)
                if j:
                    j.status = "ready"
                    j.base_path = str(base_path.relative_to(settings.media_root))
                    j.happy_path = str(happy_path.relative_to(settings.media_root))
                    j.sad_path = str(sad_path.relative_to(settings.media_root))
                    j.completed_at = datetime.now(UTC)

    except Exception as exc:
        logger.exception("Avatar job %s failed: %s", job_id, exc)
        with database.session() as session:
            with session.begin():
                j = session.get(CustomAvatar, job_id)
                if j:
                    j.status = "failed"
                    j.error_code = str(exc)[:50]
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    database = Database(settings)
    with database.session() as session:
        session.execute(text(f"SELECT pg_advisory_lock({AVATAR_WORKER_LOCK_ID})"))
    logger.info("Avatar worker started (lock %d)", AVATAR_WORKER_LOCK_ID)
    try:
        while True:
            try:
                process_one(database, settings)
            except Exception:
                logger.exception("Unexpected error in worker loop")
            time.sleep(2)
    finally:
        database.close()


if __name__ == "__main__":
    main()
