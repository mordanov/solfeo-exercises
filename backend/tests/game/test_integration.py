"""Full round: 5 correct + 1 wrong + 1 timeout.

score=4 (including default assistance bonus), correct_count=5, is_win=True, xp_gained=10
"""

import asyncio

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
    # Task subtotal 3 plus the default one-time assistance bonus.
    assert result["score"] == 4
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


@pytest.mark.parametrize(
    ("sound_hint", "correct_answer", "bonus"),
    [(True, True, 0), (False, True, 1), (True, False, 1), (False, False, 2)],
)
@pytest.mark.parametrize("all_correct", [True, False])
@pytest.mark.parametrize("rules_version", [1, 2])
async def test_round_bonus_is_authoritative_once_and_does_not_change_xp(
    client: httpx.AsyncClient,
    settings: Settings,
    database: Database,
    sound_hint: bool,
    correct_answer: bool,
    bonus: int,
    all_correct: bool,
    rules_version: int,
) -> None:
    from app.game.models import Round

    username, password = await _make_manager(settings, database)
    auth = await _login(client, username, password)
    client.headers["X-CSRF-Token"] = str(auth["csrf_token"])
    player = (await client.post("/api/game/players", json={"name": "Bonus"})).json()
    created = await client.post(
        "/api/game/rounds",
        json={
            "player_id": player["id"],
            "difficulty": "easy",
            "note_count": 2,
            "show_sound_hint": sound_hint,
            "show_correct_answer": correct_answer,
        },
    )
    assert created.status_code == 200
    round_id = created.json()["round_id"]
    with database.session() as session, session.begin():
        stored = session.get(Round, round_id)
        assert stored is not None and stored.rules_version == 2
        stored.rules_version = rules_version
    graded_correct = all_correct and rules_version == 2
    effective_bonus = bonus if rules_version == 2 else 0
    task = created.json()["task"]
    for index in range(7):
        body = {
            "task_index": index,
            "answers": [
                {
                    "name": note["name"] if all_correct else "X",
                    "octave": 5 if note["octave"] != 5 else 4,
                }
                for note in task["notes"]
            ],
            "score_bonus": 999,
            "show_sound_hint": False,
            "show_correct_answer": False,
        }
        if index == 6 and all_correct and not sound_hint and not correct_answer:
            simultaneous = await asyncio.gather(
                client.post(f"/api/game/rounds/{round_id}/submit", json=body),
                client.post(f"/api/game/rounds/{round_id}/submit", json=body),
            )
            assert sorted(item.status_code for item in simultaneous) == [200, 400]
            response = next(item for item in simultaneous if item.status_code == 200)
        else:
            response = await client.post(
                f"/api/game/rounds/{round_id}/submit", json=body
            )
        assert response.status_code == 200
        assert response.json()["is_correct"] is graded_correct
        assert response.json()["score_delta"] == (1 if graded_correct else -1)
        if index == 0:
            repeated = await client.post(
                f"/api/game/rounds/{round_id}/submit", json=body
            )
            assert repeated.json()["score_delta"] == (1 if graded_correct else -1)
        if index < 6:
            task = response.json()["next_task"]
    result = response.json()["result"]
    expected_score = (7 if graded_correct else -7) + effective_bonus
    assert result["score"] == expected_score
    assert result["score_bonus"] == effective_bonus
    assert result["correct_count"] == (7 if graded_correct else 0)
    assert result["is_win"] is graded_correct
    assert result["xp_gained"] == (12 if graded_correct else 0)
    with database.session() as session:
        stored = session.get(Round, round_id)
        assert stored is not None
        assert stored.show_sound_hint is sound_hint
        assert stored.show_correct_answer is correct_answer
        assert stored.rules_version == rules_version
        assert stored.score == expected_score
    repeated = await client.post(
        f"/api/game/rounds/{round_id}/submit", json={"task_index": 6, "timed_out": True}
    )
    assert repeated.status_code == 400
    with database.session() as session:
        stored = session.get(Round, round_id)
        assert stored is not None and stored.score == expected_score
