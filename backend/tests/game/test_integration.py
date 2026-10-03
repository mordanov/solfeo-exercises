"""Full round: 5 correct + 1 wrong + 1 timeout.

score=3, correct_count=5, is_win=True, xp_gained=10
"""

import httpx
import pytest

from app.database import Database
from app.services.auth import create_user
from app.settings import Settings

pytestmark = pytest.mark.anyio


async def _login(
    client: httpx.AsyncClient, username: str, password: str
) -> dict[str, object]:
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert r.status_code == 200
    return r.json()  # type: ignore[no-any-return]


async def _make_manager(settings: Settings, database: Database) -> tuple[str, str]:
    with database.session() as s:
        with s.begin():
            create_user(
                s,
                settings,
                username="mgr_int",
                password="P@ssw0rd!!",
                first_name="M",
                last_name="I",
                role="manager",
                must_change_password=False,
            )
    return "mgr_int", "P@ssw0rd!!"


async def _make_manager2(settings: Settings, database: Database) -> tuple[str, str]:
    with database.session() as s:
        with s.begin():
            create_user(
                s,
                settings,
                username="mgr_idem",
                password="P@ssw0rd!!",
                first_name="M",
                last_name="J",
                role="manager",
                must_change_password=False,
            )
    return "mgr_idem", "P@ssw0rd!!"


async def test_full_round(
    client: httpx.AsyncClient, settings: Settings, database: Database
) -> None:
    u, p = await _make_manager(settings, database)
    auth = await _login(client, u, p)
    csrf = str(auth["csrf_token"])

    r = await client.post(
        "/api/game/players",
        json={"name": "Hero", "avatar_animal": "unicorn"},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 200
    player_id = r.json()["id"]

    r = await client.post(
        "/api/game/rounds",
        json={"player_id": player_id, "difficulty": "easy", "note_count": 1},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 200
    data = r.json()
    round_id = data["round_id"]
    task = data["task"]
    assert task["index"] == 0

    result = None
    for i in range(7):
        note = task["notes"][0]
        if i < 5:
            answers: list[dict[str, object]] | None = [
                {"name": note["name"], "octave": note["octave"]}
            ]
            timed_out = False
        elif i == 5:
            answers = [{"name": "X", "octave": 0}]
            timed_out = False
        else:
            answers = None
            timed_out = True

        r = await client.post(
            f"/api/game/rounds/{round_id}/submit",
            json={"task_index": i, "answers": answers, "timed_out": timed_out},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 200
        data = r.json()
        task = data.get("next_task") or task
        result = data.get("result")

    assert result is not None
    # 5 correct (+1 each) + 1 wrong (−1) + 1 timeout (−1) = 3
    assert result["score"] == 3
    assert result["correct_count"] == 5
    assert result["is_win"] is True
    assert result["xp_gained"] == 10  # 5 correct × 1 + 5 win bonus


async def test_idempotent_submit(
    client: httpx.AsyncClient, settings: Settings, database: Database
) -> None:
    """Submitting the same task_index twice returns identical response."""
    u, p = await _make_manager2(settings, database)
    auth = await _login(client, u, p)
    csrf = str(auth["csrf_token"])

    r = await client.post(
        "/api/game/players",
        json={"name": "Idem", "avatar_animal": "dragon"},
        headers={"X-CSRF-Token": csrf},
    )
    player_id = r.json()["id"]

    r = await client.post(
        "/api/game/rounds",
        json={"player_id": player_id, "difficulty": "easy", "note_count": 1},
        headers={"X-CSRF-Token": csrf},
    )
    data = r.json()
    round_id = data["round_id"]
    task = data["task"]
    note = task["notes"][0]
    body = {
        "task_index": 0,
        "answers": [{"name": note["name"], "octave": note["octave"]}],
        "timed_out": False,
    }

    r1 = await client.post(
        f"/api/game/rounds/{round_id}/submit",
        json=body,
        headers={"X-CSRF-Token": csrf},
    )
    r2 = await client.post(
        f"/api/game/rounds/{round_id}/submit",
        json=body,
        headers={"X-CSRF-Token": csrf},
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["is_correct"] == r2.json()["is_correct"]
    assert r1.json()["score_delta"] == r2.json()["score_delta"]
