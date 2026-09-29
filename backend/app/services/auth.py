import hashlib
import hmac
import logging
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.database import Database
from app.models import LoginLimit, LoginSession, User
from app.settings import Settings

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    def __init__(self, code: str, status: int, retry_after: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.retry_after = retry_after


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    value = hashlib.scrypt(
        password.encode(), salt=salt, n=32768, r=8, p=3, maxmem=64 * 1024 * 1024
    )
    return f"scrypt${salt.hex()}${value.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt_hex, value_hex = stored.split("$")
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(value_hex)
        if algorithm != "scrypt" or len(salt) != 16 or len(expected) != 64:
            raise ValueError("INVALID_STORED_PASSWORD_HASH")
    except ValueError:
        logger.error("INVALID_STORED_PASSWORD_HASH")
        return False
    actual = hashlib.scrypt(
        password.encode(), salt=salt, n=32768, r=8, p=3, maxmem=64 * 1024 * 1024
    )
    return hmac.compare_digest(actual, expected)


DUMMY_HASH = hash_password("unusable-random-" + secrets.token_hex(32))


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def require_password(password: str, settings: Settings) -> None:
    if not settings.password_min_length <= len(password) <= 256:
        raise ServiceError("WEAK_PASSWORD", 422)


def administration_lock(session: Session) -> None:
    session.execute(text("SELECT pg_advisory_xact_lock(710024001)"))


def revoke_sessions(session: Session, user_id: int) -> None:
    session.execute(delete(LoginSession).where(LoginSession.user_id == user_id))


def sync_emergency(database: Database, settings: Settings) -> None:
    username = settings.emergency_manager_username.lower()
    password = settings.emergency_manager_password.get_secret_value()
    password_hash = hash_password(password) if username else None
    with database.session() as session, session.begin():
        administration_lock(session)
        for previous in session.scalars(select(User).where(User.is_emergency)):
            previous.is_active = False
            revoke_sessions(session, previous.id)
            if username and previous.username != username:
                previous.is_emergency = False
        session.flush()
        if not username:
            return
        user = session.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(
                username=username,
                ui_language=settings.default_language,
                note_naming="letters",
            )
            session.add(user)
        else:
            revoke_sessions(session, user.id)
        assert password_hash is not None
        user.first_name = settings.emergency_manager_first_name
        user.last_name = settings.emergency_manager_last_name
        user.role = "manager"
        user.password_hash = password_hash
        user.is_active = True
        user.is_emergency = True
        user.must_change_password = False


@dataclass
class Identity:
    user: User
    session: LoginSession
    token: str


def new_session(session: Session, user: User, settings: Settings) -> Identity:
    token = secrets.token_urlsafe(32)
    entry = LoginSession(
        token_hash=token_hash(token),
        user_id=user.id,
        csrf_token=secrets.token_urlsafe(32),
        expires_at=datetime.now(UTC) + timedelta(days=settings.session_lifetime_days),
    )
    session.add(entry)
    session.flush()
    return Identity(user, entry, token)


def login(
    session: Session,
    settings: Settings,
    username: str,
    password: str,
    ip: str,
    old_token: str | None,
) -> Identity:
    username = username.strip().lower()
    now = datetime.now(UTC)
    limits = [
        ("u:" + token_hash(username), settings.login_username_limit),
        ("ip:" + token_hash(ip), settings.login_ip_limit),
    ]
    outcome: Identity | ServiceError = ServiceError("INVALID_CREDENTIALS", 401)
    with session.begin():
        # Fixed lock ordering makes concurrent attempts share one persistent budget.
        for key, _ in sorted(limits):
            lock_id = int.from_bytes(
                hashlib.sha256(key.encode()).digest()[:8], signed=True
            )
            session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id}
            )
        session.execute(delete(LoginLimit).where(LoginLimit.expires_at <= now))
        session.execute(delete(LoginSession).where(LoginSession.expires_at <= now))
        buckets: list[LoginLimit] = []
        for key, maximum in limits:
            bucket = session.get(LoginLimit, key)
            if bucket is None:
                bucket = LoginLimit(
                    key=key,
                    attempts=0,
                    expires_at=now + timedelta(seconds=settings.login_window_seconds),
                )
                session.add(bucket)
            buckets.append(bucket)
            if bucket.attempts >= maximum:
                outcome = ServiceError(
                    "RATE_LIMITED",
                    429,
                    max(1, int((bucket.expires_at - now).total_seconds()) + 1),
                )
        if isinstance(outcome, ServiceError) and outcome.code != "RATE_LIMITED":
            for bucket in buckets:
                bucket.attempts += 1
            user = session.scalar(
                select(User).where(User.username == username).with_for_update()
            )
            valid = verify_password(
                password, user.password_hash if user else DUMMY_HASH
            )
            if valid and user is not None and user.is_active:
                session.delete(buckets[0])
                if old_token:
                    session.execute(
                        delete(LoginSession).where(
                            LoginSession.token_hash == token_hash(old_token)
                        )
                    )
                outcome = new_session(session, user, settings)
    if isinstance(outcome, ServiceError):
        raise outcome
    return outcome


