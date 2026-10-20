from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select, update
from test_auth import anyio_backend, client, create_user, database, login
from test_exercises import auth_settings, create_exercise, opus, png, settings

from app.database import Database
from app.models import Exercise, ListeningRun, ListeningRunItem
from app.services import listening_runs
from app.services.auth import ServiceError

pytestmark = pytest.mark.anyio
__all__ = [
    "anyio_backend",
    "client",
    "database",
    "settings",
    "auth_settings",
    "png",
    "opus",
]


async def test_run_contains_each_active_exercise_and_resumes_saved_order(
    client: httpx.AsyncClient,
    database: Database,
    png: bytes,
) -> None:
    await login(client)
    first_chapter = (await client.get("/api/chapters")).json()["chapters"][0]
    second_chapter_response = await client.post("/api/chapters")
    assert second_chapter_response.status_code == 201
    second_chapter = second_chapter_response.json()
    first_exercise = await create_exercise(client, png, "Chapter one")
    second_exercise = await client.post(
        "/api/exercises",
        data={
            "title": "Chapter two",
            "chapter_id": str(second_chapter["id"]),
        },
        files={"image": ("score.png", png, "image/png")},
    )
    assert second_exercise.status_code == 201, second_exercise.text
    student_id = await create_user(client)

    with database.session() as session:
        run = listening_runs.start_run(
            session, student_id, [first_chapter["id"], second_chapter["id"]]
        )
        run_id = run.id
        items = list(
            session.scalars(
                select(ListeningRunItem)
                .where(ListeningRunItem.run_id == run.id)
                .order_by(ListeningRunItem.position)
            )
        )
        saved_order = [(item.exercise_id, item.chapter_number) for item in items]
        assert run.status == "active"
        assert run.current_index == 0
        assert set(saved_order) == {
            (first_exercise, first_chapter["number"]),
            (second_exercise.json()["id"], second_chapter["number"]),
        }

    with database.session() as session:
        resumed = listening_runs.start_run(session, student_id, [second_chapter["id"]])
        assert resumed.id == run_id
        assert [
            (item.exercise_id, item.chapter_number)
            for item in session.scalars(
                select(ListeningRunItem)
                .where(ListeningRunItem.run_id == run_id)
                .order_by(ListeningRunItem.position)
            )
        ] == saved_order


async def test_run_samples_ten_distinct_active_exercises(
    client: httpx.AsyncClient,
    database: Database,
    png: bytes,
) -> None:
    await login(client)
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    exercises = {
        await create_exercise(client, png, f"Exercise {index}") for index in range(12)
    }
    student_id = await create_user(client)

    with database.session() as session:
        run = listening_runs.start_run(session, student_id, [chapter_id])
        items = list(
            session.scalars(
                select(ListeningRunItem).where(ListeningRunItem.run_id == run.id)
            )
        )

    assert len(items) == 10
    assert len({item.exercise_id for item in items}) == 10
    assert {item.exercise_id for item in items} <= exercises


async def test_run_rejects_missing_and_unavailable_chapters(
    client: httpx.AsyncClient,
    database: Database,
) -> None:
    await login(client)
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    student_id = await create_user(client)

    with database.session() as session:
        with pytest.raises(ServiceError) as missing:
            listening_runs.start_run(session, student_id, [987654321])
        assert (missing.value.code, missing.value.status) == ("CHAPTER_NOT_FOUND", 404)

        with pytest.raises(ServiceError) as unavailable:
            listening_runs.start_run(session, student_id, [chapter_id])
        assert (unavailable.value.code, unavailable.value.status) == (
            "CHAPTER_UNAVAILABLE",
            409,
        )

        with pytest.raises(ServiceError) as empty:
            listening_runs.start_run(session, student_id, [])
        assert (empty.value.code, empty.value.status) == ("VALIDATION_ERROR", 422)

        with pytest.raises(ServiceError) as duplicate:
            listening_runs.start_run(session, student_id, [chapter_id, chapter_id])
        assert (duplicate.value.code, duplicate.value.status) == (
            "DUPLICATE_CHAPTER_ID",
            422,
        )


