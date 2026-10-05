import hashlib
import io
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from PIL import Image, ImageDraw
from pydantic import SecretStr
from sqlalchemy import select

from app.database import Database
from app.game.models import CustomAvatar, Player
from app.game.services.avatars import start_avatar_job
from app.services.auth import create_user
from app.settings import Settings
from worker import generate_avatar


@pytest.fixture(autouse=True)
def no_external_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("Tests must not contact the image provider")

    monkeypatch.setattr(generate_avatar, "_openai_post", forbidden)
    monkeypatch.setattr(generate_avatar, "_moderate_image", lambda *_: False)


def sheet_bytes(empty_cell: bool = False) -> bytes:
    image = Image.new("RGBA", (1024, 1536))
    draw = ImageDraw.Draw(image)
    for row in range(6):
        for column in range(5):
            if empty_cell and row == 5 and column == 4:
                continue
            x, y = column * 1024 // 5, row * 256
            draw.rectangle(
                (x + 32, y + 32, x + 160, y + 224),
                fill=(row * 40, column * 45, 180, 255),
            )
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


@pytest.fixture
def avatar_job(database: Database, settings: Settings, tmp_path: Path) -> int:
    settings.media_root = tmp_path
    settings.openai_api_key = SecretStr("synthetic-avatar-key")
    with database.session() as session:
        user = create_user(
            session,
            settings,
            username="sheet-owner",
            password="synthetic-avatar-password",
            first_name="Sheet",
            last_name="Owner",
            role="manager",
            must_change_password=False,
        )
        with session.begin():
            player = Player(account_id=user.id, name="Sheet")
            session.add(player)
            session.flush()
            job = start_avatar_job(
                session, user.id, player.id, "Original rainbow creature", settings
            )
            return job.id


