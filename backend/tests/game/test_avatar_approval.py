import base64
import hashlib
import io
import json
import shutil
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, tzinfo
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import httpx
import pytest
from PIL import Image, ImageDraw
from pydantic import SecretStr

from app.database import Database
from app.game.api.avatars import _job_out
from app.game.models import AvatarGenerationLog, CustomAvatar, Player
from app.game.services.avatars import (
    avatar_path,
    check_daily_quota,
    list_review_jobs,
    review_avatar,
    start_avatar_job,
)
from app.services.auth import ServiceError, create_user
from app.settings import Settings
from worker import generate_avatar


@pytest.fixture
def review_job(
    database: Database, settings: Settings
) -> Iterator[tuple[int, int, int]]:
    root = Path(".avatar-approval-assets") / uuid4().hex
    settings.media_root = root.resolve()
    settings.openai_api_key = SecretStr("synthetic-key")
    with database.session() as session:
        owner = create_user(
            session,
            settings,
            username="review-owner",
            password="synthetic-password",
            first_name="Owner",
            last_name="Avatar",
            role="student",
            must_change_password=False,
        )
        manager = create_user(
            session,
            settings,
            username="review-manager",
            password="synthetic-password",
            first_name="Manager",
            last_name="Avatar",
            role="manager",
            must_change_password=False,
        )
        with session.begin():
            player = Player(account_id=owner.id, name="Review", avatar_animal="lion")
            session.add(player)
            session.flush()
            job = start_avatar_job(
                session, owner.id, player.id, "Friendly creature", settings
            )
            ids = job.id, player.id, manager.id
    try:
        yield ids
    finally:
        with database.session() as session, session.begin():
            stored_player = session.get(Player, ids[1])
            assert stored_player is not None
            stored_player.avatar_review_job_id = None
        shutil.rmtree(root, ignore_errors=True)


def make_ready(database: Database, job_id: int, settings: Settings) -> None:
    root = settings.media_root / "avatars" / "custom" / str(job_id)
    (root / "levels").mkdir(parents=True)
    for filename in ["sheet.png", "manifest.json"] + [
        f"levels/avatar_{level:02}_{state}.png"
        for level in range(1, 11)
        for state in ("neutral", "happy", "sad")
    ]:
        (root / filename).write_bytes(b"synthetic-assets")
    with database.session() as session, session.begin():
        job = session.get(CustomAvatar, job_id)
        assert job is not None
        job.status = "ready"
        job.phase = "review"
        job.completed_images = 30
        prefix = f"avatars/custom/{job_id}/levels/avatar_01_"
        job.base_path = prefix + "neutral.png"
        job.happy_path = prefix + "happy.png"
        job.sad_path = prefix + "sad.png"


def synthetic_sheet() -> bytes:
    image = Image.new("RGBA", (1024, 1536))
    draw = ImageDraw.Draw(image)
    for row in range(6):
        for column in range(5):
            x, y = column * 1024 // 5, row * 256
            draw.rectangle((x + 32, y + 32, x + 160, y + 224), fill="purple")
    for column in range(1, 5):
        x = column * image.width // 5
        draw.rectangle((x - 2, 0, x + 1, image.height - 1), fill=(0, 255, 255))
    for row in range(1, 6):
        y = row * image.height // 6
        draw.rectangle((0, y - 2, image.width - 1, y + 1), fill=(0, 255, 255))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_portrait_file_follows_the_same_approval_rule_and_ignores_level(
    settings: Settings, tmp_path: Path
) -> None:
    settings.media_root = tmp_path
    job = CustomAvatar(
        id=7, status="ready", review_status="pending", asset_version=2, phase="review"
    )
    portrait = tmp_path / "avatars/custom/7/portrait.png"
    portrait.parent.mkdir(parents=True)
    Image.new("RGBA", (8, 8)).save(portrait)
    with pytest.raises(ServiceError) as hidden:
        avatar_path(job, "portrait", 1, settings)
    assert hidden.value.code == "AVATAR_NOT_APPROVED"
    assert avatar_path(job, "portrait", 5, settings, manager=True) == portrait.resolve()
    job.review_status = "approved"
    assert avatar_path(job, "portrait", 1, settings) == portrait.resolve()
    portrait.unlink()
    with pytest.raises(ServiceError) as missing:
        avatar_path(job, "portrait", 1, settings)
    assert missing.value.code == "FILE_NOT_FOUND"


