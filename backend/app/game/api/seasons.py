from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.api.auth import Db, Manager, Member, require_csrf
from app.game.models import Player, Season
from app.game.services.players import get_or_403
from app.services.auth import ServiceError

router = APIRouter(tags=["game-seasons"])


class ResetBody(BaseModel):
    confirmation: str


def _season_out(s: Season) -> dict[str, object]:
    return {
        "id": s.id,
        "player_id": s.player_id,
        "number": s.number,
        "started_at": s.started_at.isoformat(),
        "ended_at": s.ended_at.isoformat() if s.ended_at is not None else None,
    }


@router.get("/api/game/players/{player_id}/seasons")
def list_seasons(
    player_id: int,
    identity: Member,
    session: Db,
) -> list[dict[str, object]]:
    from app.game.services.seasons import list_seasons as svc_list

    get_or_403(
        session,
        player_id,
        None if identity.user.role == "manager" else identity.user.id,
    )
    seasons = svc_list(session, player_id)
    return [_season_out(s) for s in seasons]


@router.post(
    "/api/game/players/{player_id}/seasons/reset",
    dependencies=[Depends(require_csrf)],
)
def reset_season(
    player_id: int,
    body: ResetBody,
    identity: Manager,
    session: Db,
) -> dict[str, object]:
    if body.confirmation != "RESET":
        raise ServiceError("CONFIRMATION_REQUIRED", 400)
    from app.game.services.seasons import reset_season as svc_reset

    with session.begin():
        season = svc_reset(session, player_id)
    return _season_out(season)


@router.post(
    "/api/game/seasons/reset-all",
    dependencies=[Depends(require_csrf)],
)
def reset_all_seasons(
    body: ResetBody,
    identity: Manager,
    session: Db,
) -> list[dict[str, object]]:
    if body.confirmation != "RESET":
        raise ServiceError("CONFIRMATION_REQUIRED", 400)
    from app.game.services.seasons import reset_season

    with session.begin():
        player_ids = list(session.scalars(select(Player.id).order_by(Player.id)))
        results = [reset_season(session, player_id) for player_id in player_ids]
    return [_season_out(s) for s in results]
