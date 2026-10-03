from fastapi import APIRouter
from sqlalchemy import select

from app.api.auth import Db, Manager, Member
from app.game.models import Season
from app.game.services.stats import get_confusion, get_stats

router = APIRouter(tags=["game-admin"])


@router.get("/api/game/players/{player_id}/stats")
def player_stats(player_id: int, identity: Member, session: Db) -> dict[str, object]:
    with session.begin():
        season = session.scalar(
            select(Season).where(
                Season.player_id == player_id, Season.ended_at.is_(None)
            )
        )
        if season is None:
            return {}
        return get_stats(session, player_id, season.id)


@router.get("/api/game/players/{player_id}/confusion")
def player_confusion(
    player_id: int, identity: Manager, session: Db
) -> dict[str, object]:
    with session.begin():
        season = session.scalar(
            select(Season).where(
                Season.player_id == player_id, Season.ended_at.is_(None)
            )
        )
        if season is None:
            return {"heatmap": {}, "top_confusions": []}
        return get_confusion(session, player_id, season.id)
