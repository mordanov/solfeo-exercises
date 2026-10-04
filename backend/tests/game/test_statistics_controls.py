from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import httpx
import pytest
from sqlalchemy import select

from app.database import Database
from app.game.models import Player, Round, Season, TaskAttempt, TrophyAwarded
from app.game.services.players import create_player
from app.game.services.seasons import reset_season
from app.services.auth import create_user
from app.settings import Settings

pytestmark = pytest.mark.anyio


@pytest.fixture
def profiles(settings: Settings, database: Database) -> tuple[int, int, int]:
    with database.session() as session:
        for username, role in (
            ("stats-manager", "manager"),
            ("stats-owner", "student"),
            ("stats-other", "student"),
        ):
            user = create_user(
                session,
                settings,
                username=username,
                password="Statistics-test-password!",
                first_name="Statistics",
                last_name="Test",
                role=role,
                must_change_password=False,
            )
            if role == "student":
                create_player(session, user.id, username, "dragon")
        with session.begin():
            players = list(session.scalars(select(Player).order_by(Player.id)))
            player, other = players
            season = session.scalar(select(Season).where(Season.player_id == player.id))
            assert season is not None
            old_id = season.id
            player.xp = 150
            session.add(TrophyAwarded(player_id=player.id, threshold=20))
            reset_season(session, player.id)
        return player.id, other.id, old_id


async def login(client: httpx.AsyncClient, role: str = "manager") -> str:
    response = await client.post(
        "/api/auth/login",
        json={
            "username": f"stats-{role}",
            "password": "Statistics-test-password!",
        },
    )
    assert response.status_code == 200
    return str(response.json()["csrf_token"])


def seed_rounds(database: Database, player_id: int, season_id: int) -> None:
    now = datetime.now(UTC)
    with database.session() as session, session.begin():
        for index, (difficulty, count, score, correct, status) in enumerate(
            (
                ("easy", 1, 3, 5, "completed"),
                ("easy", 1, 3, 4, "completed"),
                ("hard", 4, 8, 7, "completed"),
                ("easy", 1, 7, 7, "active"),
                ("easy", 1, 7, 7, "expired"),
            )
        ):
            rnd = Round(
                player_id=player_id,
                season_id=season_id,
                difficulty=difficulty,
                note_count=count,
                note_naming="letters",
                status=status,
                score=score,
                correct_count=correct,
                expires_at=now + timedelta(hours=1),
            )
            session.add(rnd)
            session.flush()
            for task, clef in enumerate(("treble", "bass")):
                session.add(
                    TaskAttempt(
                        round_id=rnd.id,
                        season_id=season_id,
                        task_index=task,
                        clef=clef,
                        expected_notes=[{"name": "D", "octave": 4}],
                        given_notes=[{"name": "F", "octave": 4}],
                        is_correct=False,
                        timed_out=False,
                        score=-1,
                        submitted_at=now,
                    )
                )
            if index == 0:
                session.add(
                    TaskAttempt(
                        round_id=rnd.id,
                        season_id=season_id,
                        task_index=2,
                        clef="treble",
                        expected_notes=[{"name": "C", "octave": 4}],
                        given_notes=None,
                        is_correct=False,
                        timed_out=True,
                        score=-1,
                        submitted_at=now,
                    )
                )


async def test_history_stats_include_wins_not_bonus_threshold(
    client: httpx.AsyncClient, database: Database, profiles: tuple[int, int, int]
) -> None:
    player_id, _, old_id = profiles
    seed_rounds(database, player_id, old_id)
    await login(client, "owner")
    current = await client.get(f"/api/game/players/{player_id}/stats")
    assert current.json() == {}
    response = await client.get(
        f"/api/game/players/{player_id}/stats?season_id={old_id}"
    )
    assert response.status_code == 200
    assert response.json()["easy"]["1"] == {
        "rounds": 2,
        "total_correct": 9,
        "avg_score": 3.0,
        "total_score": 6,
        "wins": 1,
        "win_rate": 50.0,
    }
    assert response.json()["hard"]["4"]["wins"] == 1


@pytest.mark.parametrize("path", ["stats", "seasons"])
async def test_students_cannot_read_other_players(
    client: httpx.AsyncClient, profiles: tuple[int, int, int], path: str
) -> None:
    _, other_id, _ = profiles
    await login(client, "owner")
    response = await client.get(f"/api/game/players/{other_id}/{path}")
    assert response.status_code == 404
    assert response.json()["error"] == "PLAYER_NOT_FOUND"


@pytest.mark.parametrize("path", ["stats", "confusion"])
async def test_other_players_season_is_not_selectable(
    client: httpx.AsyncClient, profiles: tuple[int, int, int], path: str
) -> None:
    _, other_id, old_id = profiles
    await login(client)
    response = await client.get(
        f"/api/game/players/{other_id}/{path}?season_id={old_id}"
    )
    assert response.status_code == 404
    assert response.json()["error"] == "SEASON_NOT_FOUND"


