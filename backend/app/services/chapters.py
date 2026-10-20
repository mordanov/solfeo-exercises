from sqlalchemy.orm import Session

from app.models import Chapter


def list_chapters(session: Session, *, nonempty_only: bool) -> list[Chapter]:
    raise NotImplementedError


def create_chapter(session: Session) -> Chapter:
    raise NotImplementedError


def delete_chapter(session: Session, chapter_id: int) -> None:
    raise NotImplementedError
