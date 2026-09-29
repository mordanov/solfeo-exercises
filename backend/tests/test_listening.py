from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from test_auth import anyio_backend, client, create_user, database, login
from test_exercises import auth_settings, create_exercise, opus, png, settings

from app.database import Database
from app.models import ListeningSession

__all__ = [
    "anyio_backend",
    "client",
    "database",
    "settings",
    "auth_settings",
    "png",
    "opus",
]
pytestmark = pytest.mark.anyio


async def audio_exercise(
    client: httpx.AsyncClient, opus: bytes, title: str = "Audio"
) -> int:
    response = await client.post(
        "/api/exercises", data={"title": title}, files={"audio": ("audio.opus", opus)}
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def event(
    client: httpx.AsyncClient,
    exercise: int,
    session: str,
    kind: str = "start",
    position: float = 0,
) -> httpx.Response:
    return await client.post(
        "/api/listening/events",
        json={
            "exercise_id": exercise,
            "session_id": session,
            "event": kind,
            "position_seconds": position,
            "csrf_token": client.headers["X-CSRF-Token"],
        },
    )


async def test_closed_tab_threshold_and_idempotent_terminal_events(
    client: httpx.AsyncClient,
    opus: bytes,
    database: Database,
) -> None:
    await login(client)
    exercise = await audio_exercise(client, opus)
    student = await create_user(client)
    await login(client, "student")
    session = str(uuid4())
    assert (await event(client, exercise, session)).status_code == 200
    with database.session() as db:
        row = db.scalar(select(ListeningSession))
        assert row is not None and row.user_id == student and row.ended_at is None
        duration = row.audio_duration_sec
    below = await event(client, exercise, session, "heartbeat", duration * 0.899)
    assert below.json()["completed"] is False
    complete = await event(client, exercise, session, "heartbeat", duration * 0.9)
    assert complete.json()["completed"] is True
    ended = await event(client, exercise, session, "end", duration * 0.2)
    timestamp = ended.json()["ended_at"]
    assert timestamp and ended.json()["completed"]
    repeated = await event(client, exercise, session, "start")
    assert repeated.json()["ended_at"] == timestamp and repeated.json()["completed"]
    await login(client)
    journal = (await client.get("/api/journal")).json()
    assert journal["total"] == 1
    assert journal["sessions"][0]["max_position_sec"] == duration * 0.9


async def test_end_before_start_and_ended_override(
    client: httpx.AsyncClient, opus: bytes
) -> None:
    await login(client)
    exercise = await audio_exercise(client, opus)
    await create_user(client)
    await login(client, "student")
    identifier = str(uuid4())
    response = await event(client, exercise, identifier, "ended", 0)
    assert response.status_code == 200 and response.json()["completed"]
    response = await event(client, exercise, identifier, "start")
    assert response.json()["completed"] and response.json()["ended_at"]


async def test_deleted_exercise_and_replaced_audio_preserve_journal(
    client: httpx.AsyncClient,
    opus: bytes,
    png: bytes,
) -> None:
    await login(client)
    exercise = await audio_exercise(client, opus, "Original title")
    await create_user(client)
    await login(client, "student")
    identifier = str(uuid4())
    assert (await event(client, exercise, identifier)).status_code == 200
    await login(client)
    assert (
        await client.put(
            f"/api/exercises/{exercise}",
            data={
                "title": "Changed title",
                "remove_audio": "true",
            },
            files={"image": ("score.png", png)},
        )
    ).status_code == 200
    await client.delete(f"/api/exercises/{exercise}")
    await login(client, "student")
    response = await event(client, exercise, identifier, "end", 0.5)
    assert response.status_code == 200
    assert (await event(client, exercise, str(uuid4()))).status_code == 404
    await login(client)
    row = (await client.get("/api/journal")).json()["sessions"][0]
    assert row["exercise_title"] == "Original title" and row["exercise_deleted"]
    assert row["audio_duration_sec"] > 1
    options = (await client.get("/api/journal/options")).json()
    assert options["exercises"][0]["id"] == exercise


async def test_audio_version_rejects_replacement_without_losing_existing_session(
    client: httpx.AsyncClient, opus: bytes
) -> None:
    await login(client)
    exercise = await audio_exercise(client, opus)
    await create_user(client)
    await login(client, "student")
    current = (await client.get("/api/listening/current")).json()["exercise"]
    audio_id = current["audio"]["id"]
    path = f"/api/exercises/{exercise}/files/audio?version={audio_id}"
    assert (await client.get(path)).status_code == 200
    identifier = str(uuid4())
    assert (await event(client, exercise, identifier)).status_code == 200
    await login(client)
    replacement = await client.put(
        f"/api/exercises/{exercise}",
        data={"title": "Replacement"},
        files={"audio": ("replacement.opus", opus)},
    )
    assert replacement.status_code == 200
    replacement_id = replacement.json()["audio"]["id"]
    assert replacement_id != audio_id
    await login(client, "student")
    assert (await client.get(path)).status_code == 404
    assert (
        await client.get(
            f"/api/exercises/{exercise}/files/audio?version={replacement_id}"
        )
    ).status_code == 200
    stale = await client.post(
        "/api/listening/events",
        json={
            "exercise_id": exercise,
            "audio_id": audio_id,
            "session_id": str(uuid4()),
            "event": "start",
            "position_seconds": 0,
            "csrf_token": client.headers["X-CSRF-Token"],
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"] == "AUDIO_CHANGED"
    assert (await event(client, exercise, identifier, "end", 0.5)).status_code == 200


async def test_navigation_persistence_random_and_deleted_pointer(
    client: httpx.AsyncClient,
    png: bytes,
    opus: bytes,
) -> None:
    await login(client)
    first = await audio_exercise(client, opus, "First")
    second = await create_exercise(client, png, "Second")
    await create_user(client)
    await login(client, "student")
    assert (await client.get("/api/listening/current")).json()["exercise"][
        "id"
    ] == first
    response = await client.post(
        "/api/listening/select",
        json={
            "mode": "sequential",
            "direction": "next",
            "current_id": first,
        },
    )
    assert response.json()["exercise"]["id"] == second
    assert (await client.get("/api/listening/current")).json()["exercise"][
        "id"
    ] == second
    response = await client.post(
        "/api/listening/select",
        json={
            "mode": "random",
            "direction": "next",
            "current_id": second,
        },
    )
    assert response.json()["exercise"]["id"] == first
    await event(client, first, str(uuid4()), "ended", 0)
    assert (await client.get("/api/listening/current")).json()["exercise"][
        "id"
    ] == second
    await login(client)
    await client.delete(f"/api/exercises/{second}")
    await login(client, "student")
    assert (await client.get("/api/listening/current")).json()["exercise"][
        "id"
    ] == first
    for _ in range(2):
        response = await client.post(
            "/api/listening/select",
            json={
                "mode": "random",
                "direction": "next",
                "current_id": first,
            },
        )
        assert response.json()["exercise"]["id"] == first


async def test_journal_permissions_csrf_filters_and_validation(
    client: httpx.AsyncClient,
    opus: bytes,
) -> None:
    for path in ("/api/listening/current", "/api/journal", "/api/journal/options"):
        assert (await client.get(path)).status_code == 401
    await login(client)
    first = await audio_exercise(client, opus)
    student = await create_user(client)
    assert (await client.get("/api/listening/current")).status_code == 403
    await login(client, "student")
    for path in ("/api/journal", "/api/journal/options"):
        assert (await client.get(path)).status_code == 403
    body = {
        "exercise_id": first,
        "session_id": str(uuid4()),
        "event": "start",
        "position_seconds": 0,
        "csrf_token": "wrong",
    }
    assert (await client.post("/api/listening/events", json=body)).status_code == 403
    body["csrf_token"] = client.headers["X-CSRF-Token"]
    headers = client.headers.pop("X-CSRF-Token")
    assert (await client.post("/api/listening/events", json=body)).status_code == 200
    client.headers["X-CSRF-Token"] = headers
    assert (await event(client, first, str(uuid4()), position=-1)).status_code == 422
    await login(client)
    filtered = await client.get(
        f"/api/journal?student_id={student}&exercise_id={first}&limit=1"
    )
    assert filtered.json()["total"] == 1
    assert (await client.get("/api/journal?offset=1&limit=1")).json()["sessions"] == []
    assert (await client.get("/api/journal?started_from=2099-01-01T00:00:00Z")).json()[
        "total"
    ] == 0
    assert (await client.get("/api/journal?started_from=2026-01-01")).status_code == 422


async def test_concurrent_delivery_creates_one_row_and_preserves_maximum(
    client: httpx.AsyncClient,
    opus: bytes,
) -> None:
    import asyncio

    await login(client)
    exercise = await audio_exercise(client, opus)
    await create_user(client)
    await login(client, "student")
    identifier = str(uuid4())
    results = await asyncio.gather(
        event(client, exercise, identifier, "start"),
        event(client, exercise, identifier, "heartbeat", 1),
        event(client, exercise, identifier, "end", 0.5),
    )
    assert all(result.status_code == 200 for result in results)
    await login(client)
    data = (await client.get("/api/journal")).json()
    assert data["total"] == 1
    assert data["sessions"][0]["max_position_sec"] == 1
    assert data["sessions"][0]["ended_at"]


async def test_session_ownership_conflicts_and_image_only(
    client: httpx.AsyncClient,
    opus: bytes,
    png: bytes,
) -> None:
    await login(client)
    first = await audio_exercise(client, opus)
    second = await audio_exercise(client, opus)
    image = await create_exercise(client, png)
    await create_user(client)
    await create_user(client, "other-student")
    await login(client, "student")
    identifier = str(uuid4())
    await event(client, first, identifier)
    assert (await event(client, second, identifier)).status_code == 409
    assert (await event(client, image, str(uuid4()))).status_code == 422
    response = await client.post(
        "/api/listening/events",
        json={
            "exercise_id": first,
            "session_id": str(uuid4()),
            "event": "start",
            "position_seconds": 0,
            "csrf_token": client.headers["X-CSRF-Token"],
        },
        headers={"Origin": "https://untrusted.invalid"},
    )
    assert response.status_code == 403
    await login(client, "other-student")
    assert (await event(client, first, identifier, "ended", 2)).status_code == 403


async def test_empty_navigation_and_completion_does_not_skip_twice(
    client: httpx.AsyncClient,
    opus: bytes,
) -> None:
    await login(client)
    await create_user(client)
    await login(client, "student")
    assert (await client.get("/api/listening/current")).json() == {"exercise": None}
    assert (
        await client.post("/api/listening/select", json={"direction": "next"})
    ).json() == {"exercise": None}
    await login(client)
    first = await audio_exercise(client, opus)
    second = await audio_exercise(client, opus)
    await login(client, "student")
    identifier = str(uuid4())
    await event(client, first, identifier, "ended")
    await event(client, first, identifier, "ended")
    assert (await client.get("/api/listening/current")).json()["exercise"][
        "id"
    ] == second
    response = await client.post(
        "/api/listening/select", json={"direction": "next", "current_id": first}
    )
    assert response.json()["exercise"]["id"] == second
    response = await client.post(
        "/api/listening/select", json={"direction": "previous", "current_id": second}
    )
    assert response.json()["exercise"]["id"] == first


async def test_completion_recovers_deleted_saved_pointer(
    client: httpx.AsyncClient,
    opus: bytes,
) -> None:
    await login(client)
    first = await audio_exercise(client, opus)
    second = await audio_exercise(client, opus)
    third = await audio_exercise(client, opus)
    await create_user(client)
    await login(client, "student")
    await client.post(
        "/api/listening/select", json={"direction": "current", "current_id": third}
    )
    await login(client)
    await client.delete(f"/api/exercises/{third}")
    await login(client, "student")
    assert (await client.get("/api/listening/current")).json()["exercise"][
        "id"
    ] == first
    await event(client, first, str(uuid4()), "ended")
    assert (await client.get("/api/listening/current")).json()["exercise"][
        "id"
    ] == second