async def test_confusion_filters_completed_rounds_and_clef_and_tracks_timeouts(
    client: httpx.AsyncClient, database: Database, profiles: tuple[int, int, int]
) -> None:
    player_id, _, old_id = profiles
    seed_rounds(database, player_id, old_id)
    await login(client)
    base = f"/api/game/players/{player_id}/confusion?season_id={old_id}"
    response = await client.get(base)
    assert response.status_code == 200
    assert response.json()["heatmap"]["D"]["F"] == 6
    assert response.json()["round_top_confusions"] == [
        {"expected": "D", "given": "F", "count": 2}
    ]
    assert response.json()["missed_notes"] == [{"name": "C", "count": 1}]
    bass = await client.get(base + "&clef=bass")
    assert bass.json()["heatmap"]["D"]["F"] == 3
    assert bass.json()["missed_notes"] == []
    assert (await client.get(base + "&clef=invalid")).status_code == 422


async def test_profile_reports_actual_all_time_trophies(
    client: httpx.AsyncClient, profiles: tuple[int, int, int]
) -> None:
    player_id, _, _ = profiles
    await login(client, "owner")
    response = await client.get(f"/api/game/players/{player_id}")
    assert response.json()["trophies"] == [20]
    assert response.json()["xp"] == 150
    assert response.json()["avatar_level"] == 4


async def test_reset_all_preserves_history_and_all_time_progress(
    client: httpx.AsyncClient, database: Database, profiles: tuple[int, int, int]
) -> None:
    player_id, other_id, old_id = profiles
    seed_rounds(database, player_id, old_id)
    csrf = await login(client)
    response = await client.post(
        "/api/game/seasons/reset-all",
        json={"confirmation": "RESET"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert {s["player_id"]: s["number"] for s in response.json()} == {
        player_id: 3,
        other_id: 2,
    }
    player = (await client.get(f"/api/game/players/{player_id}")).json()
    assert player["xp"] == 150
    assert player["avatar_animal"] == "dragon"
    assert player["trophies"] == [20]
    history = await client.get(
        f"/api/game/players/{player_id}/stats?season_id={old_id}"
    )
    assert history.json()["easy"]["1"]["rounds"] == 2
    assert (await client.get(f"/api/game/players/{player_id}/stats")).json() == {}


async def test_reset_after_closed_season_keeps_numbering(
    client: httpx.AsyncClient, database: Database, profiles: tuple[int, int, int]
) -> None:
    player_id, _, _ = profiles
    with database.session() as session, session.begin():
        active = session.scalar(
            select(Season).where(
                Season.player_id == player_id, Season.ended_at.is_(None)
            )
        )
        assert active is not None
        active.ended_at = datetime.now(UTC)
    csrf = await login(client)
    response = await client.post(
        f"/api/game/players/{player_id}/seasons/reset",
        json={"confirmation": "RESET"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert response.json()["number"] == 3


async def test_concurrent_resets_leave_one_active_season(
    database: Database, profiles: tuple[int, int, int]
) -> None:
    player_id, _, _ = profiles
    ready = Barrier(2)

    def reset() -> int:
        with database.session() as session, session.begin():
            ready.wait(timeout=10)
            return reset_season(session, player_id).number

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: reset(), range(2)))
    assert sorted(results) == [3, 4]
    with database.session() as session:
        active = list(
            session.scalars(
                select(Season).where(
                    Season.player_id == player_id, Season.ended_at.is_(None)
                )
            )
        )
        assert len(active) == 1
        assert active[0].number == 4


@pytest.mark.parametrize(
    "role,confirmation,csrf_present,status",
    [
        ("owner", "RESET", True, 403),
        ("manager", "wrong", True, 400),
        ("manager", "RESET", False, 403),
    ],
)
async def test_rejected_bulk_resets_leave_seasons_unchanged(
    client: httpx.AsyncClient,
    database: Database,
    profiles: tuple[int, int, int],
    role: str,
    confirmation: str,
    csrf_present: bool,
    status: int,
) -> None:
    player_id, other_id, _ = profiles
    csrf = await login(client, role)
    response = await client.post(
        "/api/game/seasons/reset-all",
        json={"confirmation": confirmation},
        headers={"X-CSRF-Token": csrf} if csrf_present else {},
    )
    assert response.status_code == status
    with database.session() as session:
        active = list(session.scalars(select(Season).where(Season.ended_at.is_(None))))
        assert {season.player_id: season.number for season in active} == {
            player_id: 2,
            other_id: 1,
        }
