from sqlalchemy import select
from sqlalchemy.orm import Session

from app.game.models import CustomAvatar, Player, Season
from app.services.auth import ServiceError


def get_or_403(session: Session, player_id: int, account_id: int) -> Player:
    player = session.get(Player, player_id)
    if player is None or player.account_id != account_id:
        raise ServiceError("PLAYER_NOT_FOUND", 404)
    return player


def list_players(session: Session, account_id: int | None = None) -> list[Player]:
    q = select(Player)
    if account_id is not None:
        q = q.where(Player.account_id == account_id)
    return list(session.scalars(q.order_by(Player.id)))


def choose_avatar(
    session: Session, player_id: int, animal: str, account_id: int | None
) -> Player:
    from app.game.config import ANIMAL_IDS

    if animal not in ANIMAL_IDS:
        raise ServiceError("INVALID_AVATAR_ANIMAL", 422)
    with session.begin():
        player = session.get(Player, player_id)
        if player is None or (
            account_id is not None and player.account_id != account_id
        ):
            raise ServiceError("PLAYER_NOT_FOUND", 404)
        player.avatar_animal = animal
        player.custom_avatar_id = None
    return player


def create_player(
    session: Session, account_id: int, name: str, avatar_animal: str | None
) -> Player:
    from app.game.config import ANIMAL_IDS

    if avatar_animal is not None and avatar_animal not in ANIMAL_IDS:
        raise ServiceError("INVALID_AVATAR_ANIMAL", 422)
    with session.begin():
        existing = session.scalar(
            select(Player).where(Player.account_id == account_id, Player.name == name)
        )
        if existing is not None:
            raise ServiceError("PLAYER_NAME_TAKEN", 409)
        player = Player(account_id=account_id, name=name, avatar_animal=avatar_animal)
        session.add(player)
        session.flush()
        season = Season(player_id=player.id, number=1)
        session.add(season)
        session.flush()
    return player


def update_player(
    session: Session,
    player_id: int,
    *,
    name: str | None = None,
    avatar_animal: str | None = None,
    custom_avatar_id: int | None = None,
) -> Player:
    from app.game.config import ANIMAL_IDS

    with session.begin():
        player = session.get(Player, player_id)
        if player is None:
            raise ServiceError("PLAYER_NOT_FOUND", 404)
        if name is not None:
            player.name = name
        if avatar_animal is not None:
            if avatar_animal not in ANIMAL_IDS:
                raise ServiceError("INVALID_AVATAR_ANIMAL", 422)
            player.avatar_animal = avatar_animal
            player.custom_avatar_id = None
        if custom_avatar_id is not None:
            job = session.get(CustomAvatar, custom_avatar_id)
            if job is None or job.player_id != player_id or job.status != "ready":
                raise ServiceError("INVALID_CUSTOM_AVATAR", 422)
            player.custom_avatar_id = custom_avatar_id
        session.flush()
    return player
