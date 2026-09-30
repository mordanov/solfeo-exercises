from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select
from test_auth import anyio_backend, client, create_user, database, login
from test_exercises import auth_settings, create_exercise, opus, png, settings

from app.database import Database
from app.models import OmrJob
from app.services import omr
from app.services.auth import ServiceError
from app.settings import Settings

__all__ = [
    "anyio_backend",
    "client",
    "database",
    "auth_settings",
    "settings",
    "png",
    "opus",
]
pytestmark = pytest.mark.anyio

SCORE = b"""<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0"><part-list><score-part id="P1">
<part-name>Exercise</part-name></score-part></part-list>
<part id="P1"><measure number="1"><attributes><divisions>1</divisions>
<key><fifths>0</fifths></key>
<time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
<note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note>
</measure></part></score-partwise>"""


async def test_image_upload_queues_once_and_review_gates_students(
    client: httpx.AsyncClient, database: Database, settings: Settings, png: bytes
) -> None:
    await login(client)
    identifier = await create_exercise(client, png)
    status = (await client.get(f"/api/exercises/{identifier}/omr")).json()
    assert status["status"] == "pending"
    with database.session() as session:
        job = omr.claim(session, settings)
        assert job is not None
        assert omr.claim(session, settings) is None
        assert omr.complete(session, settings, job, SCORE)
    status = (await client.get(f"/api/exercises/{identifier}/omr")).json()
    assert status["status"] == "needs_review"
    version = status["job_id"]
    path = f"/api/exercises/{identifier}/score?version={version}"
    assert (await client.get(path)).status_code == 200
    await create_user(client)
    await login(client, "student")
    assert (await client.get(path)).status_code == 403
    assert (
        await client.post(
            f"/api/exercises/{identifier}/omr/review",
            json={"job_id": version, "action": "approve"},
        )
    ).status_code == 403
    await login(client)
    assert (
        await client.post(
            f"/api/exercises/{identifier}/omr/review",
            json={"job_id": version, "action": "approve"},
        )
    ).status_code == 200
    await login(client, "student")
    assert (await client.get(path)).status_code == 200
    await login(client)
    await client.post(
        f"/api/exercises/{identifier}/omr/review",
        json={"job_id": version, "action": "reject"},
    )
    await login(client, "student")
    assert (await client.get(path)).status_code == 403


async def test_stale_worker_cannot_publish_after_image_replacement(
    client: httpx.AsyncClient, database: Database, settings: Settings, png: bytes
) -> None:
    await login(client)
    identifier = await create_exercise(client, png)
    with database.session() as session:
        old = omr.claim(session, settings)
        assert old
    response = await client.put(
        f"/api/exercises/{identifier}",
        data={"title": "Replacement"},
        files={"image": ("new.png", png)},
    )
    assert response.status_code == 200
    with database.session() as session:
        assert not omr.complete(session, settings, old, SCORE)
        new = omr.claim(session, settings)
        assert new and new.id != old.id
        assert omr.complete(session, settings, new, SCORE)
    assert (
        await client.post(
            f"/api/exercises/{identifier}/omr/review",
            json={"job_id": old.id, "action": "approve"},
        )
    ).status_code == 409


async def test_expired_lease_recovery_and_failure_retry(
    client: httpx.AsyncClient, database: Database, settings: Settings, png: bytes
) -> None:
    await login(client)
    identifier = await create_exercise(client, png)
    with database.session() as session:
        first = omr.claim(session, settings)
        assert first
        row = session.get(OmrJob, first.id)
        assert row
        row.locked_at = datetime.now(UTC) - timedelta(
            seconds=settings.omr_lease_seconds + 1
        )
        session.commit()
        second = omr.claim(session, settings)
        assert second and second.token != first.token
        assert not omr.complete(session, settings, first, SCORE)
        omr.fail(session, settings, second, "OMR_NO_SCORE", retryable=False)
    assert (await client.get(f"/api/exercises/{identifier}/omr")).json()[
        "status"
    ] == "failed"
    assert (
        await client.post(f"/api/exercises/{identifier}/omr/rerun")
    ).status_code == 200


async def test_claim_skips_locked_jobs_and_never_duplicates(
    client: httpx.AsyncClient, database: Database, settings: Settings, png: bytes
) -> None:
    await login(client)
    first = await create_exercise(client, png)
    second = await create_exercise(client, png)
    with database.session() as locking, database.session() as worker:
        locking.scalar(
            select(OmrJob).where(OmrJob.exercise_id == first).with_for_update()
        )
        work = omr.claim(worker, settings)
        assert work and work.exercise_id == second
        assert omr.claim(worker, settings) is None
        locking.rollback()
        remaining = omr.claim(worker, settings)
        assert remaining and remaining.exercise_id == first and remaining.id != work.id


