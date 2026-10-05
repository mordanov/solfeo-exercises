from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.api.auth import Configuration, Db, ExerciseMember, Input, Manager, require_csrf
from app.models import OmrJob
from app.services import omr

router = APIRouter(prefix="/api/exercises")


class OmrOutput(BaseModel):
    job_id: str | None
    image_id: str | None
    status: str
    attempts: int
    last_error: str | None


class ReviewInput(Input):
    job_id: UUID
    action: Literal["approve", "reject"]


def output(job: OmrJob | None, image_id: str | None) -> OmrOutput:
    return OmrOutput(
        job_id=job.id if job else None,
        image_id=image_id,
        status=job.status if job else "none",
        attempts=job.attempts if job else 0,
        last_error=job.last_error if job else None,
    )


@router.get("/{identifier}/omr")
def status(identifier: int, _member: ExerciseMember, session: Db) -> OmrOutput:
    exercise = omr.active_exercise(session, identifier)
    return output(omr.current(session, exercise), exercise.image_id)


@router.post("/{identifier}/omr/rerun", dependencies=[Depends(require_csrf)])
def rerun(identifier: int, _manager: Manager, session: Db) -> OmrOutput:
    job = omr.rerun(session, identifier)
    return output(job, job.image_id)


@router.post("/{identifier}/omr/review", dependencies=[Depends(require_csrf)])
def review(
    identifier: int, data: ReviewInput, manager: Manager, session: Db
) -> OmrOutput:
    job = omr.review(
        session, identifier, str(data.job_id), manager.user.id, data.action
    )
    return output(job, job.image_id)


@router.api_route("/{identifier}/score", methods=["GET", "HEAD"])
def score(
    identifier: int,
    version: UUID,
    member: ExerciseMember,
    session: Db,
    settings: Configuration,
    response: Response,
) -> Response:
    path = omr.score_file(
        session, identifier, str(version), member.user.role == "manager", settings
    )
    response.headers["X-Accel-Redirect"] = "/_protected_scores/" + path.name
    response.headers["Content-Type"] = "application/vnd.recordare.musicxml+xml"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.status_code = 200
    return response
