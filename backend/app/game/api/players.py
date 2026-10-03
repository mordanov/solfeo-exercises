from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.auth import Db, Manager, Member, require_csrf
from app.game.models import Player

router = APIRouter(prefix="/api/game/players", tags=["game-players"])


class CreatePlayerBody(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    avatar_animal: str | None = None


class PatchPlayerBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=20)
    avatar_animal: str | None = None
    custom_avatar_id: int | None = None


def _player_out(player: Player) -> dict[str, object]:
    return {
        "id": player.id,
        "account_id": player.account_id,
        "name": player.name,
        "avatar_animal": player.avatar_animal,
        "custom_avatar_id": player.custom_avatar_id,
        "xp": player.xp,
        "created_at": player.created_at.isoformat(),
    }


@router.get("")
def list_players(identity: Member, session: Db) -> list[dict[str, object]]:
    from app.game.services.players import list_players as svc_list

    if identity.user.role == "manager":
        players = svc_list(session)
    else:
        players = svc_list(session, account_id=identity.user.id)
    return [_player_out(p) for p in players]


@router.post("", dependencies=[Depends(require_csrf)])
def create_player(
    body: CreatePlayerBody, identity: Manager, session: Db
) -> dict[str, object]:
    from app.game.services.players import create_player as svc_create

    player = svc_create(session, identity.user.id, body.name, body.avatar_animal)
    return _player_out(player)


@router.get("/{player_id}")
def get_player(player_id: int, identity: Member, session: Db) -> dict[str, object]:
    from app.game.services.players import get_or_403
    from app.services.auth import ServiceError

    if identity.user.role == "manager":
        player = session.get(Player, player_id)
        if player is None:
            raise ServiceError("PLAYER_NOT_FOUND", 404)
    else:
        player = get_or_403(session, player_id, identity.user.id)
    return _player_out(player)


@router.patch("/{player_id}", dependencies=[Depends(require_csrf)])
def patch_player(
    player_id: int, body: PatchPlayerBody, identity: Manager, session: Db
) -> dict[str, object]:
    from app.game.services.players import update_player

    player = update_player(
        session,
        player_id,
        name=body.name,
        avatar_animal=body.avatar_animal,
        custom_avatar_id=body.custom_avatar_id,
    )
    return _player_out(player)
