import asyncio

import httpx
import pytest
from sqlalchemy import select

from app.database import Database
from app.game.models import Player, Season
from app.models import User
from app.services.auth import create_user
from app.settings import Settings


@pytest.mark.anyio
async def test_manager_assigns_first_profile_and_student_can_start(
    client: httpx.AsyncClient, database: Database, settings: Settings
) -> None:
    assert (await client.get("/api/game/players/accounts")).status_code == 401
    account_ids: dict[str, int] = {}
    with database.session() as session:
        for username, role in (
            ("creator", "manager"),
            ("learner", "student"),
            ("disabled", "student"),
            ("recovery", "manager"),
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
        disabled = session.get(User, account_ids["disabled"])
        recovery = session.get(User, account_ids["recovery"])
        assert disabled is not None and recovery is not None
        disabled.is_active = False
        recovery.is_emergency = True
        session.commit()
    student_id = account_ids["learner"]
    login = await client.post(
        "/api/auth/login",
        json={"username": "creator", "password": "synthetic-first-game"},
    )
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    assert (await client.get("/api/game/players")).json() == []
    eligible = await client.get("/api/game/players/accounts")
    assert eligible.status_code == 200
    assert {u["id"] for u in eligible.json()["users"]} == {
        account_ids["creator"],
        student_id,
    }
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
    response = await client.post(
        "/api/game/players",
        json={"name": "Another profile", "account_id": student_id},
    )
    assert response.status_code == 409
    assert response.json()["error"] == "PLAYER_ACCOUNT_TAKEN"
    response = await client.post(
        "/api/game/players",
        json={"name": "Recovery profile", "account_id": account_ids["recovery"]},
    )
    assert response.status_code == 422
    assert response.json()["error"] == "PLAYER_EMERGENCY_ACCOUNT"
    eligible = await client.get("/api/game/players/accounts")
    assert [u["id"] for u in eligible.json()["users"]] == [account_ids["creator"]]
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
    assert (await client.get("/api/game/players/accounts")).status_code == 403
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


@pytest.mark.anyio
async def test_concurrent_creation_permits_only_one_profile_per_account(
    client: httpx.AsyncClient, database: Database, settings: Settings
) -> None:
    with database.session() as session:
        manager = create_user(
            session,
            settings,
            username="concurrent-manager",
            password="synthetic-game-piano",
            first_name="Manager",
            last_name="Test",
            role="manager",
            must_change_password=False,
        )
        student = create_user(
            session,
            settings,
            username="concurrent-student",
            password="synthetic-game-piano",
            first_name="Student",
            last_name="Test",
            role="student",
            must_change_password=False,
        )
        student_id = student.id
        assert manager.id != student_id
    login = await client.post(
        "/api/auth/login",
        json={
            "username": "concurrent-manager",
            "password": "synthetic-game-piano",
        },
    )
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    responses = await asyncio.gather(
        *(
            client.post(
                "/api/game/players", json={"name": name, "account_id": student_id}
            )
            for name in ("First", "Second")
        )
    )
    assert sorted(response.status_code for response in responses) == [200, 409]
    with database.session() as session:
        assert len(list(session.scalars(select(Player)))) == 1
        assert len(list(session.scalars(select(Season)))) == 1
