from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field, field_validator

from app.api.auth import Configuration, Db, Input, Manager, StatusOutput, require_csrf
from app.models import TelegramLink, TelegramState
from app.services import telegram
from app.services.auth import ServiceError

router = APIRouter(prefix="/api/telegram")


class LinkOutput(BaseModel):
    linked: bool
    available: bool
    bot_username: str


class CodeOutput(BaseModel):
    code: str
    expires_at: datetime


class ImportOutput(BaseModel):
    id: int
    title: str
    description: str
    status: str
    last_error: str | None
    exercise_id: int | None
    received_at: datetime


class ImportListOutput(BaseModel):
    imports: list[ImportOutput]
    total: int


class ApplyInput(Input):
    exercise_id: int | None = Field(default=None, gt=0)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)

    @field_validator("title")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("EMPTY_TITLE")
        return value.strip()


class AppliedOutput(BaseModel):
    exercise_id: int


@router.get("")
def status(identity: Manager, session: Db, settings: Configuration) -> LinkOutput:
    state = session.get(TelegramState, 1)
    return LinkOutput(
        linked=session.get(TelegramLink, identity.user.id) is not None,
        available=state is not None
        and (datetime.now(UTC) - state.heartbeat_at).total_seconds()
        < settings.telegram_health_seconds,
        bot_username=settings.telegram_bot_username,
    )


@router.post("/link", dependencies=[Depends(require_csrf)])
def link(identity: Manager, session: Db, settings: Configuration) -> CodeOutput:
    code, expires = telegram.create_code(session, identity.user.id, settings)
    return CodeOutput(code=code, expires_at=expires)


@router.delete("/link", dependencies=[Depends(require_csrf)])
def unlink(identity: Manager, session: Db) -> StatusOutput:
    telegram.unlink(session, identity.user.id)
    return StatusOutput()


@router.get("/imports")
def imports(
    identity: Manager,
    session: Db,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ImportListOutput:
    rows, total = telegram.list_imports(session, identity.user.id, offset, limit)
    return ImportListOutput(
        imports=[
            ImportOutput.model_validate(
                {key: getattr(row, key) for key in ImportOutput.model_fields}
            )
            for row in rows
        ],
        total=total,
    )


@router.post("/imports/{identifier}/apply", dependencies=[Depends(require_csrf)])
def apply(
    identifier: int, data: ApplyInput, identity: Manager, session: Db
) -> AppliedOutput:
    return AppliedOutput(
        exercise_id=telegram.apply_import(
            session,
            identity.user.id,
            identifier,
            data.exercise_id,
            data.title,
            data.description,
        )
    )


@router.post("/imports/{identifier}/retry", dependencies=[Depends(require_csrf)])
def retry(identifier: int, identity: Manager, session: Db) -> StatusOutput:
    telegram.retry_import(session, identity.user.id, identifier)
    return StatusOutput()


@router.api_route("/imports/{identifier}/audio", methods=["GET", "HEAD"])
def audio(
    identifier: int,
    identity: Manager,
    session: Db,
    settings: Configuration,
    response: Response,
) -> Response:
    media = telegram.import_media(session, identity.user.id, identifier)
    if not (settings.media_root / media.filename).is_file():
        raise ServiceError("FILE_NOT_FOUND", 404)
    response.headers["X-Accel-Redirect"] = "/_protected_media/" + media.filename
    response.headers["Content-Type"] = media.mime_type
    response.headers["Content-Disposition"] = f'inline; filename="{media.filename}"'
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.status_code = 200
    return response
