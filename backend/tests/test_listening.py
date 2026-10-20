from typing import TypedDict, cast
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from test_auth import anyio_backend, client, create_user, database, login
from test_exercises import auth_settings, create_exercise, opus, png, settings

from app.database import Database
from app.models import ListeningRun, ListeningSession, StudentProgress

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


class MediaPayload(TypedDict):
    id: str


class ExercisePayload(TypedDict):
    id: int
    image: MediaPayload | None
    audio: MediaPayload | None


class RunItemPayload(TypedDict):
    position: int
    exercise: ExercisePayload


class RunPayload(TypedDict):
    id: int
    status: str
    current_index: int
    items: list[RunItemPayload]


async def audio_exercise(
    client: httpx.AsyncClient,
    opus: bytes,
    title: str = "Audio",
    chapter_id: int | None = None,
) -> int:
    data = {"title": title}
    if chapter_id is not None:
        data["chapter_id"] = str(chapter_id)
    response = await client.post(
        "/api/exercises", data=data, files={"audio": ("audio.opus", opus)}
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def start_run(client: httpx.AsyncClient, chapter_id: int) -> RunPayload:
    response = await client.post(
        "/api/listening/run", json={"chapter_ids": [chapter_id]}
    )
    assert response.status_code == 200, response.text
    return cast(RunPayload, response.json())


def current_exercise(run: RunPayload) -> ExercisePayload:
    item = next(
        item for item in run["items"] if item["position"] == run["current_index"]
    )
    return item["exercise"]


async def event(
    client: httpx.AsyncClient,
    run_id: int,
    exercise: int,
    session: str,
    kind: str = "start",
    position: float = 0,
) -> httpx.Response:
    return await client.post(
        "/api/listening/events",
        json={
            "run_id": run_id,
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
    chapter = (await client.post("/api/chapters")).json()
    exercise = await audio_exercise(client, opus, chapter_id=chapter["id"])
    student = await create_user(client)
    await login(client, "student")
    run = await start_run(client, chapter["id"])
    session = str(uuid4())
    assert (await event(client, run["id"], exercise, session)).status_code == 200
    with database.session() as db:
        row = db.scalar(select(ListeningSession))
        assert row is not None and row.user_id == student and row.ended_at is None
        assert row.chapter_number == chapter["number"]
        duration = row.audio_duration_sec
    below = await event(
        client, run["id"], exercise, session, "heartbeat", duration * 0.899
    )
    assert below.json()["completed"] is False
    complete = await event(
        client, run["id"], exercise, session, "heartbeat", duration * 0.9
    )
    assert complete.json()["completed"] is True
    ended = await event(client, run["id"], exercise, session, "end", duration * 0.2)
    timestamp = ended.json()["ended_at"]
    assert timestamp and ended.json()["completed"]
    repeated = await event(client, run["id"], exercise, session, "start")
    assert repeated.json()["ended_at"] == timestamp and repeated.json()["completed"]
    await login(client)
    journal = (await client.get("/api/journal")).json()
    assert journal["total"] == 1
    assert journal["sessions"][0]["max_position_sec"] == duration * 0.9


async def test_event_completion_does_not_advance_legacy_student_pointer(
    client: httpx.AsyncClient,
    opus: bytes,
    database: Database,
) -> None:
    await login(client)
    first = await audio_exercise(client, opus, "First audio")
    second = await audio_exercise(client, opus, "Second audio")
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    student_id = await create_user(client)
    await login(client, "student")
    run = await start_run(client, chapter_id)
    current_id = current_exercise(run)["id"]
    other_id = second if current_id == first else first
    with database.session() as session:
        session.add(
            StudentProgress(
                user_id=student_id,
                next_exercise_id=other_id,
                last_random_id=other_id,
            )
        )
        session.commit()

    response = await event(client, run["id"], current_id, str(uuid4()), "ended")
    assert response.status_code == 200
    await login(client)
    with database.session() as session:
        progress = session.get(StudentProgress, student_id)
        assert progress is not None
        assert progress.next_exercise_id == other_id
        assert progress.last_random_id == other_id


async def test_end_before_start_and_ended_override(
    client: httpx.AsyncClient, opus: bytes
) -> None:
    await login(client)
    exercise = await audio_exercise(client, opus)
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    await create_user(client)
    await login(client, "student")
    run = await start_run(client, chapter_id)
    identifier = str(uuid4())
    response = await event(client, run["id"], exercise, identifier, "ended", 0)
    assert response.status_code == 200 and response.json()["completed"]
    response = await event(client, run["id"], exercise, identifier, "start")
    assert response.json()["completed"] and response.json()["ended_at"]


async def test_deleted_exercise_and_replaced_audio_preserve_journal(
    client: httpx.AsyncClient,
    opus: bytes,
    png: bytes,
) -> None:
    await login(client)
    exercise = await audio_exercise(client, opus, "Original title")
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    await create_user(client)
    await login(client, "student")
    run = await start_run(client, chapter_id)
    session = str(uuid4())
    assert (await event(client, run["id"], exercise, session)).status_code == 200
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
    response = await event(client, run["id"], exercise, session, "end", 0.5)
    assert response.status_code == 200
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
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    await create_user(client)
    await login(client, "student")
    run = await start_run(client, chapter_id)
    current = current_exercise(run)
    assert current["audio"] is not None
    audio_id = current["audio"]["id"]
    path = f"/api/exercises/{exercise}/files/audio?version={audio_id}"
    assert (await client.get(path)).status_code == 200
    identifier = str(uuid4())
    assert (await event(client, run["id"], exercise, identifier)).status_code == 200
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
            "run_id": run["id"],
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
    assert (
        await event(client, run["id"], exercise, identifier, "end", 0.5)
    ).status_code == 200


async def test_student_chapter_and_run_routes_roles_csrf_and_removed_paths(
    client: httpx.AsyncClient,
    png: bytes,
) -> None:
    for path in ("/api/listening/chapters", "/api/listening/run"):
        assert (await client.get(path)).status_code == 401
    for path, body in (
        ("/api/listening/run", {"chapter_ids": [1]}),
        ("/api/listening/run/1/navigate", {"direction": "next"}),
        ("/api/listening/run/1/cancel", {}),
    ):
        assert (await client.post(path, json=body)).status_code == 401

    await login(client)
    exercise = await create_exercise(client, png)
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    student_id = await create_user(client)
    player_id = await create_user(client, "player-user", "player")
    for path in ("/api/listening/chapters", "/api/listening/run"):
        assert (await client.get(path)).status_code == 403
    assert (
        await client.post("/api/listening/run", json={"chapter_ids": [chapter_id]})
    ).status_code == 403

    await login(client, "player-user")
    for path in ("/api/listening/chapters", "/api/listening/run"):
        assert (await client.get(path)).status_code == 403
    for path, body in (
        ("/api/listening/run", {"chapter_ids": [chapter_id]}),
        ("/api/listening/run/1/navigate", {"direction": "next"}),
        ("/api/listening/run/1/cancel", {}),
    ):
        assert (await client.post(path, json=body)).status_code == 403

    await login(client, "student")
    chapters = await client.get("/api/listening/chapters")
    assert chapters.status_code == 200
    assert chapters.json()["chapters"][0]["id"] == chapter_id
    assert (await client.get("/api/listening/run")).json() is None
    for path, body in (
        ("/api/listening/run", {"chapter_ids": [chapter_id]}),
        ("/api/listening/run/1/navigate", {"direction": "next"}),
        ("/api/listening/run/1/cancel", {}),
    ):
        response = await client.post(path, json=body, headers={"X-CSRF-Token": "wrong"})
        assert response.status_code == 403

    run = await start_run(client, chapter_id)
    assert current_exercise(run)["id"] == exercise
    assert (await client.get("/api/listening/current")).status_code == 404
    assert (
        await client.post("/api/listening/select", json={"direction": "next"})
    ).status_code == 404
    assert student_id > 0 and player_id > 0


async def test_navigation_path_run_and_event_bind_to_current_run_and_user(
    client: httpx.AsyncClient,
    opus: bytes,
) -> None:
    await login(client)
    exercise = await audio_exercise(client, opus)
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    first_student_id = await create_user(client, "first-student")
    second_student_id = await create_user(client, "second-student")

    await login(client, "first-student")
    first_run = await start_run(client, chapter_id)
    exercise_id = current_exercise(first_run)["id"]
    event_body = {
        "exercise_id": exercise_id,
        "session_id": str(uuid4()),
        "event": "start",
        "position_seconds": 0,
        "csrf_token": client.headers["X-CSRF-Token"],
    }
    assert (
        await client.post("/api/listening/events", json=event_body)
    ).status_code == 422
    event_body["run_id"] = first_run["id"]
    event_body["mode"] = "sequential"
    assert (
        await client.post("/api/listening/events", json=event_body)
    ).status_code == 422
    session_id = str(uuid4())
    assert (
        await event(client, first_run["id"], exercise_id, session_id)
    ).status_code == 200

    await login(client, "second-student")
    second_run = await start_run(client, chapter_id)
    foreign_event = await event(client, first_run["id"], exercise_id, str(uuid4()))
    assert foreign_event.status_code == 403
    for path, body in (
        (
            f"/api/listening/run/{first_run['id']}/navigate",
            {"direction": "next"},
        ),
        (f"/api/listening/run/{first_run['id']}/cancel", {}),
    ):
        foreign_mutation = await client.post(
            path,
            json=body,
            headers={"X-CSRF-Token": client.headers["X-CSRF-Token"]},
        )
        assert foreign_mutation.status_code == 403
    assert (await client.get("/api/listening/run")).json()["id"] == second_run["id"]
    assert (
        await event(client, second_run["id"], exercise_id, session_id)
    ).status_code == 403

    await login(client, "first-student")
    bad_current = await event(client, first_run["id"], exercise + 100000, str(uuid4()))
    assert bad_current.status_code == 409

    await login(client)
    assert first_student_id != second_student_id


async def test_event_origin_csrf_image_only_and_session_concurrency(
    client: httpx.AsyncClient,
    opus: bytes,
    png: bytes,
    database: Database,
) -> None:
    import asyncio

    await login(client)
    image = await create_exercise(client, png)
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    student = await create_user(client)
    await login(client, "student")
    image_run = await start_run(client, chapter_id)
    image_item = current_exercise(image_run)
    assert image_item["id"] == image
    assert image_item["image"] and image_item["audio"] is None
    image_event = await event(client, image_run["id"], image, str(uuid4()))
    assert image_event.status_code == 422
    await login(client)
    assert (await client.get("/api/journal")).json()["total"] == 0
    chapter_two = (await client.post("/api/chapters")).json()
    audio = await audio_exercise(client, opus, chapter_id=chapter_two["id"])
    await login(client, "student")
    cancelled = await client.post(
        f"/api/listening/run/{image_run['id']}/cancel",
        headers={"X-CSRF-Token": client.headers["X-CSRF-Token"]},
    )
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    run = await start_run(client, chapter_two["id"])
    assert current_exercise(run)["id"] == audio
    identifier = str(uuid4())
    origin_failure = await client.post(
        "/api/listening/events",
        json={
            "run_id": run["id"],
            "exercise_id": audio,
            "session_id": str(uuid4()),
            "event": "start",
            "position_seconds": 0,
            "csrf_token": client.headers["X-CSRF-Token"],
        },
        headers={"Origin": "https://untrusted.invalid"},
    )
    assert origin_failure.status_code == 403

    body = {
        "run_id": run["id"],
        "exercise_id": audio,
        "session_id": identifier,
        "event": "start",
        "position_seconds": 0,
        "csrf_token": "wrong",
    }
    assert (await client.post("/api/listening/events", json=body)).status_code == 403
    body["csrf_token"] = client.headers["X-CSRF-Token"]
    csrf_header = client.headers.pop("X-CSRF-Token")
    assert (await client.post("/api/listening/events", json=body)).status_code == 200
    client.headers["X-CSRF-Token"] = csrf_header

    results = await asyncio.gather(
        event(client, run["id"], audio, identifier, "start"),
        event(client, run["id"], audio, identifier, "heartbeat", 1),
        event(client, run["id"], audio, identifier, "end", 0.5),
    )
    assert all(result.status_code == 200 for result in results)
    await login(client)
    journal = (await client.get("/api/journal")).json()
    assert journal["total"] == 1
    assert journal["sessions"][0]["user_id"] == student
    assert journal["sessions"][0]["max_position_sec"] == 1
    assert journal["sessions"][0]["ended_at"]


async def test_run_mutations_validate_stale_chapter_empty_and_soft_deleted_exercises(
    client: httpx.AsyncClient,
    database: Database,
    png: bytes,
) -> None:
    await login(client)
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    active_id = await create_exercise(client, png)
    deleted_id = await create_exercise(client, png)
    await client.delete(f"/api/exercises/{deleted_id}")
    await create_user(client)
    await login(client, "student")

    stale = await client.post("/api/listening/run", json={"chapter_ids": [987654321]})
    assert stale.status_code == 404 and stale.json()["error"] == "CHAPTER_NOT_FOUND"
    empty_selection = await client.post("/api/listening/run", json={"chapter_ids": []})
    assert empty_selection.status_code == 422
    run = await start_run(client, chapter_id)
    assert [item["exercise"]["id"] for item in run["items"]] == [active_id]

    cancelled = await client.post(
        f"/api/listening/run/{run['id']}/cancel",
        headers={"X-CSRF-Token": client.headers["X-CSRF-Token"]},
    )
    assert cancelled.status_code == 200
    await login(client)
    empty_chapter = (await client.post("/api/chapters")).json()
    await login(client, "student")
    listed_ids = {
        row["id"]
        for row in (await client.get("/api/listening/chapters")).json()["chapters"]
    }
    assert empty_chapter["id"] not in listed_ids
    unavailable = await client.post(
        "/api/listening/run", json={"chapter_ids": [empty_chapter["id"]]}
    )
    assert unavailable.status_code == 409
    assert unavailable.json()["error"] == "CHAPTER_UNAVAILABLE"


async def test_deleted_queue_items_are_hidden_and_all_deleted_queue_completes(
    client: httpx.AsyncClient,
    database: Database,
    png: bytes,
) -> None:
    await login(client)
    first = await create_exercise(client, png, "First score")
    second = await create_exercise(client, png, "Second score")
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    await create_user(client)
    await login(client, "student")
    run = await start_run(client, chapter_id)
    current = current_exercise(run)
    deleted_id = current["id"]
    assert current["image"] is not None
    deleted_file_id = current["image"]["id"]

    await login(client)
    assert (await client.delete(f"/api/exercises/{deleted_id}")).status_code == 200
    await login(client, "student")
    resumed = (await client.get("/api/listening/run")).json()
    assert resumed["current_index"] != run["current_index"]
    assert [item["exercise"]["id"] for item in resumed["items"]] == [
        second if deleted_id == first else first
    ]
    assert (
        await client.get(
            f"/api/exercises/{deleted_id}/files/image?version={deleted_file_id}"
        )
    ).status_code == 404

    remaining_id = resumed["items"][0]["exercise"]["id"]
    await login(client)
    assert (await client.delete(f"/api/exercises/{remaining_id}")).status_code == 200
    await login(client, "student")
    assert (await client.get("/api/listening/run")).json() is None
    with database.session() as session:
        completed = session.scalar(
            select(ListeningRun).where(ListeningRun.id == run["id"])
        )
        assert completed is not None and completed.status == "completed"


async def test_concurrent_run_starts_create_one_saved_run(
    client: httpx.AsyncClient,
    database: Database,
    png: bytes,
) -> None:
    import asyncio

    await login(client)
    await create_exercise(client, png)
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    student_id = await create_user(client)
    await login(client, "student")
    responses = await asyncio.gather(
        client.post("/api/listening/run", json={"chapter_ids": [chapter_id]}),
        client.post("/api/listening/run", json={"chapter_ids": [chapter_id]}),
    )
    assert all(response.status_code == 200 for response in responses)
    assert responses[0].json()["id"] == responses[1].json()["id"]
    with database.session() as session:
        runs = list(
            session.scalars(
                select(ListeningRun).where(
                    ListeningRun.user_id == student_id,
                    ListeningRun.status == "active",
                )
            )
        )
        assert len(runs) == 1
