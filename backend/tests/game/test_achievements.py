from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select

from app.database import Database
from app.game.models import AchievementAwarded, Player, Round, Season, TaskAttempt
from app.game.services.achievements import ACHIEVEMENT_CODES, evaluate_achievements
from app.game.services.seasons import reset_season
from app.services.auth import create_user
from app.settings import Settings


@pytest.mark.anyio
async def test_achievement_collection_requires_authentication_and_ownership(
    client: httpx.AsyncClient, database: Database, settings: Settings
) -> None:
    account_ids: list[int] = []
    with database.session() as session:
        for index, username in enumerate(("prize-api-owner", "prize-api-other")):
            user = create_user(
                session,
                settings,
                username=username,
                password="test-password-123",
                first_name="Prize",
                last_name="API",
                role="student" if index == 0 else "manager",
                must_change_password=False,
            )
            account_ids.append(user.id)
        with session.begin():
            profiles = [
                Player(account_id=account_id, name=f"API {index}")
                for index, account_id in enumerate(account_ids)
            ]
            session.add_all(profiles)
            session.flush()
            owner_id, other_id = [profile.id for profile in profiles]
    path = f"/api/game/players/{owner_id}/achievements"
    other_path = f"/api/game/players/{other_id}/achievements"
    assert (await client.get(path)).status_code == 401
    assert (
        await client.post(
            "/api/auth/login",
            json={"username": "prize-api-owner", "password": "test-password-123"},
        )
    ).status_code == 200
    response = await client.get(path)
    assert response.status_code == 200
    assert response.json()["earned"] == []
    assert len(response.json()["catalog"]) == 20
    assert (await client.get(other_path)).status_code == 404
    assert (
        await client.post(
            "/api/auth/login",
            json={"username": "prize-api-other", "password": "test-password-123"},
        )
    ).status_code == 200
    assert (await client.get(path)).status_code == 200


def test_achievement_catalog_has_twenty_distinct_rewards() -> None:
    assert len(ACHIEVEMENT_CODES) == len(set(ACHIEVEMENT_CODES)) == 20


def test_rewards_count_positions_days_and_streaks_and_survive_reset(
    database: Database, settings: Settings
) -> None:
    settings.game_timezone = "Europe/Madrid"
    with database.session() as session:
        user = create_user(
            session,
            settings,
            username="achievement-owner",
            password="synthetic-achievement-password",
            first_name="Prize",
            last_name="Owner",
            role="student",
            must_change_password=False,
        )
        with session.begin():
            player = Player(account_id=user.id, name="Prize", xp=250)
            session.add(player)
            session.flush()
            season = Season(player_id=player.id, number=1)
            session.add(season)
            session.flush()
            now = datetime.now(UTC)
            for index in range(15):
                completed = now - timedelta(days=14 - index)
                record = Round(
                    player_id=player.id,
                    season_id=season.id,
                    difficulty=("easy", "medium", "hard")[index % 3],
                    note_count=(index % 4) + 1,
                    note_naming="letters",
                    status="completed",
                    score=7,
                    correct_count=7,
                    completed_at=completed,
                    expires_at=completed + timedelta(hours=1),
                    show_sound_hint=False,
                    show_correct_answer=False,
                    rules_version=2,
                )
                session.add(record)
                session.flush()
                for task_index, name in enumerate("CDEFGAB"):
                    notes = [{"name": name, "octave": 4}] * record.note_count
                    session.add(
                        TaskAttempt(
                            round_id=record.id,
                            season_id=season.id,
                            task_index=task_index,
                            clef="treble" if task_index % 2 else "bass",
                            expected_notes=notes,
                            given_notes=notes,
                            is_correct=True,
                            timed_out=False,
                            score=1,
                            submitted_at=completed,
                        )
                    )
            session.flush()
            prizes = evaluate_achievements(session, player, record, settings)
            assert set(prizes) == set(ACHIEVEMENT_CODES) - {"welcome_back"}
            assert evaluate_achievements(session, player, record, settings) == []
            player_id = player.id
        with session.begin():
            reset_season(session, player_id)
        assert (
            len(
                list(
                    session.scalars(
                        select(AchievementAwarded).where(
                            AchievementAwarded.player_id == player_id
                        )
                    )
                )
            )
            == 19
        )
        saved_player = session.get(Player, player_id)
        assert saved_player is not None and saved_player.xp == 250


def test_correct_positions_count_without_partial_task_xp_and_ignore_active_rounds(
    database: Database, settings: Settings
) -> None:
    with database.session() as session:
        user = create_user(
            session,
            settings,
            username="partial-prize",
            password="synthetic-achievement-password",
            first_name="Partial",
            last_name="Prize",
            role="student",
            must_change_password=False,
        )
        with session.begin():
            player = Player(account_id=user.id, name="Partial", xp=0)
            session.add(player)
            session.flush()
            season = Season(player_id=player.id, number=1)
            session.add(season)
            session.flush()
            now = datetime.now(UTC)
            for index in range(5):
                date = now - timedelta(days=8 if index == 0 else 0)
                record = Round(
                    player_id=player.id,
                    season_id=season.id,
                    difficulty="easy",
                    note_count=4,
                    note_naming="letters",
                    status="active" if index == 4 else "completed",
                    score=0,
                    correct_count=0,
                    rules_version=2,
                    completed_at=date,
                    expires_at=now + timedelta(hours=1),
                )
                session.add(record)
                session.flush()
                for task_index in range(7):
                    session.add(
                        TaskAttempt(
                            round_id=record.id,
                            season_id=season.id,
                            task_index=task_index,
                            clef="treble",
                            expected_notes=[{"name": n, "octave": 4} for n in "CDEG"],
                            given_notes=[{"name": n, "octave": 4} for n in "CDFG"],
                            is_correct=False,
                            timed_out=False,
                            score=-1,
                            submitted_at=date,
                        )
                    )
            session.flush()
            assert set(evaluate_achievements(session, player, record, settings)) == {
                "first_round",
                "welcome_back",
            }
            record.status = "completed"
            assert evaluate_achievements(session, player, record, settings) == [
                "notes_100"
            ]
            assert player.xp == 0
