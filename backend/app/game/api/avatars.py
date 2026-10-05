from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field

from app.api.auth import Configuration, Db, Manager, Member, require_csrf
from app.game.config import ANIMAL_IDS
from app.game.models import CustomAvatar
from app.game.services.avatars import (
    authorized_job,
    avatar_path,
    generation_estimate,
    list_avatar_jobs,
    list_review_jobs,
    quota_usage,
    remaining_seconds,
    review_avatar,
    review_sheet_path,
)
from app.game.services.avatars import (
    discard_avatar as discard_job,
)
from app.game.services.avatars import (
    use_avatar as use_job,
)

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


class GenerationOut(BaseModel):
    job_id: int


class MutationOut(BaseModel):
    ok: bool


@router.post("/generate", dependencies=[Depends(require_csrf)])
def generate_avatar(
    body: GenerateBody, identity: Member, session: Db, settings: Configuration
) -> GenerationOut:
    from app.game.services.avatars import start_avatar_job

    with session.begin():
        account_id = identity.user.id
        job = start_avatar_job(
            session, account_id, body.player_id, body.description, settings
        )
        job_id = job.id
    return GenerationOut(job_id=job_id)


class AvatarJobOut(BaseModel):
    id: int
    status: str
    review_status: str
    phase: str
    asset_version: int
    completed_images: int
    total_images: int
    estimated_seconds_remaining: int | None
    base_path: str | None
    happy_path: str | None
    sad_path: str | None
    error_code: str | None


class SavedAvatarsOut(BaseModel):
    jobs: list[AvatarJobOut]
    total: int


class ReviewBody(BaseModel):
    decision: Literal["approved", "rejected"]


class ReviewJobOut(AvatarJobOut):
    player_id: int
    player_name: str
    account_id: int
    description: str
    created_at: str


class ReviewQueueOut(BaseModel):
    jobs: list[ReviewJobOut]
    total: int


class AvatarQuotaOut(BaseModel):
    used: int
    limit: int | None
    resets_at: str | None
    generation_available: bool
    generation_reason: str | None
    image_count: int = 30


def _job_out(job: CustomAvatar, estimate: int) -> AvatarJobOut:
    ready = job.status == "ready"
    approved = job.review_status == "approved"
    total = 30 if job.asset_version == 2 else 3
    return AvatarJobOut(
        id=job.id,
        status=job.status,
        review_status=job.review_status,
        phase="complete" if ready and approved else job.phase,
        asset_version=job.asset_version,
        completed_images=3
        if ready and job.asset_version == 1
        else job.completed_images,
        total_images=total,
        estimated_seconds_remaining=remaining_seconds(job, estimate),
        base_path=job.base_path if approved else None,
        happy_path=job.happy_path if approved else None,
        sad_path=job.sad_path if approved else None,
        error_code=job.error_code,
    )


@router.get("/review")
def review_queue(
    identity: Manager,
    session: Db,
    settings: Configuration,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReviewQueueOut:
    with session.begin():
        jobs, total = list_review_jobs(session, offset)
        estimate = generation_estimate(session, settings)
        return ReviewQueueOut(
            jobs=[
                ReviewJobOut(
                    **_job_out(job, estimate).model_dump(),
                    player_id=job.player_id,
                    player_name=player_name,
                    account_id=job.account_id,
                    description=job.description,
                    created_at=job.created_at.isoformat(),
                )
                for job, player_name in jobs
            ],
            total=total,
        )


@router.post("/{job_id}/review", dependencies=[Depends(require_csrf)])
def decide_review(
    job_id: int,
    body: ReviewBody,
    identity: Manager,
    session: Db,
    settings: Configuration,
) -> AvatarJobOut:
    with session.begin():
        job = review_avatar(session, job_id, identity.user.id, body.decision, settings)
        return _job_out(job, generation_estimate(session, settings))


@router.api_route("/{job_id}/review-sheet", methods=["GET", "HEAD"])
def review_sheet(
    job_id: int,
    identity: Manager,
    session: Db,
    settings: Configuration,
    response: Response,
) -> Response:
    with session.begin():
        job = authorized_job(session, job_id, identity.user.id, True)
        path = review_sheet_path(job, settings)
    return _protected_image(path, settings, response)


@router.get("/saved")
def saved_avatars(
    player_id: int,
    identity: Member,
    session: Db,
    settings: Configuration,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SavedAvatarsOut:
    with session.begin():
        jobs, total = list_avatar_jobs(
            session,
            player_id,
            identity.user.id,
            identity.user.role == "manager",
            saved=True,
            offset=offset,
        )
        estimate = generation_estimate(session, settings)
        return SavedAvatarsOut(
            jobs=[_job_out(job, estimate) for job in jobs], total=total
        )


@router.get("")
def recent_jobs(
    player_id: int, identity: Member, session: Db, settings: Configuration
) -> list[AvatarJobOut]:
    with session.begin():
        jobs, _ = list_avatar_jobs(
            session,
            player_id,
            identity.user.id,
            identity.user.role == "manager",
        )
        estimate = generation_estimate(session, settings)
        return [_job_out(job, estimate) for job in jobs]


@router.get("/{job_id}/status")
def job_status(
    job_id: int, identity: Member, session: Db, settings: Configuration
) -> AvatarJobOut:
    with session.begin():
        job = authorized_job(
            session, job_id, identity.user.id, identity.user.role == "manager"
        )
        return _job_out(job, generation_estimate(session, settings))


@router.post("/{job_id}/use", dependencies=[Depends(require_csrf)])
def use_avatar(
    job_id: int, identity: Member, session: Db, settings: Configuration
) -> MutationOut:
    with session.begin():
        use_job(
            session,
            job_id,
            identity.user.id,
            identity.user.role == "manager",
            settings,
        )
    return MutationOut(ok=True)


@router.api_route("/{job_id}/files/{state}", methods=["GET", "HEAD"])
def avatar_file(
    job_id: int,
    state: Literal["neutral", "happy", "sad"],
    identity: Member,
    session: Db,
    settings: Configuration,
    response: Response,
    level: Annotated[int, Query(ge=1, le=10)] = 1,
) -> Response:
    with session.begin():
        job = authorized_job(
            session, job_id, identity.user.id, identity.user.role == "manager"
        )
        path = avatar_path(
            job, state, level, settings, manager=identity.user.role == "manager"
        )
    return _protected_image(path, settings, response)


def _protected_image(
    path: Path, settings: Configuration, response: Response
) -> Response:
    root = settings.media_root.resolve()
    response.headers["X-Accel-Redirect"] = "/_protected_media/" + quote(
        path.relative_to(root).as_posix()
    )
    response.headers["Content-Type"] = "image/png"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.status_code = 200
    return response


@router.delete("/{job_id}", dependencies=[Depends(require_csrf)])
def discard_avatar(job_id: int, identity: Member, session: Db) -> MutationOut:
    with session.begin():
        discard_job(session, job_id, identity.user.id, identity.user.role == "manager")
    return MutationOut(ok=True)


@router.get("/quota")
def quota(identity: Member, session: Db, settings: Configuration) -> AvatarQuotaOut:
    available = bool(settings.openai_api_key.get_secret_value())
    with session.begin():
        used, limit, resets_at = quota_usage(
            session, identity.user.id, identity.user.role == "manager", settings
        )
    return AvatarQuotaOut(
        used=used,
        limit=limit,
        resets_at=resets_at.isoformat() if resets_at else None,
        generation_available=available,
        generation_reason=None if available else "AVATAR_GENERATION_UNAVAILABLE",
    )