def test_pending_job_hides_paths_even_after_generation() -> None:
    job = CustomAvatar(
        id=1,
        status="ready",
        review_status="pending",
        phase="review",
        asset_version=2,
        completed_images=30,
        base_path="private/neutral.png",
        happy_path="private/happy.png",
        sad_path="private/sad.png",
    )
    output = _job_out(job, 90)
    assert output.review_status == "pending"
    assert output.phase == "review"
    assert output.base_path is output.happy_path is output.sad_path is None
    job.review_status = "approved"
    assert _job_out(job, 90).base_path == "private/neutral.png"
    job.review_status = "rejected"
    assert _job_out(job, 90).base_path is None


def test_image_moderation_sends_text_and_image(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, object]] = []

    def post(
        _settings: Settings,
        path: str,
        payload: dict[str, object],
        timeout: float = 60,
    ) -> dict[str, object]:
        assert path == "/moderations"
        calls.append(payload)
        return {"results": [{"flagged": True}]}

    monkeypatch.setattr(generate_avatar, "_openai_post", post)
    assert generate_avatar._moderate(settings, "Friendly creature", b"image-data")
    assert calls == [
        {
            "model": "omni-moderation-latest",
            "input": [
                {"type": "text", "text": "Friendly creature"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "data:image/png;base64,"
                        + base64.b64encode(b"image-data").decode("ascii")
                    },
                },
            ],
        }
    ]


def test_generation_marks_pending_selection(
    database: Database, review_job: tuple[int, int, int]
) -> None:
    with database.session() as session:
        player = session.get(Player, review_job[1])
        assert player is not None
        assert player.avatar_review_job_id == review_job[0]
        assert player.custom_avatar_id is None


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_review_is_idempotent_and_opposite_decision_conflicts(
    database: Database,
    settings: Settings,
    review_job: tuple[int, int, int],
    decision: str,
) -> None:
    job_id, player_id, manager_id = review_job
    make_ready(database, job_id, settings)
    with database.session() as session, session.begin():
        review_avatar(session, job_id, manager_id, decision, settings)
        review_avatar(session, job_id, manager_id, decision, settings)
    with database.session() as session:
        job = session.get(CustomAvatar, job_id)
        player = session.get(Player, player_id)
        assert job is not None and player is not None
        assert job.review_status == decision
        assert job.reviewed_by == manager_id and job.reviewed_at is not None
        assert player.custom_avatar_id == (job_id if decision == "approved" else None)
    with database.session() as session, session.begin():
        with pytest.raises(ServiceError) as error:
            review_avatar(
                session,
                job_id,
                manager_id,
                "rejected" if decision == "approved" else "approved",
                settings,
            )
        assert error.value.code == "AVATAR_REVIEW_CONFLICT"


def test_approval_does_not_override_later_builtin_selection(
    database: Database,
    settings: Settings,
    review_job: tuple[int, int, int],
) -> None:
    job_id, player_id, manager_id = review_job
    make_ready(database, job_id, settings)
    with database.session() as session, session.begin():
        player = session.get(Player, player_id)
        assert player is not None
        player.avatar_review_job_id = None
        review_avatar(session, job_id, manager_id, "approved", settings)
        assert player.custom_avatar_id is None


def test_concurrent_opposite_reviews_cannot_overwrite_each_other(
    database: Database,
    settings: Settings,
    review_job: tuple[int, int, int],
) -> None:
    job_id, _, manager_id = review_job
    make_ready(database, job_id, settings)
    barrier = Barrier(2)

    def decide(decision: str) -> str:
        with database.session() as session:
            try:
                with session.begin():
                    barrier.wait(timeout=5)
                    review_avatar(session, job_id, manager_id, decision, settings)
                return decision
            except ServiceError as error:
                return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(decide, ["approved", "rejected"]))
    assert results.count("AVATAR_REVIEW_CONFLICT") == 1
    with database.session() as session:
        job = session.get(CustomAvatar, job_id)
        assert job is not None and job.review_status in results


