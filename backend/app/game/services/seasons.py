from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.game.models import Player, Season
from app.services.auth import ServiceError


def list_seasons(session: Session, player_id: int) -> list[Season]:
    return list(
        session.scalars(
            select(Season).where(Season.player_id == player_id).order_by(Season.number)
        )
    )


def reset_season(session: Session, player_id: int) -> Season:
    player = session.scalar(
        select(Player).where(Player.id == player_id).with_for_update()
    )
    if player is None:
        raise ServiceError("PLAYER_NOT_FOUND", 404)
    active = session.scalar(
        select(Season).where(Season.player_id == player_id, Season.ended_at.is_(None))
    )
    now = datetime.now(UTC)
    if active is not None:
        active.ended_at = now
        session.flush()
    last_number = (
        session.scalar(
            select(func.max(Season.number)).where(Season.player_id == player_id)
        )
        or 0
    )
    new_season = Season(player_id=player_id, number=last_number + 1, started_at=now)
    session.add(new_season)
    session.flush()
    return new_season


def resolve_season(
    session: Session, player_id: int, season_id: int | None
) -> Season | None:
    query = select(Season).where(Season.player_id == player_id)
    query = query.where(
        Season.id == season_id if season_id is not None else Season.ended_at.is_(None)
    )
    season = session.scalar(query)
    if season is None and season_id is not None:
        raise ServiceError("SEASON_NOT_FOUND", 404)
    return season