def authenticate(session: Session, settings: Settings, token: str | None) -> Identity:
    if not token or len(token) > 128:
        raise ServiceError("AUTH_REQUIRED", 401)
    with session.begin():
        entry = session.scalar(
            select(LoginSession)
            .where(LoginSession.token_hash == token_hash(token))
            .with_for_update()
        )
        if entry is None or entry.expires_at <= datetime.now(UTC):
            raise ServiceError("AUTH_REQUIRED", 401)
        user = session.get(User, entry.user_id)
        if user is None or not user.is_active:
            raise ServiceError("AUTH_REQUIRED", 401)
        entry.expires_at = datetime.now(UTC) + timedelta(
            days=settings.session_lifetime_days
        )
        return Identity(user, entry, token)


def logout(session: Session, identity: Identity) -> None:
    with session.begin():
        session.execute(
            delete(LoginSession).where(
                LoginSession.token_hash == identity.session.token_hash
            )
        )


def change_password(
    session: Session,
    settings: Settings,
    identity: Identity,
    current: str,
    replacement: str,
) -> Identity:
    require_password(replacement, settings)
    with session.begin():
        user = session.scalar(
            select(User)
            .where(User.id == identity.user.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if user is None or not user.is_active:
            raise ServiceError("AUTH_REQUIRED", 401)
        if user.is_emergency:
            raise ServiceError("EMERGENCY_USER_PROTECTED", 403)
        if not verify_password(current, user.password_hash):
            raise ServiceError("CURRENT_PASSWORD_INVALID", 400)
        user.password_hash = hash_password(replacement)
        user.must_change_password = False
        revoke_sessions(session, user.id)
        return new_session(session, user, settings)


def update_settings(
    session: Session, identity: Identity, language: str, naming: str
) -> User:
    with session.begin():
        identity.user.ui_language = language
        identity.user.note_naming = naming
    return identity.user


def list_users(session: Session, offset: int, limit: int) -> tuple[list[User], int]:
    with session.begin():
        count = session.scalar(select(func.count()).select_from(User))
        users = list(
            session.scalars(select(User).order_by(User.id).offset(offset).limit(limit))
        )
    return users, count or 0


def create_user(
    session: Session,
    settings: Settings,
    *,
    username: str,
    password: str,
    first_name: str,
    last_name: str,
    role: str,
    must_change_password: bool,
) -> User:
    username = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,63}", username):
        raise ServiceError("INVALID_USERNAME", 422)
    require_password(password, settings)
    password_hash = hash_password(password)
    with session.begin():
        administration_lock(session)
        if session.scalar(select(User.id).where(User.username == username)) is not None:
            raise ServiceError("USERNAME_TAKEN", 409)
        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role,
            password_hash=password_hash,
            ui_language=settings.default_language,
            note_naming="letters",
            must_change_password=must_change_password,
        )
        session.add(user)
        session.flush()
    return user


def editable_user(session: Session, identity: Identity, user_id: int) -> User:
    administration_lock(session)
    user = session.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None:
        raise ServiceError("USER_NOT_FOUND", 404)
    if user.is_emergency:
        raise ServiceError("EMERGENCY_USER_PROTECTED", 403)
    if user.id == identity.user.id:
        raise ServiceError("SELF_CHANGE_FORBIDDEN", 403)
    return user


def update_user(
    session: Session,
    identity: Identity,
    user_id: int,
    *,
    first_name: str | None,
    last_name: str | None,
    role: str | None,
    is_active: bool | None,
) -> User:
    with session.begin():
        user = editable_user(session, identity, user_id)
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active
        if role is not None or is_active is False:
            revoke_sessions(session, user.id)
    return user


def reset_password(
    session: Session,
    settings: Settings,
    identity: Identity,
    user_id: int,
    password: str,
    must_change: bool,
) -> None:
    require_password(password, settings)
    password_hash = hash_password(password)
    with session.begin():
        user = editable_user(session, identity, user_id)
        user.password_hash = password_hash
        user.must_change_password = must_change
        revoke_sessions(session, user.id)