def test_review_queue_paginates_only_ready_pending_jobs(
    database: Database,
    settings: Settings,
    review_job: tuple[int, int, int],
) -> None:
    make_ready(database, review_job[0], settings)
    with database.session() as session, session.begin():
        original = session.get(CustomAvatar, review_job[0])
        assert original is not None
        for index in range(12):
            session.add(
                CustomAvatar(
                    account_id=original.account_id,
                    player_id=original.player_id,
                    description=f"Pending review {index}",
                    status="ready",
                    review_status="pending",
                )
            )
        for status, review_status in [
            ("failed", "pending"),
            ("pending", "pending"),
            ("ready", "approved"),
            ("ready", "rejected"),
        ]:
            session.add(
                CustomAvatar(
                    account_id=original.account_id,
                    player_id=original.player_id,
                    description="Excluded from queue",
                    status=status,
                    review_status=review_status,
                )
            )
        session.flush()
        jobs, total = list_review_jobs(session)
        assert len(jobs) == 12 and total == 13
        next_jobs, next_total = list_review_jobs(session, offset=12)
        assert len(next_jobs) == 1 and next_total == 13
        assert next_jobs[0][0].id not in [job.id for job, _ in jobs]


@pytest.mark.parametrize(
    "code",
    [
        "AVATAR_PROVIDER_AUTH_ERROR",
        "AVATAR_PROVIDER_TIMEOUT",
        "AVATAR_SHEET_INVALID",
        "AVATAR_GENERATION_INTERRUPTED",
        "MODERATION_FLAGGED",
    ],
)
def test_all_worker_failures_release_quota_atomically(
    database: Database,
    review_job: tuple[int, int, int],
    code: str,
) -> None:
    lease = generate_avatar.Lease(review_job[0], "Friendly creature", "test-lease")
    with database.session() as session, session.begin():
        job = session.get(CustomAvatar, lease.job_id)
        assert job is not None
        job.lease_token = lease.token
    generate_avatar._update(database, lease, "failed", error=code)
    with database.session() as session:
        job = session.get(CustomAvatar, lease.job_id)
        assert job is not None and job.status == "failed"
        log = session.get(AvatarGenerationLog, job.generation_log_id)
        assert log is not None
        assert not log.billable
        assert log.flagged == (code == "MODERATION_FLAGGED")


@pytest.mark.parametrize("flagged", [False, True])
def test_worker_moderates_image_before_extraction_and_waits_for_review(
    database: Database,
    settings: Settings,
    review_job: tuple[int, int, int],
    monkeypatch: pytest.MonkeyPatch,
    flagged: bool,
) -> None:
    calls: list[str] = []

    def post(
        _settings: Settings,
        path: str,
        payload: dict[str, object],
        timeout: float = 60,
    ) -> dict[str, object]:
        assert path == "/moderations"
        image = isinstance(payload["input"], list)
        calls.append("image" if image else "text")
        return {"results": [{"flagged": flagged if image else False}]}

    original_frames = generate_avatar._frames

    def frames(
        image: Image.Image, *, require_separator_lines: bool = False
    ) -> list[tuple[int, str, bytes]]:
        assert calls == ["text", "image"]
        return original_frames(image, require_separator_lines=require_separator_lines)

    monkeypatch.setattr(generate_avatar, "_openai_post", post)
    monkeypatch.setattr(
        generate_avatar, "_generate_sheet", lambda *_: synthetic_sheet()
    )
    monkeypatch.setattr(generate_avatar, "_frames", frames)
    assert generate_avatar.process_one(database, settings)
    assert calls == ["text", "image"]
    with database.session() as session:
        job = session.get(CustomAvatar, review_job[0])
        player = session.get(Player, review_job[1])
        assert job is not None and player is not None
        assert job.review_status == "pending"
        assert job.status == ("failed" if flagged else "ready")
        assert job.phase == ("failed" if flagged else "review")
        assert player.custom_avatar_id is None
        log = session.get(AvatarGenerationLog, job.generation_log_id)
        assert log is not None
        assert log.billable is not flagged
        assert log.flagged is flagged
    root = settings.media_root / "avatars" / "custom" / str(review_job[0])
    assert (root / "sheet.png").is_file()
    assert (root / "levels/avatar_01_neutral.png").is_file() is not flagged


