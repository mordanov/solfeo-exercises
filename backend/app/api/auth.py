import hmac
from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.appearance import ColorScheme, UiFont, UiFontSize
from app.models import User
from app.services import auth
from app.settings import Settings

router = APIRouter(prefix="/api")
Db = Annotated[Session, Depends(get_session)]
COOKIE = "solfeo_session"


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginInput(Input):
    username: str = Field(min_length=1, max_length=64)
    password: SecretStr = Field(min_length=1, max_length=256)


class UserOutput(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    role: Literal["manager", "student", "player"]
    is_active: bool
    is_emergency: bool
    must_change_password: bool
    ui_language: Literal["ru", "en", "es"]
    note_naming: Literal["letters", "solfege"]
    light_scheme: ColorScheme
    dark_scheme: ColorScheme
    ui_font: UiFont
    ui_font_size: UiFontSize


def user_output(user: User) -> UserOutput:
    return UserOutput.model_validate(
        {key: getattr(user, key) for key in UserOutput.model_fields}
    )


class AuthOutput(BaseModel):
    user: UserOutput
    csrf_token: str


class UserListOutput(BaseModel):
    users: list[UserOutput]
    total: int


class StatusOutput(BaseModel):
    status: Literal["ok"] = "ok"


class CreateUserInput(LoginInput):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: Literal["manager", "student", "player"]
    must_change_password: bool = True

    @field_validator("first_name", "last_name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("EMPTY_NAME")
        return value.strip()


class UpdateUserInput(Input):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: Literal["manager", "student", "player"] | None = None
    is_active: bool | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def nonblank_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("EMPTY_NAME")
        return value.strip() if value is not None else None


class ResetPasswordInput(Input):
    password: SecretStr = Field(min_length=1, max_length=256)
    must_change_password: bool = True


class ChangePasswordInput(Input):
    current_password: SecretStr = Field(min_length=1, max_length=256)
    new_password: SecretStr = Field(min_length=1, max_length=256)


class SettingsInput(Input):
    ui_language: Literal["ru", "en", "es"] | None = None
    note_naming: Literal["letters", "solfege"] | None = None
    light_scheme: ColorScheme | None = None
    dark_scheme: ColorScheme | None = None
    ui_font: UiFont | None = None
    ui_font_size: UiFontSize | None = None

    @field_validator(
        "ui_language",
        "note_naming",
        "light_scheme",
        "dark_scheme",
        "ui_font",
        "ui_font_size",
    )
    @classmethod
    def reject_null(cls, value: str | int | None) -> str | int:
        if value is None:
            raise ValueError("NULL_SETTING")
        return value

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("EMPTY_SETTINGS")
        return self


def get_settings(request: Request) -> Settings:
    settings = request.app.state.settings
    if not isinstance(settings, Settings):
        raise RuntimeError("SETTINGS_NOT_INITIALIZED")
    return settings


Configuration = Annotated[Settings, Depends(get_settings)]


def require_origin(request: Request, settings: Configuration) -> None:
    if request.headers.get("origin") not in settings.auth_allowed_origins:
        raise auth.ServiceError("CSRF_FAILED", 403)


def set_cookie(response: Response, identity: auth.Identity, settings: Settings) -> None:
    response.set_cookie(
        COOKIE,
        identity.token,
        max_age=settings.session_lifetime_days * 86400,
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )


def require_identity(
    request: Request, response: Response, session: Db, settings: Configuration
) -> auth.Identity:
    identity = auth.authenticate(session, settings, request.cookies.get(COOKIE))
    set_cookie(response, identity, settings)
    return identity


Current = Annotated[auth.Identity, Depends(require_identity)]


def require_member(identity: Current) -> auth.Identity:
    if identity.user.must_change_password:
        raise auth.ServiceError("PASSWORD_CHANGE_REQUIRED", 403)
    return identity


Member = Annotated[auth.Identity, Depends(require_member)]


def require_student_or_manager(identity: Member) -> auth.Identity:
    if identity.user.role not in {"student", "manager"}:
        raise auth.ServiceError("FORBIDDEN", 403)
    return identity


ExerciseMember = Annotated[auth.Identity, Depends(require_student_or_manager)]


def require_manager(identity: Member) -> auth.Identity:
    if identity.user.role != "manager":
        raise auth.ServiceError("FORBIDDEN", 403)
    return identity


Manager = Annotated[auth.Identity, Depends(require_manager)]


def require_csrf(request: Request, identity: Current, settings: Configuration) -> None:
    require_origin(request, settings)
    if not hmac.compare_digest(
        request.headers.get("x-csrf-token", "").encode(),
        identity.session.csrf_token.encode(),
    ):
        raise auth.ServiceError("CSRF_FAILED", 403)


def auth_output(identity: auth.Identity) -> AuthOutput:
    return AuthOutput(
        user=user_output(identity.user), csrf_token=identity.session.csrf_token
    )


@router.post("/auth/login", dependencies=[Depends(require_origin)])
def login(
    data: LoginInput,
    request: Request,
    response: Response,
    session: Db,
    settings: Configuration,
) -> AuthOutput:
    ip = request.client.host if request.client else "unknown"
    identity = auth.login(
        session,
        settings,
        data.username,
        data.password.get_secret_value(),
        ip,
        request.cookies.get(COOKIE),
    )
    set_cookie(response, identity, settings)
    return auth_output(identity)


@router.get("/auth/me")
def me(identity: Current) -> AuthOutput:
    return auth_output(identity)


@router.post("/auth/logout", dependencies=[Depends(require_csrf)])
def logout(
    identity: Current, session: Db, response: Response, settings: Configuration
) -> StatusOutput:
    auth.logout(session, identity)
    response.delete_cookie(
        COOKIE,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return StatusOutput()


@router.put("/auth/password", dependencies=[Depends(require_csrf)])
def change_password(
    data: ChangePasswordInput,
    identity: Current,
    session: Db,
    response: Response,
    settings: Configuration,
) -> AuthOutput:
    updated = auth.change_password(
        session,
        settings,
        identity,
        data.current_password.get_secret_value(),
        data.new_password.get_secret_value(),
    )
    set_cookie(response, updated, settings)
    return auth_output(updated)


@router.patch("/settings", dependencies=[Depends(require_csrf)])
def settings_update(data: SettingsInput, identity: Member, session: Db) -> UserOutput:
    return user_output(
        auth.update_settings(
            session,
            identity,
            data.ui_language,
            data.note_naming,
            light_scheme=data.light_scheme,
            dark_scheme=data.dark_scheme,
            ui_font=data.ui_font,
            ui_font_size=data.ui_font_size,
        )
    )


@router.get("/users")
def users(
    _manager: Manager,
    session: Db,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> UserListOutput:
    rows, total = auth.list_users(session, offset, limit)
    return UserListOutput(users=[user_output(user) for user in rows], total=total)


@router.post("/users", status_code=201, dependencies=[Depends(require_csrf)])
def create_user(
    data: CreateUserInput, _manager: Manager, session: Db, settings: Configuration
) -> UserOutput:
    return user_output(
        auth.create_user(
            session,
            settings,
            username=data.username,
            password=data.password.get_secret_value(),
            first_name=data.first_name,
            last_name=data.last_name,
            role=data.role,
            must_change_password=data.must_change_password,
        )
    )


@router.patch("/users/{user_id}", dependencies=[Depends(require_csrf)])
def update_user(
    user_id: int, data: UpdateUserInput, manager: Manager, session: Db
) -> UserOutput:
    return user_output(
        auth.update_user(
            session,
            manager,
            user_id,
            first_name=data.first_name,
            last_name=data.last_name,
            role=data.role,
            is_active=data.is_active,
        )
    )


@router.post("/users/{user_id}/password", dependencies=[Depends(require_csrf)])
def reset_password(
    user_id: int,
    data: ResetPasswordInput,
    manager: Manager,
    session: Db,
    settings: Configuration,
) -> StatusOutput:
    auth.reset_password(
        session,
        settings,
        manager,
        user_id,
        data.password.get_secret_value(),
        data.must_change_password,
    )
    return StatusOutput()
