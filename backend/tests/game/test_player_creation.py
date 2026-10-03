import httpx
import pytest
from sqlalchemy import select

from app.database import Database
from app.game.models import Player, Season
from app.services.auth import create_user
from app.settings import Settings


@pytest.mark.anyio
async def test_manager_assigns_first_profile_and_student_can_start(
    client: httpx.AsyncClient, database: Database, settings: Settings
) -> None:
    account_ids: dict[str, int] = {}
    with database.session() as session:
        for username, role in (
            ("creator", "manager"),
            ("learner", "student"),
            ("disabled", "student"),
        ):
            user = create_user(
                session,
                settings,
                username=username,
                password="synthetic-first-game",
                first_name=username,
                last_name="Test",
                role=role,
                must_change_password=False,
            )
            account_ids[username] = user.id
            if username == "disabled":
                user.is_active = False
        session.commit()
    student_id = account_ids["learner"]
    login = await client.post(
        "/api/auth/login",
        json={"username": "creator", "password": "synthetic-first-game"},
    )
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    assert (await client.get("/api/game/players")).json() == []
    response = await client.post(
        "/api/game/players",
        json={
            "name": "First player",
            "account_id": student_id,
            "avatar_animal": "lion",
        },
    )
    assert response.status_code == 200
    player = response.json()
    assert player["account_id"] == student_id
    assert player["avatar_level"] == 1
    with database.session() as session:
        assert (
            session.scalar(
                select(Season).where(
                    Season.player_id == player["id"], Season.ended_at.is_(None)
                )
            )
            is not None
        )
    response = await client.post(
        "/api/game/players",
        json={"name": "Invalid owner", "account_id": student_id + 999999},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "PLAYER_ACCOUNT_NOT_FOUND"
    response = await client.post(
        "/api/game/players",
        json={"name": "Inactive owner", "account_id": account_ids["disabled"]},
    )
    assert response.status_code == 404
    response = await client.post(
        "/api/game/players",
        json={"name": "First player", "account_id": student_id},
    )
    assert response.status_code == 409
    assert response.json()["error"] == "PLAYER_NAME_TAKEN"
    with database.session() as session:
        assert len(list(session.scalars(select(Player)))) == 1
        assert len(list(session.scalars(select(Season)))) == 1
    csrf = client.headers.pop("X-CSRF-Token")
    assert (
        await client.post("/api/game/players", json={"name": "Without CSRF"})
    ).status_code == 403
    client.headers["X-CSRF-Token"] = csrf
    response = await client.post("/api/game/players", json={"name": "Manager profile"})
    assert response.status_code == 200
    manager_player = response.json()
    assert manager_player["account_id"] == account_ids["creator"]
    login = await client.post(
        "/api/auth/login",
        json={"username": "learner", "password": "synthetic-first-game"},
    )
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    assert [item["id"] for item in (await client.get("/api/game/players")).json()] == [
        player["id"]
    ]
    assert (
        await client.post(
            "/api/game/players", json={"name": "Not allowed", "account_id": student_id}
        )
    ).status_code == 403
    assert (
        await client.post(
            "/api/game/rounds",
            json={
                "player_id": manager_player["id"],
                "difficulty": "easy",
                "note_count": 1,
            },
        )
    ).status_code == 404
    response = await client.post(
        "/api/game/rounds",
        json={"player_id": player["id"], "difficulty": "easy", "note_count": 1},
    )
    assert response.status_code == 200
    assert response.json()["task"]["index"] == 0
