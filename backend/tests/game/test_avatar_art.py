from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.database import Database
from app.game.config import ANIMAL_IDS, LEVEL_THRESHOLDS
from app.game.models import CustomAvatar, Player
from app.services.auth import create_user
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[3]
STATES = ("neutral", "happy", "sad")


def test_every_catalog_avatar_has_ten_transparent_stages() -> None:
    assert set(ANIMAL_IDS) == {
        "unicorn",
        "dragon",
        "phoenix",
        "griffin",
        "sphinx_cat",
        "kitsune_fox",
        "pegasus",
        "mermaid",
        "lion",
        "panda",
        "rhino",
    }
    for animal in ANIMAL_IDS:
        for level in range(1, 11):
            for state in STATES:
                path = (
                    ROOT
                    / "frontend/public/assets/avatars"
                    / animal
                    / f"{animal}_{level:02}_{state}.png"
                )
                with Image.open(path) as image:
                    assert image.mode == "RGBA"
                    assert image.size == (384, 384)
                    alpha = image.getchannel("A")
                    minimum, maximum = alpha.getextrema()
                    assert minimum == 0
                    assert isinstance(maximum, (int, float))
                    assert maximum >= 250
                    assert alpha.getpixel((0, 0)) == 0
                    box = alpha.getbbox()
                    assert box is not None
                    assert max(box[2] - box[0], box[3] - box[1]) >= 358
        with Image.open(ROOT / "avatars/selection" / f"{animal}.png") as image:
            assert image.mode == "RGBA"
            assert image.getchannel("A").getpixel((0, 0)) == 0


async def identity(
    client: httpx.AsyncClient,
    database: Database,
    settings: Settings,
    role: str = "manager",
) -> tuple[int, int]:
    with database.session() as session:
        user = create_user(
            session,
            settings,
            username=f"art-{role}",
            password="synthetic-art-password",
            first_name="Art",
            last_name="Manager",
            role=role,
            must_change_password=False,
        )
        with session.begin():
            player = Player(
                account_id=user.id, name="Art", avatar_animal="dragon", xp=0
            )
            session.add(player)
            session.flush()
            user_id, player_id = user.id, player.id
    response = await client.post(
        "/api/auth/login",
        json={"username": f"art-{role}", "password": "synthetic-art-password"},
    )
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return user_id, player_id


@pytest.mark.anyio
async def test_catalog_choice_and_persisted_level(
    client: httpx.AsyncClient, database: Database, settings: Settings
) -> None:
    _, player_id = await identity(client, database, settings)
    assert {
        animal["id"]
        for animal in (await client.get("/api/game/avatars/catalog")).json()
    } == set(ANIMAL_IDS)
    for index, xp in enumerate(LEVEL_THRESHOLDS):
        with database.session() as session, session.begin():
            player = session.get(Player, player_id)
            assert player is not None
            player.xp = xp
        response = await client.get(f"/api/game/players/{player_id}")
        assert response.json()["avatar_level"] == index + 1
    for animal in ("lion", "panda", "rhino"):
        response = await client.post(
            f"/api/game/players/{player_id}/avatar", json={"avatar_animal": animal}
        )
        assert response.status_code == 200, response.text
        assert response.json()["avatar_animal"] == animal
    assert (
        await client.post(
            f"/api/game/players/{player_id}/avatar", json={"avatar_animal": "invalid"}
        )
    ).status_code == 422


