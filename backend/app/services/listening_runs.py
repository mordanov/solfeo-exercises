from typing import Literal

from sqlalchemy.orm import Session

from app.models import ListeningRun


def active_run(session: Session, user_id: int) -> ListeningRun | None:
    raise NotImplementedError


def start_run(session: Session, user_id: int, chapter_ids: list[int]) -> ListeningRun:
    raise NotImplementedError


def move_run(
    session: Session, user_id: int, direction: Literal["next", "previous"]
) -> ListeningRun:
    raise NotImplementedError


def cancel_run(session: Session, user_id: int) -> ListeningRun:
    raise NotImplementedError
