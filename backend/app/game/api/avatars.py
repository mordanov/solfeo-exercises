from fastapi import APIRouter, Depends
from pydantic import BaseModel

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
}


@router.get("/catalog")
def catalog(identity: Member) -> list[dict[str, object]]:
    return [
        {"id": aid, "name": ANIMAL_DISPLAY_NAMES.get(aid, aid)} for aid in ANIMAL_IDS
    ]


class GenerateBody(BaseModel):
    player_id: int
    description: str


@router.post("/generate", dependencies=[Depends(require_csrf)])
def generate_avatar(
    body: GenerateBody, identity: Member, session: Db, settings: Configuration
) -> dict[str, object]:
    from app.game.services.avatars import check_daily_quota, start_avatar_job
    from app.game.services.players import get_or_403

    with session.begin():
        account_id = identity.user.id
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
    from app.game.models import CustomAvatar
    from app.game.services.players import update_player

    with session.begin():
        job = session.get(CustomAvatar, job_id)
        if job is None or (
            identity.user.role != "manager" and job.account_id != identity.user.id
        ):
            raise ServiceError("JOB_NOT_FOUND", 404)
        if job.status != "ready":
            raise ServiceError("JOB_NOT_READY", 400)
        update_player(session, job.player_id, custom_avatar_id=job.id)
    return {"ok": True}


@router.delete("/{job_id}", dependencies=[Depends(require_csrf)])
def discard_avatar(job_id: int, identity: Member, session: Db) -> dict[str, object]:
    from app.game.models import CustomAvatar

    with session.begin():
        job = session.get(CustomAvatar, job_id)
        if job is None or (
            identity.user.role != "manager" and job.account_id != identity.user.id
        ):
            raise ServiceError("JOB_NOT_FOUND", 404)
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
