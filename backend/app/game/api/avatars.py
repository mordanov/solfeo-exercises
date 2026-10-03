from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from app.api.auth import Configuration, Db, Member, require_csrf
from app.game.config import ANIMAL_IDS
from app.services.auth import ServiceError

router = APIRouter(prefix="/api/game/avatars", tags=["game-avatars"])

ANIMAL_DISPLAY_NAMES = {
    "unicorn": "Единорог",
    "dragon": "Дракон",
    "phoenix": "Феникс",
    "griffin": "Грифон",
    "sphinx_cat": "Сфинкс",
    "kitsune_fox": "Кицунэ",
    "pegasus": "Пегас",
    "mermaid": "Русалка",
    "lion": "Лев",
    "panda": "Панда",
    "rhino": "Носорог",
}


@router.get("/catalog")
def catalog(identity: Member) -> list[dict[str, object]]:
    return [
        {"id": aid, "name": ANIMAL_DISPLAY_NAMES.get(aid, aid)} for aid in ANIMAL_IDS
    ]


class GenerateBody(BaseModel):
    player_id: int
    description: str = Field(min_length=1, max_length=1000)


@router.post("/generate", dependencies=[Depends(require_csrf)])
def generate_avatar(
    body: GenerateBody, identity: Member, session: Db, settings: Configuration
) -> dict[str, object]:
    from app.game.services.avatars import check_daily_quota, start_avatar_job
    from app.game.services.players import get_or_403

    if not settings.openai_api_key.get_secret_value():
        raise ServiceError("AVATAR_GENERATION_UNAVAILABLE", 503)
    with session.begin():
        account_id = identity.user.id
        if identity.user.role == "manager":
            from app.game.models import Player

            if session.get(Player, body.player_id) is None:
                raise ServiceError("PLAYER_NOT_FOUND", 404)
        else:
            get_or_403(session, body.player_id, account_id)
        is_manager = identity.user.role == "manager"
        if not is_manager:
            remaining = check_daily_quota(
                session, account_id, settings.avatar_gen_daily_limit
            )
            if remaining <= 0:
                raise ServiceError("AVATAR_QUOTA_EXCEEDED", 429)
        job = start_avatar_job(
            session, account_id, body.player_id, body.description, settings
        )
        job_id = job.id
    return {"job_id": job_id}


def _job_out(job: object) -> dict[str, object]:
    from app.game.models import CustomAvatar

    assert isinstance(job, CustomAvatar)
    return {
        "id": job.id,
        "status": job.status,
        "base_path": job.base_path,
        "happy_path": job.happy_path,
        "sad_path": job.sad_path,
        "error_code": job.error_code,
    }


@router.get("")
def recent_jobs(
    player_id: int, identity: Member, session: Db
) -> list[dict[str, object]]:
    from sqlalchemy import select

    from app.game.models import CustomAvatar, Player

    with session.begin():
        player = session.get(Player, player_id)
        if player is None or (
            identity.user.role != "manager" and player.account_id != identity.user.id
        ):
            raise ServiceError("PLAYER_NOT_FOUND", 404)
        query = (
            select(CustomAvatar)
            .where(
                CustomAvatar.player_id == player_id,
                CustomAvatar.status.in_(("pending", "ready", "failed")),
            )
            .order_by(CustomAvatar.id.desc())
            .limit(5)
        )
        if player.custom_avatar_id is not None:
            query = query.where(CustomAvatar.id != player.custom_avatar_id)
        if identity.user.role != "manager":
            query = query.where(CustomAvatar.account_id == identity.user.id)
        return [_job_out(job) for job in session.scalars(query)]


@router.get("/{job_id}/status")
def job_status(job_id: int, identity: Member, session: Db) -> dict[str, object]:
    from app.game.models import CustomAvatar

    with session.begin():
        job = session.get(CustomAvatar, job_id)
        if job is None or (
            identity.user.role != "manager" and job.account_id != identity.user.id
        ):
            raise ServiceError("JOB_NOT_FOUND", 404)
    return _job_out(job)


@router.post("/{job_id}/use", dependencies=[Depends(require_csrf)])
def use_avatar(job_id: int, identity: Member, session: Db) -> dict[str, object]:
    from app.game.models import CustomAvatar, Player

    with session.begin():
        job = session.get(CustomAvatar, job_id)
        if job is None or (
            identity.user.role != "manager" and job.account_id != identity.user.id
        ):
            raise ServiceError("JOB_NOT_FOUND", 404)
        if job.status != "ready":
            raise ServiceError("JOB_NOT_READY", 400)
        player = session.get(Player, job.player_id)
        if player is None:
            raise ServiceError("PLAYER_NOT_FOUND", 404)
        player.custom_avatar_id = job.id
    return {"ok": True}


@router.api_route("/{job_id}/files/{state}", methods=["GET", "HEAD"])
def avatar_file(
    job_id: int,
    state: Literal["neutral", "happy", "sad"],
    identity: Member,
    session: Db,
    settings: Configuration,
    response: Response,
) -> Response:
    from app.game.models import CustomAvatar, Player

    with session.begin():
        job = session.get(CustomAvatar, job_id)
        player = session.get(Player, job.player_id) if job else None
        if (
            job is None
            or player is None
            or (
                identity.user.role != "manager"
                and identity.user.id not in (job.account_id, player.account_id)
            )
        ):
            raise ServiceError("JOB_NOT_FOUND", 404)
        if job.status != "ready":
            raise ServiceError("JOB_NOT_READY", 400)
        filename = {
            "neutral": job.base_path,
            "happy": job.happy_path,
            "sad": job.sad_path,
        }[state]
    if not filename:
        raise ServiceError("FILE_NOT_FOUND", 404)
    root = settings.media_root.resolve()
    path = (root / filename).resolve()
    job_root = root / "avatars" / "custom" / str(job_id)
    if (
        not path.is_relative_to(root)
        or not path.is_relative_to(job_root)
        or not path.is_file()
    ):
        raise ServiceError("FILE_NOT_FOUND", 404)
    response.headers["X-Accel-Redirect"] = "/_protected_media/" + quote(
        path.relative_to(root).as_posix()
    )
    response.headers["Content-Type"] = "image/png"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.status_code = 200
    return response


@router.delete("/{job_id}", dependencies=[Depends(require_csrf)])
def discard_avatar(job_id: int, identity: Member, session: Db) -> dict[str, object]:
    from app.game.models import CustomAvatar, Player

    with session.begin():
        job = session.get(CustomAvatar, job_id)
        if job is None or (
            identity.user.role != "manager" and job.account_id != identity.user.id
        ):
            raise ServiceError("JOB_NOT_FOUND", 404)
        player = session.get(Player, job.player_id)
        if player is not None and player.custom_avatar_id == job.id:
            player.custom_avatar_id = None
            session.flush()
        session.delete(job)
    return {"ok": True}


@router.get("/quota")
def quota(identity: Member, session: Db, settings: Configuration) -> dict[str, object]:
    from datetime import UTC, datetime, timedelta

    from app.game.services.avatars import check_daily_quota

    if identity.user.role == "manager":
        return {"used": 0, "limit": None, "resets_at": None}
    with session.begin():
        remaining = check_daily_quota(
            session, identity.user.id, settings.avatar_gen_daily_limit
        )
    used = settings.avatar_gen_daily_limit - remaining
    now = datetime.now(UTC)
    resets_at = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return {
        "used": used,
        "limit": settings.avatar_gen_daily_limit,
        "resets_at": resets_at.isoformat(),
    }
