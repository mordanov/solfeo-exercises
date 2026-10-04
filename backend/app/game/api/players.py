from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.auth import Db, Manager, Member, require_csrf
from app.game.config import LEVEL_THRESHOLDS
from app.game.models import Player

router = APIRouter(prefix="/api/game/players", tags=["game-players"])


class CreatePlayerBody(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    avatar_animal: str | None = None
    account_id: int | None = Field(default=None, gt=0)


class PatchPlayerBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=20)
    avatar_animal: str | None = None
    custom_avatar_id: int | None = None


class EligibleAccountOut(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str


class EligibleAccountsOut(BaseModel):
    users: list[EligibleAccountOut]
    total: int


def _player_out(player: Player) -> dict[str, object]:
    return {
        "id": player.id,
        "account_id": player.account_id,
        "name": player.name,
        "avatar_animal": player.avatar_animal,
        "custom_avatar_id": player.custom_avatar_id,
        "xp": player.xp,
        "avatar_level": sum(player.xp >= threshold for threshold in LEVEL_THRESHOLDS),
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

    account_id = body.account_id if body.account_id is not None else identity.user.id
    player = svc_create(session, account_id, body.name, body.avatar_animal)
    return _player_out(player)


@router.get("/accounts")
def eligible_accounts(
    identity: Manager,
    session: Db,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EligibleAccountsOut:
    from app.game.services.players import eligible_accounts as svc_accounts

    users, total = svc_accounts(session, offset)
    return EligibleAccountsOut(
        users=[
            EligibleAccountOut(
                id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            for user in users
        ],
        total=total,
    )


class AvatarChoiceBody(BaseModel):
    avatar_animal: str


@router.post("/{player_id}/avatar", dependencies=[Depends(require_csrf)])
def choose_avatar(
    player_id: int, body: AvatarChoiceBody, identity: Member, session: Db
) -> dict[str, object]:
    from app.game.services.players import choose_avatar as svc_choose

    account_id = None if identity.user.role == "manager" else identity.user.id
    player = svc_choose(session, player_id, body.avatar_animal, account_id)
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
