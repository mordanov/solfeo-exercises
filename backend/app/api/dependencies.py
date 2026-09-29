from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from app.database import Database


def get_session(request: Request) -> Iterator[Session]:
    database = request.app.state.database
    if not isinstance(database, Database):
        raise RuntimeError("DATABASE_NOT_INITIALIZED")
    with database.session() as session:
        yield session