@pytest.mark.anyio
async def test_ready_custom_avatar_can_be_used_and_served_privately(
    client: httpx.AsyncClient, database: Database, settings: Settings, tmp_path: Path
) -> None:
    user_id, player_id = await identity(client, database, settings)
    settings.media_root = tmp_path
    with database.session() as session, session.begin():
        job = CustomAvatar(
            account_id=user_id,
            player_id=player_id,
            description="Synthetic",
            status="ready",
            review_status="approved",
        )
        session.add(job)
        session.flush()
        job_id = job.id
        job.base_path = f"avatars/custom/{job_id}/base.png"
        job.happy_path = f"avatars/custom/{job_id}/happy.png"
        job.sad_path = f"avatars/custom/{job_id}/sad.png"
    for state in ("base", "happy", "sad"):
        path = tmp_path / f"avatars/custom/{job_id}/{state}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", (32, 32), "red").save(path)
    response = await client.post(f"/api/game/avatars/{job_id}/use")
    assert response.status_code == 200, response.text
    player = (await client.get(f"/api/game/players/{player_id}")).json()
    assert player["custom_avatar_id"] == job_id
    url = f"/api/game/avatars/{job_id}/files/happy"
    response = await client.get(url)
    assert response.status_code == 200
    assert (
        response.headers["x-accel-redirect"]
        == f"/_protected_media/avatars/custom/{job_id}/happy.png"
    )
    assert response.headers["content-type"] == "image/png"
    assert (await client.head(url)).status_code == 200
    response = await client.patch(
        f"/api/game/players/{player_id}", json={"avatar_animal": "lion"}
    )
    assert response.json()["custom_avatar_id"] is None
    response = await client.patch(
        f"/api/game/players/{player_id}", json={"custom_avatar_id": job_id + 99999}
    )
    assert response.status_code == 422
    response = await client.post(
        f"/api/game/players/{player_id}/avatar", json={"avatar_animal": "panda"}
    )
    assert response.json()["custom_avatar_id"] is None
    with database.session() as session, session.begin():
        stored_job = session.get(CustomAvatar, job_id)
        assert stored_job is not None
        stored_job.happy_path = "../outside.png"
    assert (await client.get(url)).status_code == 404
    with database.session() as session, session.begin():
        stored_job = session.get(CustomAvatar, job_id)
        assert stored_job is not None
        stored_job.happy_path = "private.png"
    Image.new("RGBA", (1, 1), "red").save(tmp_path / "private.png")
    assert (await client.get(url)).status_code == 404
    client.cookies.clear()
    assert (await client.get(url)).status_code == 401


@pytest.mark.anyio
async def test_student_can_change_only_an_owned_avatar(
    client: httpx.AsyncClient, database: Database, settings: Settings
) -> None:
    manager_id, foreign_id = await identity(client, database, settings)
    with database.session() as session, session.begin():
        job = CustomAvatar(
            account_id=manager_id,
            player_id=foreign_id,
            description="Private",
            status="ready",
        )
        session.add(job)
        session.flush()
        job_id = job.id
    _, own_id = await identity(client, database, settings, "student")
    body = {"avatar_animal": "rhino"}
    response = await client.post(f"/api/game/players/{own_id}/avatar", json=body)
    assert response.status_code == 200
    assert (await client.get(f"/api/game/players/{own_id}")).json()[
        "avatar_animal"
    ] == "rhino"
    assert (
        await client.post(f"/api/game/players/{foreign_id}/avatar", json=body)
    ).status_code == 404
    assert (
        await client.patch(f"/api/game/players/{own_id}", json={"name": "Changed"})
    ).status_code == 403
    assert (await client.post(f"/api/game/avatars/{job_id}/use")).status_code == 404
    assert (
        await client.get(f"/api/game/avatars/{job_id}/files/neutral")
    ).status_code == 404
    assert (
        await client.get(f"/api/game/avatars?player_id={foreign_id}")
    ).status_code == 404
    del client.headers["X-CSRF-Token"]
    assert (
        await client.post(f"/api/game/players/{own_id}/avatar", json=body)
    ).status_code == 403
    client.cookies.clear()
    assert (
        await client.post(f"/api/game/players/{own_id}/avatar", json=body)
    ).status_code == 401


@pytest.mark.anyio
async def test_custom_generation_requires_configuration(
    client: httpx.AsyncClient, database: Database, settings: Settings
) -> None:
    from pydantic import SecretStr
    from sqlalchemy import select

    _, player_id = await identity(client, database, settings)
    settings.openai_api_key = SecretStr("")
    body = {"player_id": player_id, "description": "An original tiny rainbow creature"}
    response = await client.post("/api/game/avatars/generate", json=body)
    assert response.status_code == 503
    assert response.json()["error"] == "AVATAR_GENERATION_UNAVAILABLE"
    with database.session() as session:
        assert session.scalar(select(CustomAvatar)) is None
    settings.openai_api_key = SecretStr("synthetic-nonfunctional-key")
    response = await client.post("/api/game/avatars/generate", json=body)
    assert response.status_code == 200
    assert (await client.get(f"/api/game/avatars?player_id={player_id}")).json()[0][
        "id"
    ] == response.json()["job_id"]
    assert (
        await client.get(f"/api/game/avatars/{response.json()['job_id']}/status")
    ).json()["status"] == "pending"
