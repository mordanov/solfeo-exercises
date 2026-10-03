import pytest

from app.database import Database
from app.services.auth import create_user
from app.settings import Settings

pytestmark = pytest.mark.anyio


def test_check_daily_quota_empty(settings: Settings, database: Database) -> None:
    from app.game.services.avatars import check_daily_quota

    with database.session() as session:
        with session.begin():
            user = create_user(
                session,
                settings,
                username="qtest",
                password="P@ssw0rd!!",
                first_name="Q",
                last_name="T",
                role="student",
                must_change_password=False,
            )
            remaining = check_daily_quota(session, user.id, limit=3)
    assert remaining == 3


def test_check_daily_quota_decrements(settings: Settings, database: Database) -> None:
    from app.game.models import AvatarGenerationLog
    from app.game.services.avatars import check_daily_quota

    with database.session() as session:
        with session.begin():
            user = create_user(
                session,
                settings,
                username="qtest2",
                password="P@ssw0rd!!",
                first_name="Q",
                last_name="T",
                role="student",
                must_change_password=False,
            )
            session.add(AvatarGenerationLog(account_id=user.id, billable=True))
            session.flush()
            remaining = check_daily_quota(session, user.id, limit=3)
    assert remaining == 2


def test_non_billable_does_not_count(settings: Settings, database: Database) -> None:
    from app.game.models import AvatarGenerationLog
    from app.game.services.avatars import check_daily_quota

    with database.session() as session:
        with session.begin():
            user = create_user(
                session,
                settings,
                username="qtest3",
                password="P@ssw0rd!!",
                first_name="Q",
                last_name="T",
                role="student",
                must_change_password=False,
            )
            session.add(AvatarGenerationLog(account_id=user.id, billable=False))
            session.flush()
            remaining = check_daily_quota(session, user.id, limit=3)
    assert remaining == 3
