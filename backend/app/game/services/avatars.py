from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.game.models import AvatarGenerationLog, CustomAvatar, Player
from app.models import User
from app.services.auth import ServiceError
from app.settings import Settings


def _quota_day(timezone: str | ZoneInfo) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone) if isinstance(timezone, str) else timezone
    today = (
        datetime.now(UTC)
        .astimezone(zone)
        .replace(hour=0, minute=0, second=0, microsecond=0)
    )
    return today.astimezone(UTC), (today + timedelta(days=1)).astimezone(UTC)


def check_daily_quota(
    session: Session, account_id: int, limit: int, timezone: str | ZoneInfo = "UTC"
) -> int:
    today, tomorrow = _quota_day(timezone)
    used = (
        session.scalar(
            select(func.count())
            .select_from(AvatarGenerationLog)
            .where(
                AvatarGenerationLog.account_id == account_id,
                AvatarGenerationLog.billable == True,  # noqa: E712
                AvatarGenerationLog.created_at >= today,
                AvatarGenerationLog.created_at < tomorrow,
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
    used = limit - check_daily_quota(session, account_id, limit, settings.game_timezone)
    _, resets_at = _quota_day(settings.game_timezone)
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
        and check_daily_quota(
            session, account_id, settings.avatar_gen_daily_limit, settings.game_timezone
        )
        <= 0
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
        review_status="pending",
        generation_log_id=log.id,
    )
    session.add(job)
    session.flush()
    player.avatar_review_job_id = job.id
    player.custom_avatar_id = None
    return job


def authorized_job(
    session: Session, job_id: int, account_id: int, manager: bool
) -> CustomAvatar:
    job = session.get(CustomAvatar, job_id)
    player = session.get(Player, job.player_id) if job else None
    shared = (
        job is not None and job.status == "ready" and job.review_status == "approved"
    )
    if (
        job is None
        or player is None
        or (
            not manager
            and account_id not in (job.account_id, player.account_id)
            and not shared
        )
    ):
        raise ServiceError("JOB_NOT_FOUND", 404)
    return job


def can_discard_avatar(job: CustomAvatar, account_id: int, manager: bool) -> bool:
    return manager or job.account_id == account_id


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


def avatar_path(
    job: CustomAvatar,
    state: str,
    level: int,
    settings: Settings,
    *,
    manager: bool = False,
) -> Path:
    if job.status != "ready":
        raise ServiceError("JOB_NOT_READY", 400)
    if not manager and job.review_status != "approved":
        raise ServiceError("AVATAR_NOT_APPROVED", 403)
    filename: str | None
    if state == "portrait":
        filename = f"avatars/custom/{job.id}/portrait.png"
    else:
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


def review_sheet_path(job: CustomAvatar, settings: Settings) -> Path:
    if job.status != "ready":
        raise ServiceError("JOB_NOT_READY", 400)
    root = settings.media_root.resolve()
    job_root = root / "avatars" / "custom" / str(job.id)
    path = (job_root / "sheet.png").resolve()
    if not path.is_relative_to(job_root) or not path.is_file():
        raise ServiceError("FILE_NOT_FOUND", 404)
    return path


def list_review_jobs(
    session: Session, offset: int = 0
) -> tuple[list[tuple[CustomAvatar, str]], int]:
    query = (
        select(CustomAvatar, Player.name)
        .join(Player, CustomAvatar.player_id == Player.id)
        .where(CustomAvatar.status == "ready", CustomAvatar.review_status == "pending")
    )
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.execute(query.order_by(CustomAvatar.id).offset(offset).limit(12))
    return [(job, name) for job, name in rows], total


def _lock_job_and_player(
    session: Session, job: CustomAvatar
) -> tuple[CustomAvatar, Player]:
    # Match generation's player-first order so review and selection cannot deadlock.
    player = session.scalar(
        select(Player)
        .where(Player.id == job.player_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    locked_job = session.scalar(
        select(CustomAvatar)
        .where(CustomAvatar.id == job.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if player is None or locked_job is None:
        raise ServiceError("JOB_NOT_FOUND", 404)
    return locked_job, player


def review_avatar(
    session: Session,
    job_id: int,
    manager_id: int,
    decision: str,
    settings: Settings,
) -> CustomAvatar:
    manager = session.get(User, manager_id)
    if manager is None or manager.role != "manager" or not manager.is_active:
        raise ServiceError("FORBIDDEN", 403)
    if decision not in ("approved", "rejected"):
        raise ServiceError("AVATAR_REVIEW_INVALID", 422)
    job = authorized_job(session, job_id, manager_id, True)
    job, player = _lock_job_and_player(session, job)
    if job.status != "ready":
        raise ServiceError("JOB_NOT_READY", 400)
    if job.review_status == decision:
        return job
    if job.review_status != "pending":
        raise ServiceError("AVATAR_REVIEW_CONFLICT", 409)
    if decision == "approved":
        validate_avatar_assets(job, settings)
    job.review_status = decision
    job.reviewed_at = datetime.now(UTC)
    job.reviewed_by = manager_id
    job.phase = "complete" if decision == "approved" else "rejected"
    if player.avatar_review_job_id == job.id:
        player.custom_avatar_id = job.id if decision == "approved" else None
        if decision == "approved":
            player.avatar_review_job_id = None
    elif decision == "rejected" and player.custom_avatar_id == job.id:
        player.custom_avatar_id = None
    return job


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
        query = select(CustomAvatar).where(
            CustomAvatar.status == "ready",
            or_(
                CustomAvatar.review_status == "approved",
                CustomAvatar.player_id == player_id,
            ),
        )
    elif player.custom_avatar_id is not None:
        query = query.where(CustomAvatar.id != player.custom_avatar_id)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    jobs = session.scalars(
        query.order_by(CustomAvatar.id.desc()).offset(offset).limit(12 if saved else 5)
    )
    return list(jobs), total


def use_avatar(
    session: Session,
    job_id: int,
    player_id: int,
    account_id: int,
    manager: bool,
    settings: Settings,
) -> None:
    authorized = authorized_job(session, job_id, account_id, manager)
    player = session.scalar(
        select(Player)
        .where(Player.id == player_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    job = session.scalar(
        select(CustomAvatar)
        .where(CustomAvatar.id == authorized.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if player is None or (not manager and player.account_id != account_id):
        raise ServiceError("PLAYER_NOT_FOUND", 404)
    if job is None:
        raise ServiceError("JOB_NOT_FOUND", 404)
    if job.status != "ready":
        raise ServiceError("JOB_NOT_READY", 400)
    if job.review_status != "approved":
        raise ServiceError("AVATAR_NOT_APPROVED", 403)
    validate_avatar_assets(job, settings)
    player.custom_avatar_id = job.id
    player.avatar_review_job_id = None


def discard_avatar(
    session: Session, job_id: int, account_id: int, manager: bool
) -> None:
    job = authorized_job(session, job_id, account_id, manager)
    if not can_discard_avatar(job, account_id, manager):
        raise ServiceError("JOB_NOT_FOUND", 404)
    job, player = _lock_job_and_player(session, job)
    if job.status == "pending":
        raise ServiceError("AVATAR_JOB_BUSY", 409)
    another_player_uses_avatar = session.scalar(
        select(Player.id)
        .where(Player.custom_avatar_id == job.id, Player.id != player.id)
        .limit(1)
    )
    if another_player_uses_avatar is not None:
        raise ServiceError("AVATAR_IN_USE", 409)
    if player.custom_avatar_id == job.id:
        player.custom_avatar_id = None
    if player.avatar_review_job_id == job.id:
        player.avatar_review_job_id = None
    session.flush()
    session.delete(job)