def test_provider_error_process_releases_quota(
    database: Database,
    settings: Settings,
    review_job: tuple[int, int, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def provider_error(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise httpx.ReadTimeout("Synthetic provider timeout")

    monkeypatch.setattr(generate_avatar, "_openai_post", provider_error)
    assert generate_avatar.process_one(database, settings)
    with database.session() as session:
        job = session.get(CustomAvatar, review_job[0])
        assert job is not None and job.error_code == "AVATAR_PROVIDER_TIMEOUT"
        log = session.get(AvatarGenerationLog, job.generation_log_id)
        assert log is not None and not log.billable


@pytest.mark.parametrize(
    ("proof", "flagged"),
    [("missing", False), ("missing", True), ("mismatched", False), ("valid", False)],
)
def test_saved_sheet_recovery_requires_verified_image_moderation(
    database: Database,
    settings: Settings,
    review_job: tuple[int, int, int],
    monkeypatch: pytest.MonkeyPatch,
    proof: str,
    flagged: bool,
) -> None:
    data = synthetic_sheet()
    root = settings.media_root / "avatars" / "custom" / str(review_job[0])
    root.mkdir(parents=True)
    (root / "sheet.png").write_bytes(data)
    if proof != "missing":
        (root / "moderation.json").write_text(
            json.dumps(
                {
                    "model": "omni-moderation-latest",
                    "source_sha256": hashlib.sha256(
                        data if proof == "valid" else b"another sheet"
                    ).hexdigest(),
                    "flagged": False,
                }
            )
        )
    with database.session() as session, session.begin():
        job = session.get(CustomAvatar, review_job[0])
        assert job is not None
        job.phase = "splitting"
    settings.openai_api_key = SecretStr("")
    calls: list[str] = []

    def post(
        _settings: Settings,
        path: str,
        payload: dict[str, object],
        timeout: float = 60,
    ) -> dict[str, object]:
        assert path == "/moderations"
        assert isinstance(payload["input"], list)
        calls.append(path)
        return {"results": [{"flagged": flagged}]}

    def forbidden_generation(*_args: object) -> bytes:
        pytest.fail("Recovery must not repeat paid image generation")

    monkeypatch.setattr(generate_avatar, "_openai_post", post)
    monkeypatch.setattr(generate_avatar, "_generate_sheet", forbidden_generation)
    assert generate_avatar.process_one(database, settings)
    assert len(calls) == (0 if proof == "valid" else 1)
    with database.session() as session:
        job = session.get(CustomAvatar, review_job[0])
        assert job is not None
        assert job.status == ("failed" if flagged else "ready")
        assert job.review_status == "pending"
        log = session.get(AvatarGenerationLog, job.generation_log_id)
        assert log is not None and log.billable is not flagged
    if flagged:
        assert not (root / "levels").exists()
    else:
        recorded = json.loads((root / "moderation.json").read_text())
        assert recorded["source_sha256"] == hashlib.sha256(data).hexdigest()
        assert recorded["flagged"] is False


@pytest.mark.parametrize(
    "content",
    [
        "not-json",
        '{"source_sha256":"digest"}',
        '{"model":"omni-moderation-latest","source_sha256":"digest","flagged":true}',
        '{"model":"other-model","source_sha256":"digest","flagged":false}',
    ],
)
def test_incomplete_or_flagged_moderation_proof_is_not_trusted(content: str) -> None:
    path = Path(f".avatar-approval-proof-{uuid4().hex}.json")
    try:
        path.write_text(content)
        assert not generate_avatar._has_image_moderation(path, "digest")
    finally:
        path.unlink(missing_ok=True)


def test_timezone_reset_handles_daylight_saving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.game.services import avatars

    class Clock(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> "Clock":
            return cls(2026, 3, 29, 12, tzinfo=UTC)

    monkeypatch.setattr(avatars, "datetime", Clock)
    start, end = avatars._quota_day("Europe/Madrid")
    assert start == datetime(2026, 3, 28, 23, tzinfo=UTC)
    assert end == datetime(2026, 3, 29, 22, tzinfo=UTC)


def test_daily_quota_uses_local_calendar_day(
    database: Database,
    review_job: tuple[int, int, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.game.services import avatars

    class Clock(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> "Clock":
            return cls(2026, 10, 4, 23, 30, tzinfo=UTC)

    monkeypatch.setattr(avatars, "datetime", Clock)
    with database.session() as session, session.begin():
        job = session.get(CustomAvatar, review_job[0])
        assert job is not None
        log = session.get(AvatarGenerationLog, job.generation_log_id)
        assert log is not None
        log.created_at = datetime(2026, 10, 4, 22, 0, tzinfo=UTC)
        session.add(
            AvatarGenerationLog(
                account_id=job.account_id,
                billable=True,
                created_at=datetime(2026, 10, 4, 20, 0, tzinfo=UTC),
            )
        )
        session.flush()
        assert check_daily_quota(session, job.account_id, 3, "Europe/Moscow") == 2
        assert check_daily_quota(session, job.account_id, 3) == 1


@pytest.mark.anyio
async def test_manager_queue_review_and_student_file_permissions(
    client: httpx.AsyncClient,
    database: Database,
    settings: Settings,
    review_job: tuple[int, int, int],
) -> None:
    job_id = review_job[0]
    make_ready(database, job_id, settings)
    assert (await client.get("/api/game/avatars/review")).status_code == 401
    for username, role in [
        ("review-owner", "student"),
        ("review-manager", "manager"),
    ]:
        client.cookies.clear()
        login = await client.post(
            "/api/auth/login",
            json={"username": username, "password": "synthetic-password"},
        )
        client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        if role == "student":
            assert (await client.get("/api/game/avatars/review")).status_code == 403
            assert (
                await client.post(
                    f"/api/game/avatars/{job_id}/review",
                    json={"decision": "approved"},
                )
            ).status_code == 403
            assert (
                await client.get(f"/api/game/avatars/{job_id}/files/neutral")
            ).status_code == 403
            assert (
                await client.get(f"/api/game/avatars/{job_id}/review-sheet")
            ).status_code == 403
            assert (
                await client.post(f"/api/game/avatars/{job_id}/use")
            ).status_code == 403
            status = (await client.get(f"/api/game/avatars/{job_id}/status")).json()
            assert status["review_status"] == "pending"
            assert status["base_path"] is None
        else:
            queue = (await client.get("/api/game/avatars/review")).json()
            assert queue["total"] == 1 and queue["jobs"][0]["id"] == job_id
            assert queue["jobs"][0]["player_name"] == "Review"
            sheet = await client.get(f"/api/game/avatars/{job_id}/review-sheet")
            assert sheet.status_code == 200
            assert sheet.headers["x-accel-redirect"].endswith("/sheet.png")
            assert (
                await client.post(
                    f"/api/game/avatars/{job_id}/review",
                    json={"decision": "approved"},
                )
            ).status_code == 200
            assert (await client.get("/api/game/avatars/review")).json()["total"] == 0
    client.cookies.clear()
    login = await client.post(
        "/api/auth/login",
        json={"username": "review-owner", "password": "synthetic-password"},
    )
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    assert (
        await client.get(f"/api/game/avatars/{job_id}/files/neutral")
    ).status_code == 200
    assert (await client.post(f"/api/game/avatars/{job_id}/use")).status_code == 200
