from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.game.models import AvatarGenerationLog, CustomAvatar, Player
from app.models import User
from app.services.auth import ServiceError
from app.settings import Settings


def check_daily_quota(session: Session, account_id: int, limit: int) -> int:
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    used = (
        session.scalar(
            select(func.count())
            .select_from(AvatarGenerationLog)
            .where(
                AvatarGenerationLog.account_id == account_id,
                AvatarGenerationLog.billable == True,  # noqa: E712
                AvatarGenerationLog.created_at >= today,
            )
        )
        or 0
    )
    return max(0, limit - used)


def quota_usage(
    session: Session, account_id: int, manager: bool, settings: Settings
) -> tuple[int, int | None, datetime | None]:
    if manager:
        return 0, None, None
    limit = settings.avatar_gen_daily_limit
    used = limit - check_daily_quota(session, account_id, limit)
    resets_at = (datetime.now(UTC) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return used, limit, resets_at


def start_avatar_job(
    session: Session,
    account_id: int,
    player_id: int,
    description: str,
    settings: Settings,
) -> CustomAvatar:
    account = session.scalar(
        select(User).where(User.id == account_id).with_for_update()
    )
    player = session.scalar(
        select(Player).where(Player.id == player_id).with_for_update()
    )
    if (
        account is None
        or player is None
        or (account.role != "manager" and player.account_id != account_id)
    ):
        raise ServiceError("PLAYER_NOT_FOUND", 404)
    description = description.strip()
    if not description:
        raise ServiceError("AVATAR_DESCRIPTION_REQUIRED", 422)
    pending = session.scalar(
        select(CustomAvatar)
        .where(CustomAvatar.player_id == player_id, CustomAvatar.status == "pending")
        .order_by(CustomAvatar.id)
        .limit(1)
    )
    if pending is not None:
        if pending.account_id == account_id and pending.description == description:
            return pending
        raise ServiceError("AVATAR_JOB_BUSY", 409)
    if not settings.openai_api_key.get_secret_value():
        raise ServiceError("AVATAR_GENERATION_UNAVAILABLE", 503)
    if (
        account.role != "manager"
        and check_daily_quota(session, account_id, settings.avatar_gen_daily_limit) <= 0
    ):
        raise ServiceError("AVATAR_QUOTA_EXCEEDED", 429)
    log = AvatarGenerationLog(account_id=account_id, billable=True)
    session.add(log)
    session.flush()
    job = CustomAvatar(
        account_id=account_id,
        player_id=player_id,
        description=description,
        status="pending",
        asset_version=2,
        phase="queued",
        generation_log_id=log.id,
    )
    session.add(job)
    session.flush()
    return job


def authorized_job(
    session: Session, job_id: int, account_id: int, manager: bool
) -> CustomAvatar:
    job = session.get(CustomAvatar, job_id)
    player = session.get(Player, job.player_id) if job else None
    if (
        job is None
        or player is None
        or (not manager and account_id not in (job.account_id, player.account_id))
    ):
        raise ServiceError("JOB_NOT_FOUND", 404)
    return job


def generation_estimate(session: Session, settings: Settings) -> int:
    rows = session.execute(
        select(CustomAvatar.started_at, CustomAvatar.completed_at)
        .where(
            CustomAvatar.status == "ready",
            CustomAvatar.asset_version == 2,
            CustomAvatar.attempts == 1,
            CustomAvatar.started_at.is_not(None),
            CustomAvatar.completed_at.is_not(None),
        )
        .order_by(CustomAvatar.id.desc())
        .limit(5)
    )
    durations = [
        (end - start).total_seconds()
        for start, end in rows
        if start is not None
        and end is not None
        and 0
        < (end - start).total_seconds()
        <= settings.avatar_gen_timeout_seconds + 60
    ]
    return (
        max(1, math.ceil(sum(durations) / len(durations)))
        if durations
        else settings.avatar_gen_estimated_seconds
    )


def remaining_seconds(job: CustomAvatar, estimate: int) -> int | None:
    if job.status == "ready":
        return 0
    elapsed = (datetime.now(UTC) - (job.started_at or job.created_at)).total_seconds()
    remaining = math.ceil(estimate - elapsed)
    return remaining if job.status == "pending" and remaining > 0 else None


def validate_avatar_assets(job: CustomAvatar, settings: Settings) -> None:
    if job.asset_version != 2:
        return
    root = settings.media_root.resolve() / "avatars" / "custom" / str(job.id)
    filenames = ["sheet.png", "manifest.json"] + [
        f"levels/avatar_{level:02}_{state}.png"
        for level in range(1, 11)
        for state in ("neutral", "happy", "sad")
    ]
    if job.completed_images != 30 or any(
        not (root / filename).is_file()
        or not (root / filename).resolve().is_relative_to(root)
        for filename in filenames
    ):
        raise ServiceError("AVATAR_ASSETS_MISSING", 409)


def avatar_path(job: CustomAvatar, state: str, level: int, settings: Settings) -> Path:
    if job.status != "ready":
        raise ServiceError("JOB_NOT_READY", 400)
    filename = {
        "neutral": job.base_path,
        "happy": job.happy_path,
        "sad": job.sad_path,
    }[state]
    if job.asset_version == 2:
        filename = f"avatars/custom/{job.id}/levels/avatar_{level:02}_{state}.png"
    if not filename:
        raise ServiceError("FILE_NOT_FOUND", 404)
    root = settings.media_root.resolve()
    path = (root / filename).resolve()
    job_root = root / "avatars" / "custom" / str(job.id)
    if not path.is_relative_to(job_root) or not path.is_file():
        raise ServiceError("FILE_NOT_FOUND", 404)
    return path


def list_avatar_jobs(
    session: Session,
    player_id: int,
    account_id: int,
    manager: bool,
    *,
    saved: bool = False,
    offset: int = 0,
) -> tuple[list[CustomAvatar], int]:
    player = session.get(Player, player_id)
    if player is None or (not manager and player.account_id != account_id):
        raise ServiceError("PLAYER_NOT_FOUND", 404)
    query = select(CustomAvatar).where(CustomAvatar.player_id == player_id)
    if saved:
        query = query.where(CustomAvatar.status == "ready")
    elif player.custom_avatar_id is not None:
        query = query.where(CustomAvatar.id != player.custom_avatar_id)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    jobs = session.scalars(
        query.order_by(CustomAvatar.id.desc()).offset(offset).limit(12 if saved else 5)
    )
    return list(jobs), total


def use_avatar(
    session: Session, job_id: int, account_id: int, manager: bool, settings: Settings
) -> None:
    job = authorized_job(session, job_id, account_id, manager)
    if job.status != "ready":
        raise ServiceError("JOB_NOT_READY", 400)
    validate_avatar_assets(job, settings)
    player = session.get(Player, job.player_id)
    if player is None:
        raise ServiceError("PLAYER_NOT_FOUND", 404)
    player.custom_avatar_id = job.id


def discard_avatar(
    session: Session, job_id: int, account_id: int, manager: bool
) -> None:
    job = authorized_job(session, job_id, account_id, manager)
    if job.status == "pending":
        raise ServiceError("AVATAR_JOB_BUSY", 409)
    player = session.get(Player, job.player_id)
    if player is not None and player.custom_avatar_id == job.id:
        player.custom_avatar_id = None
        session.flush()
    session.delete(job)