def test_one_request_creates_and_persists_all_thirty_frames(
    database: Database,
    settings: Settings,
    avatar_job: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[str] = []

    def generate(_settings: Settings, description: str) -> bytes:
        requests.append(description)
        return sheet_bytes()

    monkeypatch.setattr(generate_avatar, "_moderate", lambda *_: False)
    monkeypatch.setattr(generate_avatar, "_generate_sheet", generate)
    assert generate_avatar.process_one(database, settings)
    assert len(requests) == 1
    with database.session() as session:
        job = session.get(CustomAvatar, avatar_job)
        assert job is not None
        assert job.status == "ready"
        assert job.completed_images == 30
        assert job.phase == "review"
        assert job.asset_version == 2
    root = settings.media_root / "avatars" / "custom" / str(avatar_job)
    assert (root / "sheet.png").is_file()
    manifest = json.loads((root / "manifest.json").read_text())
    assert len(manifest["frames"]) == 30
    for frame in manifest["frames"]:
        path = root / frame["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == frame["sha256"]
        with Image.open(path) as image:
            assert image.mode == "RGBA"
            assert image.size == (384, 384)
            assert image.getchannel("A").getpixel((0, 0)) == 0
            row = (frame["level"] - 1) // 5 * 3 + ("neutral", "happy", "sad").index(
                frame["state"]
            )
            column = (frame["level"] - 1) % 5
            assert image.getpixel((192, 192)) == (row * 40, column * 45, 180, 255)
    assert not generate_avatar.process_one(database, settings)
    assert len(requests) == 1


def test_restart_reuses_the_saved_sheet_without_another_paid_request(
    database: Database,
    settings: Settings,
    avatar_job: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = settings.media_root / "avatars" / "custom" / str(avatar_job)
    root.mkdir(parents=True)
    (root / "sheet.png").write_bytes(sheet_bytes())
    with database.session() as session, session.begin():
        job = session.get(CustomAvatar, avatar_job)
        assert job is not None
        job.phase = "splitting"
        job.locked_at = datetime.now(UTC) - timedelta(hours=1)
        job.started_at = job.locked_at
        job.lease_token = "interrupted-worker"
        job.completed_images = 8

    def forbidden(*_args: object) -> bytes:
        pytest.fail("A saved sheet must not trigger another image request")

    monkeypatch.setattr(generate_avatar, "_generate_sheet", forbidden)
    settings.openai_api_key = SecretStr("")
    assert generate_avatar.process_one(database, settings)
    with database.session() as session:
        job = session.get(CustomAvatar, avatar_job)
        assert job is not None and job.status == "ready"
        assert job.completed_images == 30
        assert job.attempts == 1


def test_incomplete_sheet_fails_explicitly_and_keeps_the_original(
    database: Database,
    settings: Settings,
    avatar_job: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(generate_avatar, "_moderate", lambda *_: False)
    monkeypatch.setattr(
        generate_avatar, "_generate_sheet", lambda *_: sheet_bytes(True)
    )
    assert generate_avatar.process_one(database, settings)
    with database.session() as session:
        job = session.get(CustomAvatar, avatar_job)
        assert job is not None and job.status == "failed"
        assert job.error_code == "AVATAR_SHEET_INVALID"
    assert (
        settings.media_root / "avatars" / "custom" / str(avatar_job) / "sheet.png"
    ).is_file()


def test_active_claim_is_not_processed_twice(
    database: Database, settings: Settings, avatar_job: int
) -> None:
    with database.session() as session, session.begin():
        job = session.get(CustomAvatar, avatar_job)
        assert job is not None
        job.phase = "generating"
        job.locked_at = datetime.now(UTC)
        job.lease_token = "active-worker"
    assert not generate_avatar.process_one(database, settings)


def test_interrupted_unsaved_generation_never_repeats_a_billable_request(
    database: Database, settings: Settings, avatar_job: int
) -> None:
    with database.session() as session, session.begin():
        job = session.get(CustomAvatar, avatar_job)
        assert job is not None
        job.phase = "generating"
        job.locked_at = datetime.now(UTC) - timedelta(hours=1)
    assert generate_avatar.process_one(database, settings)
    with database.session() as session:
        job = session.scalar(select(CustomAvatar).where(CustomAvatar.id == avatar_job))
        assert job is not None and job.status == "failed"
        assert job.error_code == "AVATAR_GENERATION_INTERRUPTED"


@pytest.mark.anyio
async def test_progress_saved_gallery_and_all_thirty_private_frames_survive_reuse(
    client: httpx.AsyncClient,
    database: Database,
    settings: Settings,
    avatar_job: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    login = await client.post(
        "/api/auth/login",
        json={
            "username": "sheet-owner",
            "password": "synthetic-avatar-password",
        },
    )
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    pending = (await client.get(f"/api/game/avatars/{avatar_job}/status")).json()
    assert pending["completed_images"] == 0 and pending["total_images"] == 30
    assert pending["phase"] == "queued"
    assert pending["estimated_seconds_remaining"] > 0
    monkeypatch.setattr(generate_avatar, "_moderate", lambda *_: False)
    monkeypatch.setattr(generate_avatar, "_generate_sheet", lambda *_: sheet_bytes())
    assert generate_avatar.process_one(database, settings)
    with database.session() as session:
        stored = session.get(CustomAvatar, avatar_job)
        assert stored is not None
        player_id = stored.player_id
    assert (
        await client.post(
            f"/api/game/avatars/{avatar_job}/review", json={"decision": "approved"}
        )
    ).status_code == 200
    assert (await client.post(f"/api/game/avatars/{avatar_job}/use")).status_code == 200
    await client.post(
        f"/api/game/players/{player_id}/avatar", json={"avatar_animal": "lion"}
    )
    settings.openai_api_key = SecretStr("")
    quota = (await client.get("/api/game/avatars/quota")).json()
    assert quota["generation_available"] is False
    saved = (await client.get(f"/api/game/avatars/saved?player_id={player_id}")).json()
    assert saved["total"] == 1 and saved["jobs"][0]["completed_images"] == 30
    assert (await client.post(f"/api/game/avatars/{avatar_job}/use")).status_code == 200
    for level in range(1, 11):
        for state in ("neutral", "happy", "sad"):
            response = await client.head(
                f"/api/game/avatars/{avatar_job}/files/{state}?level={level}"
            )
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["x-accel-redirect"].endswith(
                f"avatar_{level:02}_{state}.png"
            )
    assert (
        await client.get(f"/api/game/avatars/{avatar_job}/files/happy?level=11")
    ).status_code == 422
    assert (
        await client.get(f"/api/game/avatars/saved?player_id={player_id}&offset=-1")
    ).status_code == 422
    client.cookies.clear()
    assert (
        await client.get(f"/api/game/avatars/saved?player_id={player_id}")
    ).status_code == 401


def test_generation_payload_uses_one_image_not_thirty_requests(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    import base64

    calls: list[dict[str, object]] = []

    def post(
        _settings: Settings, path: str, payload: dict[str, object], _timeout: float
    ) -> dict[str, object]:
        assert path == "/images/generations"
        calls.append(payload)
        return {"data": [{"b64_json": base64.b64encode(sheet_bytes()).decode()}]}

    settings.avatar_image_model = "gpt-image-1-mini"
    settings.avatar_image_quality = "low"
    monkeypatch.setattr(generate_avatar, "_openai_post", post)
    assert (
        generate_avatar._generate_sheet(settings, "Original creature") == sheet_bytes()
    )
    assert len(calls) == 1
    assert calls[0]["n"] == 1
    assert calls[0]["size"] == "1024x1536"
    assert calls[0]["quality"] == "low"
    assert calls[0]["background"] == "transparent"
    assert "response_format" not in calls[0]


def test_without_a_key_the_worker_leaves_queued_generation_untouched(
    database: Database, settings: Settings, avatar_job: int
) -> None:
    settings.openai_api_key = SecretStr("")
    assert not generate_avatar.process_one(database, settings)
    with database.session() as session:
        job = session.get(CustomAvatar, avatar_job)
        assert job is not None and job.status == "pending"
        assert job.attempts == 0


def test_repeated_requests_reuse_a_pending_job_without_consuming_quota(
    database: Database, settings: Settings, avatar_job: int
) -> None:
    from app.game.models import AvatarGenerationLog
    from app.services.auth import ServiceError

    with database.session() as session, session.begin():
        first = session.get(CustomAvatar, avatar_job)
        assert first is not None
        retried = start_avatar_job(
            session, first.account_id, first.player_id, first.description, settings
        )
        assert retried.id == first.id
        assert len(list(session.scalars(select(AvatarGenerationLog)))) == 1
        with pytest.raises(ServiceError) as conflict:
            start_avatar_job(
                session, first.account_id, first.player_id, "Another creature", settings
            )
        assert conflict.value.code == "AVATAR_JOB_BUSY"


@pytest.mark.anyio
async def test_missing_frame_prevents_selecting_an_incomplete_avatar(
    client: httpx.AsyncClient,
    database: Database,
    settings: Settings,
    avatar_job: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(generate_avatar, "_moderate", lambda *_: False)
    monkeypatch.setattr(generate_avatar, "_generate_sheet", lambda *_: sheet_bytes())
    assert generate_avatar.process_one(database, settings)
    with database.session() as session, session.begin():
        job = session.get(CustomAvatar, avatar_job)
        assert job is not None
        job.review_status = "approved"
    path = settings.media_root / f"avatars/custom/{avatar_job}/levels/avatar_10_sad.png"
    path.unlink()
    login = await client.post(
        "/api/auth/login",
        json={"username": "sheet-owner", "password": "synthetic-avatar-password"},
    )
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    response = await client.post(f"/api/game/avatars/{avatar_job}/use")
    assert response.status_code == 409
    assert response.json()["error"] == "AVATAR_ASSETS_MISSING"
    with database.session() as session:
        job = session.get(CustomAvatar, avatar_job)
        assert job is not None
        player_id = job.player_id
    response = await client.patch(
        f"/api/game/players/{player_id}", json={"custom_avatar_id": avatar_job}
    )
    assert response.status_code == 409
    with database.session() as session:
        player = session.get(Player, player_id)
        assert player is not None and player.custom_avatar_id is None


def test_a_late_provider_reply_cannot_replace_the_new_workers_saved_sheet(
    database: Database,
    settings: Settings,
    avatar_job: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = settings.media_root / f"avatars/custom/{avatar_job}"
    newer = io.BytesIO()
    with Image.open(io.BytesIO(sheet_bytes())) as source:
        source.save(newer, format="PNG", compress_level=0)
    current_sheet = newer.getvalue()

    def generate(_settings: Settings, _description: str) -> bytes:
        with database.session() as session, session.begin():
            job = session.get(CustomAvatar, avatar_job)
            assert job is not None
            job.lease_token = "new-worker"
            job.phase = "splitting"
        root.mkdir(parents=True)
        (root / "sheet.png").write_bytes(current_sheet)
        return sheet_bytes()

    monkeypatch.setattr(generate_avatar, "_moderate", lambda *_: False)
    monkeypatch.setattr(generate_avatar, "_generate_sheet", generate)
    assert generate_avatar.process_one(database, settings)
    assert (root / "sheet.png").read_bytes() == current_sheet


def test_partial_recovery_reports_existing_files_without_rewriting_them(
    database: Database,
    settings: Settings,
    avatar_job: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = settings.media_root / f"avatars/custom/{avatar_job}"
    root.mkdir(parents=True)
    (root / "sheet.png").write_bytes(sheet_bytes())
    frames = generate_avatar._frames(
        generate_avatar._load_sheet(root / "sheet.png", settings)
    )
    for level, state, data in frames[:8]:
        generate_avatar._atomic_write(
            root / f"levels/avatar_{level:02}_{state}.png", data
        )
    with database.session() as session, session.begin():
        job = session.get(CustomAvatar, avatar_job)
        assert job is not None
        job.phase = "splitting"
        job.completed_images = 8
        job.locked_at = datetime.now(UTC) - timedelta(hours=1)
    written: list[str] = []
    original = generate_avatar._atomic_write

    def write(path: Path, data: bytes) -> None:
        if path.parent.name == "levels":
            assert not path.is_file(), "Recovery must reuse already saved valid frames"
            written.append(path.name)
        original(path, data)

    monkeypatch.setattr(generate_avatar, "_atomic_write", write)
    settings.openai_api_key = SecretStr("")
    assert generate_avatar.process_one(database, settings)
    with database.session() as session:
        job = session.get(CustomAvatar, avatar_job)
        assert job is not None and job.status == "ready"
        assert job.completed_images == 30
    assert len(written) == 22


def test_legacy_white_background_removal_preserves_magenta_and_enclosed_white(
    settings: Settings, tmp_path: Path
) -> None:
    image = Image.new("RGB", (1024, 1024), "white")
    draw = ImageDraw.Draw(image)
    for row in range(6):
        for column in range(5):
            x, y = column * 1024 // 5, row * 1024 // 6
            draw.rectangle((x + 32, y + 24, x + 160, y + 140), fill="magenta")
            draw.rectangle((x + 80, y + 60, x + 100, y + 80), fill="white")
    path = tmp_path / "legacy-sheet.png"
    image.save(path)
    transparent = generate_avatar._load_sheet(path, settings)
    assert transparent.getpixel((40, 40)) == (255, 0, 255, 255)
    assert transparent.getpixel((90, 70)) == (255, 255, 255, 255)
    assert transparent.getpixel((0, 0)) == (255, 255, 255, 0)
    assert len(generate_avatar._frames(transparent)) == 30