async def test_retry_budget_and_text_edit_preserve_job(
    client: httpx.AsyncClient, database: Database, settings: Settings, png: bytes
) -> None:
    await login(client)
    identifier = await create_exercise(client, png)
    before = (await client.get(f"/api/exercises/{identifier}/omr")).json()
    await client.put(f"/api/exercises/{identifier}", data={"title": "New title"})
    assert (await client.get(f"/api/exercises/{identifier}/omr")).json() == before
    with database.session() as session:
        for attempt in range(settings.omr_max_attempts):
            work = omr.claim(session, settings)
            assert work
            omr.fail(session, settings, work, "OMR_TIMEOUT", retryable=True)
            row = session.get(OmrJob, work.id)
            assert row
            assert row.attempts == attempt + 1
            if attempt + 1 < settings.omr_max_attempts:
                assert row.status == "pending"
                assert omr.claim(session, settings) is None
                row.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
                session.commit()
        assert row is not None and row.status == "failed"
        assert omr.claim(session, settings) is None


async def test_removal_deletion_and_rerun_withdraw_scores(
    client: httpx.AsyncClient,
    database: Database,
    settings: Settings,
    png: bytes,
    opus: bytes,
) -> None:
    await login(client)
    identifier = await create_exercise(client, png)
    with database.session() as session:
        job = omr.claim(session, settings)
        assert job and omr.complete(session, settings, job, SCORE)
    await client.post(
        f"/api/exercises/{identifier}/omr/review",
        json={"job_id": job.id, "action": "approve"},
    )
    await client.post(f"/api/exercises/{identifier}/omr/rerun")
    assert (
        await client.get(f"/api/exercises/{identifier}/score?version={job.id}")
    ).status_code == 409
    with database.session() as session:
        next_job = omr.claim(session, settings)
        assert next_job
    response = await client.put(
        f"/api/exercises/{identifier}",
        data={"title": "Audio only", "remove_image": "true"},
        files={"audio": ("tone.opus", opus)},
    )
    assert response.status_code == 200
    with database.session() as session:
        assert not omr.complete(session, settings, next_job, SCORE)
    assert (await client.get(f"/api/exercises/{identifier}/omr")).json()[
        "status"
    ] == "none"
    assert (
        await client.post(f"/api/exercises/{identifier}/omr/rerun")
    ).status_code == 422
    another = await create_exercise(client, png)
    with database.session() as session:
        deleted_job = omr.claim(session, settings)
        assert deleted_job
    await client.delete(f"/api/exercises/{another}")
    with database.session() as session:
        assert not omr.complete(session, settings, deleted_job, SCORE)
    assert (await client.get(f"/api/exercises/{another}/omr")).status_code == 404


async def test_omr_permissions_and_csrf(
    client: httpx.AsyncClient, database: Database, settings: Settings, png: bytes
) -> None:
    await login(client)
    identifier = await create_exercise(client, png)
    await create_user(client)
    csrf = client.headers.pop("X-CSRF-Token")
    assert (
        await client.post(f"/api/exercises/{identifier}/omr/rerun")
    ).status_code == 403
    client.headers["X-CSRF-Token"] = csrf
    await login(client, "student")
    assert (
        await client.post(f"/api/exercises/{identifier}/omr/rerun")
    ).status_code == 403
    client.cookies.clear()
    assert (await client.get(f"/api/exercises/{identifier}/omr")).status_code == 401
    assert (
        await client.get(
            f"/api/exercises/{identifier}/score?version=00000000-0000-0000-0000-000000000000"
        )
    ).status_code == 401


@pytest.mark.parametrize(
    "xml",
    [
        b"<bad/>",
        b"<score-partwise/>",
        b'<!DOCTYPE x [<!ENTITY x "expand">]><score-partwise>&x;</score-partwise>',
        SCORE.replace(b"<step>C</step>", b"<step>Z</step>"),
    ],
)
def test_invalid_musicxml_is_rejected(xml: bytes, settings: Settings) -> None:
    with pytest.raises(ServiceError, match="OMR_INVALID_SCORE"):
        omr.validate_musicxml(xml, settings.omr_max_xml_bytes)
