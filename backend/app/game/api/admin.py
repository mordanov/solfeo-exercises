from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.auth import Db, Manager, Member
from app.game.services.players import get_or_403
from app.game.services.seasons import resolve_season
from app.game.services.stats import get_confusion, get_stats

router = APIRouter(tags=["game-admin"])


@router.get("/api/game/players/{player_id}/stats")
def player_stats(
    player_id: int,
    identity: Member,
    session: Db,
    season_id: Annotated[int | None, Query(gt=0)] = None,
) -> dict[str, object]:
    with session.begin():
        get_or_403(
            session,
            player_id,
            None if identity.user.role == "manager" else identity.user.id,
        )
        season = resolve_season(session, player_id, season_id)
        if season is None:
            return {}
        return get_stats(session, player_id, season.id)


@router.get("/api/game/players/{player_id}/confusion")
def player_confusion(
    player_id: int,
    identity: Manager,
    session: Db,
    season_id: Annotated[int | None, Query(gt=0)] = None,
    clef: Literal["treble", "bass"] | None = None,
) -> dict[str, object]:
    with session.begin():
        get_or_403(session, player_id, None)
        season = resolve_season(session, player_id, season_id)
        if season is None:
            return {
                "heatmap": {},
                "top_confusions": [],
                "missed_notes": [],
                "round_top_confusions": [],
            }
        return get_confusion(session, player_id, season.id, clef)
