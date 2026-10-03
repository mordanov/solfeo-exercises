from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.game.models import AvatarGenerationLog, CustomAvatar
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


def start_avatar_job(
    session: Session,
    account_id: int,
    player_id: int,
    description: str,
    settings: Settings,
) -> CustomAvatar:
    log = AvatarGenerationLog(account_id=account_id, billable=True)
    session.add(log)
    job = CustomAvatar(
        account_id=account_id,
        player_id=player_id,
        description=description,
        status="pending",
    )
    session.add(job)
    session.flush()
    return job
