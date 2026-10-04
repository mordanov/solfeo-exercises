from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select

from app.database import Database
from app.game.models import CustomAvatar, Player
from app.game.services.players import choose_avatar, update_player
from app.services.auth import create_user
from app.settings import Settings


def _create_player(
    database: Database, settings: Settings, username: str
) -> tuple[int, int, int]:
    with database.session() as session:
        user = create_user(
            session,
            settings,
            username=username,
            password="test-password-123",
            first_name="Avatar",
            last_name="Choice",
            role="student",
            must_change_password=False,
        )
        with session.begin():
            player = Player(account_id=user.id, name="Choice", avatar_animal="dragon")
            session.add(player)
            session.flush()
            job = CustomAvatar(
                account_id=user.id,
                player_id=player.id,
                description="Synthetic choice",
                status="ready",
                review_status="approved",
            )
            session.add(job)
            session.flush()
            job.base_path = f"avatars/custom/{job.id}/base.png"
            job.happy_path = f"avatars/custom/{job.id}/happy.png"
            job.sad_path = f"avatars/custom/{job.id}/sad.png"
            waiting = CustomAvatar(
                account_id=user.id,
                player_id=player.id,
                description="Synthetic pending choice",
                status="ready",
                review_status="pending",
            )
            session.add(waiting)
            session.flush()
            player.avatar_review_job_id = waiting.id
            return player.id, job.id, waiting.id


@pytest.mark.parametrize("method", ["choose", "update"])
def test_builtin_choice_refreshes_player_after_concurrent_approval(
    database: Database, settings: Settings, method: str
) -> None:
    player_id, _, job_id = _create_player(database, settings, f"avatar-choice-{method}")
    with database.session() as stale_session:
        stale = stale_session.get(Player, player_id)
        assert stale is not None and stale.custom_avatar_id is None
        stale_session.commit()
        with database.session() as review_session, review_session.begin():
            reviewed = review_session.get(Player, player_id)
            assert reviewed is not None
            approved = review_session.get(CustomAvatar, job_id)
            assert approved is not None
            approved.review_status = "approved"
            reviewed.custom_avatar_id = job_id
            reviewed.avatar_review_job_id = None
        if method == "choose":
            choose_avatar(stale_session, player_id, "dragon", None)
        else:
            update_player(stale_session, player_id, settings, avatar_animal="dragon")
    with database.session() as session:
        saved = session.get(Player, player_id)
        assert saved is not None
        assert saved.custom_avatar_id is None
        assert saved.avatar_review_job_id is None


def test_explicit_approved_choice_clears_waiting_review(
    database: Database, settings: Settings, tmp_path: Path
) -> None:
    player_id, job_id, _ = _create_player(database, settings, "avatar-choice-custom")
    settings.media_root = tmp_path
    directory = tmp_path / f"avatars/custom/{job_id}"
    directory.mkdir(parents=True)
    for mood in ("base", "happy", "sad"):
        Image.new("RGBA", (32, 32), "red").save(directory / f"{mood}.png")
    with database.session() as session:
        update_player(session, player_id, settings, custom_avatar_id=job_id)
    with database.session() as session:
        saved = session.scalar(select(Player).where(Player.id == player_id))
        assert saved is not None
        assert saved.custom_avatar_id == job_id
        assert saved.avatar_review_job_id is None
