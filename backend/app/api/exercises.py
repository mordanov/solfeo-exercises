from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Query, Response, UploadFile
from pydantic import BaseModel, Field, field_validator

from app.api.auth import (
    Configuration,
    Db,
    Input,
    Manager,
    Member,
    StatusOutput,
    require_csrf,
)
from app.models import Exercise, MediaFile
from app.services import exercises
from app.services.auth import ServiceError

router = APIRouter(prefix="/api/exercises")


class ExerciseInput(Input):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    category: str | None = Field(default=None, max_length=100)
    remove_image: bool = False
    remove_audio: bool = False
    image: UploadFile | None = None
    audio: UploadFile | None = None

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("EMPTY_TITLE")
        return value.strip()

    @field_validator("category")
    @classmethod
    def optional_category(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value else None


class MediaOutput(BaseModel):
    id: str
    mime_type: str
    size_bytes: int
    duration_seconds: float | None


class ExerciseOutput(BaseModel):
    id: int
    title: str
    description: str
    category: str | None
    position: int
    image: MediaOutput | None
    audio: MediaOutput | None


class ExerciseListOutput(BaseModel):
    exercises: list[ExerciseOutput]
    total: int


class OrderInput(Input):
    ids: list[int] = Field(max_length=10000)


def output(row: Exercise, session: Db) -> ExerciseOutput:
    def media(identifier: str | None) -> MediaOutput | None:
        value = session.get(MediaFile, identifier) if identifier else None
        return (
            MediaOutput(
                id=value.id,
                mime_type=value.mime_type,
                size_bytes=value.size_bytes,
                duration_seconds=value.duration_seconds,
            )
            if value
            else None
        )

    return ExerciseOutput(
        id=row.id,
        title=row.title,
        description=row.description,
        category=row.category,
        position=row.position,
        image=media(row.image_id),
        audio=media(row.audio_id),
    )


@router.get("")
def listing(
    _member: Member,
    session: Db,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=10000)] = 10000,
) -> ExerciseListOutput:
    rows, total = exercises.list_exercises(session, offset, limit)
    return ExerciseListOutput(
        exercises=[output(row, session) for row in rows], total=total
    )


@router.put("/order", dependencies=[Depends(require_csrf)])
def order(data: OrderInput, _manager: Manager, session: Db) -> StatusOutput:
    exercises.reorder(session, data.ids)
    return StatusOutput()


def save(
    data: ExerciseInput, identifier: int | None, session: Db, settings: Configuration
) -> ExerciseOutput:
    row = exercises.save_exercise(
        session,
        settings,
        identifier,
        title=data.title,
        description=data.description,
        category=data.category,
        image=data.image.file if data.image else None,
        audio=data.audio.file if data.audio else None,
        remove_image=data.remove_image,
        remove_audio=data.remove_audio,
    )
    return output(row, session)


@router.post("", status_code=201, dependencies=[Depends(require_csrf)])
def create(
    data: Annotated[ExerciseInput, Form()],
    _manager: Manager,
    session: Db,
    settings: Configuration,
) -> ExerciseOutput:
    return save(data, None, session, settings)


@router.put("/{identifier}", dependencies=[Depends(require_csrf)])
def update(
    identifier: int,
    data: Annotated[ExerciseInput, Form()],
    _manager: Manager,
    session: Db,
    settings: Configuration,
) -> ExerciseOutput:
    return save(data, identifier, session, settings)


@router.get("/{identifier}")
def detail(identifier: int, _member: Member, session: Db) -> ExerciseOutput:
    return output(exercises.get_exercise(session, identifier), session)


@router.delete("/{identifier}", dependencies=[Depends(require_csrf)])
def delete(identifier: int, _manager: Manager, session: Db) -> StatusOutput:
    exercises.delete_exercise(session, identifier)
    return StatusOutput()


@router.api_route("/{identifier}/files/{kind}", methods=["GET", "HEAD"])
def protected_file(
    identifier: int,
    kind: Literal["image", "audio"],
    _member: Member,
    session: Db,
    settings: Configuration,
    response: Response,
    version: UUID | None = None,
) -> Response:
    media = exercises.get_media(session, identifier, kind)
    if version is not None and str(version) != media.id:
        raise ServiceError("FILE_NOT_FOUND", 404)
    if not (settings.media_root / media.filename).is_file():
        raise ServiceError("FILE_NOT_FOUND", 404)
    response.headers["X-Accel-Redirect"] = "/_protected_media/" + media.filename
    response.headers["Content-Type"] = media.mime_type
    response.headers["Content-Disposition"] = f'inline; filename="{media.filename}"'
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.status_code = 200
    return response