async def test_navigation_completes_and_cancellation_only_affects_requested_run(
    client: httpx.AsyncClient,
    database: Database,
    png: bytes,
) -> None:
    await login(client)
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    await create_exercise(client, png, "Image")
    await create_exercise(client, png, "Another image")
    student_id = await create_user(client)

    with database.session() as session:
        run = listening_runs.start_run(session, student_id, [chapter_id])
        run_id = run.id
        first_index = run.current_index

        previous = listening_runs.move_run(session, student_id, run_id, "previous")
        assert previous.current_index == first_index

        next_item = listening_runs.move_run(session, student_id, run_id, "next")
        assert next_item.current_index == first_index + 1

        completed = listening_runs.move_run(session, student_id, run_id, "next")
        assert completed.status == "completed"

        replacement = listening_runs.start_run(session, student_id, [chapter_id])
        assert replacement.id != run_id
        with pytest.raises(ServiceError) as stale_navigation:
            listening_runs.move_run(session, student_id, run_id, "next")
        assert stale_navigation.value.code == "LISTENING_RUN_NOT_ACTIVE"
        assert replacement.status == "active"
        assert replacement.current_index == 0

        cancelled = listening_runs.cancel_run(session, student_id, replacement.id)
        assert cancelled.status == "cancelled"
        with pytest.raises(ServiceError) as stale:
            listening_runs.cancel_run(session, student_id, replacement.id)
        assert stale.value.code == "LISTENING_RUN_NOT_ACTIVE"


async def test_one_active_run_per_student_and_foreign_run_cannot_be_changed(
    client: httpx.AsyncClient,
    database: Database,
    png: bytes,
) -> None:
    await login(client)
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    await create_exercise(client, png, "Image")
    first_student = await create_user(client, "first-student")
    second_student = await create_user(client, "second-student")

    with database.session() as session:
        run = listening_runs.start_run(session, first_student, [chapter_id])
        resumed = listening_runs.start_run(session, first_student, [chapter_id])
        assert resumed.id == run.id
        with pytest.raises(ServiceError) as foreign:
            listening_runs.cancel_run(session, second_student, run.id)
        assert (foreign.value.code, foreign.value.status) == ("FORBIDDEN", 403)
        current_run = session.get(ListeningRun, run.id)
        assert current_run is not None and current_run.status == "active"


async def test_deleted_current_item_is_skipped_and_deleted_queue_completes(
    client: httpx.AsyncClient,
    database: Database,
    png: bytes,
) -> None:
    await login(client)
    chapter_id = (await client.get("/api/chapters")).json()["chapters"][0]["id"]
    await create_exercise(client, png, "First image")
    await create_exercise(client, png, "Second image")
    student_id = await create_user(client)

    with database.session() as session:
        run = listening_runs.start_run(session, student_id, [chapter_id])
        ordered_items = list(
            session.scalars(
                select(ListeningRunItem)
                .where(ListeningRunItem.run_id == run.id)
                .order_by(ListeningRunItem.position)
            )
        )
        first_id = ordered_items[0].exercise_id
        session.execute(
            update(Exercise)
            .where(Exercise.id == first_id)
            .values(deleted_at=datetime.now(UTC))
        )
        session.commit()

        moved = listening_runs.move_run(session, student_id, run.id, "next")
        assert moved.status == "active" and moved.current_index == 1
        resumed = listening_runs.active_run(session, student_id)
        assert resumed is not None and resumed.current_index == 1

        session.execute(
            update(Exercise)
            .where(Exercise.id.in_([item.exercise_id for item in ordered_items]))
            .values(deleted_at=datetime.now(UTC))
        )
        session.commit()

        assert listening_runs.active_run(session, student_id) is None
        completed = session.get(ListeningRun, run.id)
        assert completed is not None and completed.status == "completed"
