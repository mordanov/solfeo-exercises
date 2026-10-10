"""Generate one persistent sprite sheet and extract thirty custom-avatar frames."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import IO, Literal
from uuid import uuid4

import httpx
from PIL import Image, ImageChops, ImageDraw, ImageOps
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import Database
from app.game.models import AvatarGenerationLog, CustomAvatar
from app.logging import configure_logging
from app.settings import Settings

logger = logging.getLogger("worker.generate_avatar")
STATES = ("neutral", "happy", "sad")
PORTRAIT_SIZE = 256
SHEET_ATTEMPTS = 2
SHEET_LAYOUT_MARKER = "separator-grid-v1\n"
PORTRAIT_SYSTEM = (
    "Create ONE close-up face portrait icon of an original child-friendly magical "
    "creature: only the head and face, centered, filling a perfect circle with a "
    "soft pastel circular background and a thin outline. No text, labels, real "
    "people, brands or existing franchise characters. Bright pastel cartoon with "
    "clear outlines, friendly neutral expression, the young (level 1) form."
)
MIN_VISIBLE_ALPHA = 32
MIN_FIGURE_AREA = 0.02
IMAGE_SYSTEM = (
    "Create ONE sprite sheet of an original child-friendly magical creature: "
    "exactly 30 complete, separate figures in a STRICT 5-column, 6-row grid. "
    "Use identical equal-size cells and generous empty gutters; no part of a figure "
    "may touch a cell edge. Draw exactly 4 thin, straight, continuous cyan divider "
    "lines vertically and 5 matching horizontal lines between cells. "
    "Use no outer border, labels, or other cyan lines. No text, real people, brands, "
    "or existing franchise characters. Bright pastel cartoon with clear outlines. "
    "All figures must be recognizably the SAME character. "
    "Columns 1-5 are levels 1-5 in rows 1-3, and levels 6-10 in rows 4-6. "
    "Rows 1 and 4: neutral; rows 2 and 5: happy; rows 3 and 6: sad. "
    "All characters must stay the same overall size with the same body proportions. "
    "Do not grow or shrink the body by level. Show level progression through "
    "increasingly distinct magical ornaments, accessories, and details instead. "
    "Level 1 has the simplest design; each level adds or evolves visible adornments "
    "without repeating another level's design; level 10 has the richest details. "
    "Retain identity, colours, and the correct emotion for every row."
)


class AvatarError(Exception):
    def __init__(self, code: str, cell: str = "") -> None:
        self.code = code
        self.cell = cell
        super().__init__(code)


class ImageEntry(BaseModel):
    b64_json: str | None = None


class ImageReply(BaseModel):
    data: list[ImageEntry]


class ModerationEntry(BaseModel):
    flagged: bool


class ModerationReply(BaseModel):
    results: list[ModerationEntry]


class ImageModerationProof(BaseModel):
    model: Literal["omni-moderation-latest"]
    source_sha256: str
    flagged: Literal[False]


@dataclass(frozen=True)
class Lease:
    job_id: int
    description: str
    token: str


def _openai_post(
    settings: Settings, path: str, payload: dict[str, object], timeout: float = 60
) -> dict[str, object]:
    key = settings.openai_api_key.get_secret_value()
    with httpx.Client(timeout=httpx.Timeout(timeout, connect=10)) as client:
        response = client.post(
            f"https://api.openai.com/v1{path}",
            json=payload,
            headers={"Authorization": f"Bearer {key}"},
        )
    response.raise_for_status()
    if len(response.content) > settings.avatar_gen_max_image_bytes * 2:
        raise AvatarError("AVATAR_IMAGE_TOO_LARGE")
    raw: object = response.json()
    if not isinstance(raw, dict):
        raise AvatarError("AVATAR_PROVIDER_RESPONSE_INVALID")
    return {str(key): value for key, value in raw.items()}


def _moderate(settings: Settings, description: str, image: bytes | None = None) -> bool:
    moderation_input: object = description
    if image is not None:
        moderation_input = [
            {"type": "text", "text": description},
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/png;base64,"
                    + base64.b64encode(image).decode("ascii")
                },
            },
        ]
    reply = ModerationReply.model_validate(
        _openai_post(
            settings,
            "/moderations",
            {"input": moderation_input, "model": "omni-moderation-latest"},
        )
    )
    if not reply.results:
        raise AvatarError("AVATAR_PROVIDER_RESPONSE_INVALID")
    return any(result.flagged for result in reply.results)


def _moderate_image(settings: Settings, description: str, image: bytes) -> bool:
    return _moderate(settings, description, image)


def _generate_image(settings: Settings, prompt: str, size: str) -> bytes:
    legacy = settings.avatar_image_model.startswith("dall-e-")
    payload: dict[str, object] = {
        "model": settings.avatar_image_model,
        "prompt": prompt
        + (
            " Use a solid pure-white background."
            if legacy
            else " Use a transparent background."
        ),
        "n": 1,
        "size": "1024x1024" if legacy else size,
    }
    if legacy:
        payload["response_format"] = "b64_json"
        if settings.avatar_image_model == "dall-e-3":
            payload["quality"] = "standard"
    else:
        payload.update(
            quality=settings.avatar_image_quality,
            background="transparent",
            output_format="png",
        )
    reply = ImageReply.model_validate(
        _openai_post(
            settings,
            "/images/generations",
            payload,
            settings.avatar_gen_timeout_seconds,
        )
    )
    if len(reply.data) != 1 or not reply.data[0].b64_json:
        raise AvatarError("AVATAR_PROVIDER_RESPONSE_INVALID")
    encoded = reply.data[0].b64_json
    if len(encoded) > (settings.avatar_gen_max_image_bytes + 2) // 3 * 4:
        raise AvatarError("AVATAR_IMAGE_TOO_LARGE")
    data = base64.b64decode(encoded, validate=True)
    if len(data) > settings.avatar_gen_max_image_bytes:
        raise AvatarError("AVATAR_IMAGE_TOO_LARGE")
    return data


def _generate_sheet(settings: Settings, description: str) -> bytes:
    return _generate_image(
        settings, IMAGE_SYSTEM + "\nCreature: " + description, "1024x1536"
    )


def _generate_portrait(settings: Settings, description: str) -> bytes:
    return _generate_image(
        settings, PORTRAIT_SYSTEM + "\nCreature: " + description, "1024x1024"
    )


def _circular_portrait(data: bytes) -> bytes:
    with Image.open(io.BytesIO(data)) as source:
        if source.format != "PNG" or source.width != source.height:
            raise AvatarError("AVATAR_PORTRAIT_INVALID")
        image = source.convert("RGBA").resize(
            (PORTRAIT_SIZE, PORTRAIT_SIZE), Image.Resampling.LANCZOS
        )
    oversized = PORTRAIT_SIZE * 4
    mask = Image.new("L", (oversized, oversized), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, oversized - 1, oversized - 1), fill=255)
    mask = mask.resize((PORTRAIT_SIZE, PORTRAIT_SIZE), Image.Resampling.LANCZOS)
    image.putalpha(ImageChops.multiply(image.getchannel("A"), mask))
    encoded = io.BytesIO()
    image.save(encoded, format="PNG")
    return encoded.getvalue()


def _ensure_portrait(settings: Settings, description: str, path: Path) -> None:
    # The face icon is optional: any failure leaves the 30 frames usable and the
    # interface falls back to the neutral level-1 frame.
    if path.is_file():
        return
    try:
        data = _generate_portrait(settings, description)
        if _moderate_image(settings, description, data):
            logger.warning("AVATAR_PORTRAIT_FLAGGED")
            return
        _atomic_write(path, _circular_portrait(data))
    except Exception:
        logger.exception("AVATAR_PORTRAIT_FAILED")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def _claim(database: Database, settings: Settings) -> Lease | None:
    now = datetime.now(UTC)
    expired = now - timedelta(seconds=settings.avatar_gen_timeout_seconds + 60)
    with database.session() as session, session.begin():
        query = (
            select(CustomAvatar)
            .where(
                CustomAvatar.status == "pending",
                or_(CustomAvatar.locked_at.is_(None), CustomAvatar.locked_at < expired),
            )
            .order_by(CustomAvatar.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not settings.openai_api_key.get_secret_value():
            query = query.where(CustomAvatar.phase != "queued")
        job = session.scalar(query)
        if job is None:
            return None
        token = str(uuid4())
        job.lease_token = token
        job.locked_at = now
        job.started_at = job.started_at or now
        job.attempts += 1
        job.asset_version = 2
        return Lease(job.id, job.description, token)


def _leased_job(session: Session, lease: Lease) -> CustomAvatar:
    job = session.scalar(
        select(CustomAvatar)
        .where(CustomAvatar.id == lease.job_id, CustomAvatar.lease_token == lease.token)
        .with_for_update()
    )
    if job is None or job.status != "pending":
        raise AvatarError("AVATAR_LEASE_LOST")
    return job


def _save_sheet(database: Database, lease: Lease, path: Path, data: bytes) -> None:
    with database.session() as session, session.begin():
        job = _leased_job(session, lease)
        _atomic_write(path.parent / "sheet-layout.txt", SHEET_LAYOUT_MARKER.encode())
        _atomic_write(path, data)
        job.phase = "image_moderating"
        job.locked_at = datetime.now(UTC)


def _has_image_moderation(path: Path, digest: str) -> bool:
    try:
        proof = ImageModerationProof.model_validate_json(path.read_bytes())
    except (OSError, ValueError):
        return False
    return proof.source_sha256 == digest


def _save_image_moderation(
    database: Database, lease: Lease, path: Path, digest: str
) -> None:
    with database.session() as session, session.begin():
        job = _leased_job(session, lease)
        proof = ImageModerationProof(
            model="omni-moderation-latest", source_sha256=digest, flagged=False
        )
        _atomic_write(path, (proof.model_dump_json() + "\n").encode())
        job.phase = "splitting"
        job.locked_at = datetime.now(UTC)


def _update(
    database: Database,
    lease: Lease,
    phase: str,
    *,
    completed: int | None = None,
    error: str | None = None,
) -> None:
    with database.session() as session, session.begin():
        job = _leased_job(session, lease)
        job.phase = phase
        job.locked_at = datetime.now(UTC)
        if completed is not None:
            job.completed_images = completed
        if error:
            job.status = "failed"
            job.error_code = error
            job.completed_at = datetime.now(UTC)
            if job.generation_log_id is not None:
                log = session.get(AvatarGenerationLog, job.generation_log_id)
                if log:
                    log.flagged = error == "MODERATION_FLAGGED"
                    log.billable = False
        elif phase == "review":
            job.status = "ready"
            job.review_status = "pending"
            job.completed_at = datetime.now(UTC)
            prefix = f"avatars/custom/{job.id}/levels/avatar_01_"
            job.base_path = prefix + "neutral.png"
            job.happy_path = prefix + "happy.png"
            job.sad_path = prefix + "sad.png"


def _decode_sheet(source: Path | IO[bytes], settings: Settings) -> Image.Image:
    with Image.open(source) as source_image:
        if source_image.format != "PNG" or source_image.size not in (
            (1024, 1536),
            (1024, 1024),
        ):
            raise AvatarError("AVATAR_SHEET_INVALID")
        image = source_image.convert("RGBA")
    if image.getchannel("A").getextrema()[0] == 255:
        # Legacy DALL-E has no native transparency. Remove only edge-connected white.
        red, green, blue = image.convert("RGB").split()
        mask = ImageChops.darker(ImageChops.darker(red, green), blue).point(
            lambda value: 255 if value >= 245 else 0
        )
        for point in (
            (0, 0),
            (image.width - 1, 0),
            (0, image.height - 1),
            (image.width - 1, image.height - 1),
        ):
            if mask.getpixel(point) == 255:
                ImageDraw.floodfill(mask, point, 128)
        pixels = bytearray(image.tobytes())
        mask_bytes = mask.tobytes()
        for index in range(image.width * image.height):
            if mask_bytes[index] == 128:
                pixels[index * 4 + 3] = 0
        image = Image.frombytes("RGBA", image.size, bytes(pixels))
    return image


def _load_sheet(path: Path, settings: Settings) -> Image.Image:
    if path.stat().st_size > settings.avatar_gen_max_image_bytes:
        raise AvatarError("AVATAR_IMAGE_TOO_LARGE")
    return _decode_sheet(path, settings)


def _generate_usable_sheet(settings: Settings, description: str) -> bytes:
    # The provider sometimes ignores the grid. One extra request is worth it;
    # a second invalid sheet is returned so the saved original explains the failure.
    for attempt in range(SHEET_ATTEMPTS):
        data = _generate_sheet(settings, description)
        try:
            _figures(
                _decode_sheet(io.BytesIO(data), settings),
                require_separator_lines=True,
            )
        except AvatarError as error:
            if error.code != "AVATAR_SHEET_INVALID" or attempt == SHEET_ATTEMPTS - 1:
                return data
            logger.warning("AVATAR_SHEET_REGENERATED", extra={"cell": error.cell})
        else:
            return data
    raise AssertionError("unreachable")


def _separator_bands(image: Image.Image, *, vertical: bool) -> list[tuple[int, int]]:
    red, green, blue, alpha = image.convert("RGBA").split()
    cyan = ImageChops.darker(
        ImageChops.darker(
            red.point(lambda value: 255 if value <= 100 else 0),
            green.point(lambda value: 255 if value >= 180 else 0),
        ),
        ImageChops.darker(
            blue.point(lambda value: 255 if value >= 180 else 0),
            alpha.point(lambda value: 255 if value >= MIN_VISIBLE_ALPHA else 0),
        ),
    )
    projection_size = (image.width, 1) if vertical else (1, image.height)
    projection = cyan.resize(projection_size, Image.Resampling.BOX)
    extent = image.width if vertical else image.height
    positions: list[int] = []
    for coordinate in range(extent):
        value = projection.getpixel((coordinate, 0) if vertical else (0, coordinate))
        if isinstance(value, int) and value >= 180:
            positions.append(coordinate)
    bands: list[tuple[int, int]] = []
    for position in positions:
        if bands and position == bands[-1][1] + 1:
            bands[-1] = (bands[-1][0], position)
        else:
            bands.append((position, position))
    return bands


def _grid_bounds(
    extent: int, count: int, bands: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    if len(bands) != count - 1:
        raise AvatarError("AVATAR_SHEET_INVALID", "grid=separators")
    maximum_band = max(8, extent // count // 20)
    if any(end - start + 1 > maximum_band for start, end in bands):
        raise AvatarError("AVATAR_SHEET_INVALID", "grid=separators")
    bounds = [
        (0, bands[0][0]),
        *[
            (previous[1] + 1, following[0])
            for previous, following in zip(bands, bands[1:], strict=False)
        ],
        (bands[-1][1] + 1, extent),
    ]
    if any(end - start < extent // count // 2 for start, end in bounds):
        raise AvatarError("AVATAR_SHEET_INVALID", "grid=separators")
    return bounds


def _figures(
    image: Image.Image, *, require_separator_lines: bool = False
) -> list[tuple[int, str, Image.Image]]:
    vertical_bands = _separator_bands(image, vertical=True)
    horizontal_bands = _separator_bands(image, vertical=False)
    if not vertical_bands and not horizontal_bands and not require_separator_lines:
        column_bounds = [
            (index * image.width // 5, (index + 1) * image.width // 5)
            for index in range(5)
        ]
        row_bounds = [
            (index * image.height // 6, (index + 1) * image.height // 6)
            for index in range(6)
        ]
    else:
        column_bounds = _grid_bounds(image.width, 5, vertical_bands)
        row_bounds = _grid_bounds(image.height, 6, horizontal_bands)
    figures: list[tuple[int, str, Image.Image]] = []
    for level in range(1, 11):
        column = (level - 1) % 5
        for state_index, state in enumerate(STATES):
            row = (level - 1) // 5 * 3 + state_index
            cell = image.crop(
                (
                    column_bounds[column][0],
                    row_bounds[row][0],
                    column_bounds[column][1],
                    row_bounds[row][1],
                )
            )
            bounds = (
                cell.getchannel("A")
                .point(lambda value: 255 if value >= MIN_VISIBLE_ALPHA else 0)
                .getbbox()
            )
            if (
                bounds is None
                or (bounds[2] - bounds[0]) * (bounds[3] - bounds[1])
                < cell.width * cell.height * MIN_FIGURE_AREA
            ):
                raise AvatarError(
                    "AVATAR_SHEET_INVALID", f"level={level} state={state}"
                )
            figures.append((level, state, cell.crop(bounds)))
    return figures


def _frames(
    image: Image.Image, *, require_separator_lines: bool = False
) -> list[tuple[int, str, bytes]]:
    frames: list[tuple[int, str, bytes]] = []
    for level, state, cropped in _figures(
        image, require_separator_lines=require_separator_lines
    ):
        resized = ImageOps.contain(cropped, (360, 360), Image.Resampling.LANCZOS)
        frame = Image.new("RGBA", (384, 384))
        frame.alpha_composite(
            resized, ((384 - resized.width) // 2, (384 - resized.height) // 2)
        )
        encoded = io.BytesIO()
        frame.save(encoded, format="PNG")
        frames.append((level, state, encoded.getvalue()))
    return frames


def process_one(database: Database, settings: Settings) -> bool:
    lease = _claim(database, settings)
    if lease is None:
        return False
    root = settings.media_root / "avatars" / "custom" / str(lease.job_id)
    sheet = root / "sheet.png"
    try:
        with database.session() as session:
            job = session.get(CustomAvatar, lease.job_id)
            assert job is not None
            previous_phase = job.phase
        if not sheet.is_file():
            if previous_phase != "queued":
                raise AvatarError("AVATAR_GENERATION_INTERRUPTED")
            _update(database, lease, "moderating")
            if _moderate(settings, lease.description):
                raise AvatarError("MODERATION_FLAGGED")
            _update(database, lease, "generating")
            data = _generate_usable_sheet(settings, lease.description)
            _save_sheet(database, lease, sheet, data)
        if sheet.stat().st_size > settings.avatar_gen_max_image_bytes:
            raise AvatarError("AVATAR_IMAGE_TOO_LARGE")
        sheet_data = sheet.read_bytes()
        digest = hashlib.sha256(sheet_data).hexdigest()
        proof_path = root / "moderation.json"
        # Old workers persisted sheets without moderation; phase alone is not proof.
        if not _has_image_moderation(proof_path, digest):
            _update(database, lease, "image_moderating")
            if _moderate_image(settings, lease.description, sheet_data):
                raise AvatarError("MODERATION_FLAGGED")
            _save_image_moderation(database, lease, proof_path, digest)
        _update(database, lease, "splitting")
        image = _load_sheet(sheet, settings)
        layout_marker = root / "sheet-layout.txt"
        requires_separator_lines = False
        if layout_marker.is_file():
            if layout_marker.read_text() != SHEET_LAYOUT_MARKER:
                raise AvatarError("AVATAR_SHEET_INVALID", "grid=metadata")
            requires_separator_lines = True
        frames = _frames(image, require_separator_lines=requires_separator_lines)
        persisted: set[tuple[int, str]] = set()
        for level, state, data in frames:
            path = root / f"levels/avatar_{level:02}_{state}.png"
            if (
                path.is_file()
                and path.stat().st_size == len(data)
                and path.read_bytes() == data
            ):
                persisted.add((level, state))
        _update(database, lease, "splitting", completed=len(persisted))
        manifest_frames: list[dict[str, object]] = []
        for level, state, data in frames:
            filename = f"levels/avatar_{level:02}_{state}.png"
            if (level, state) not in persisted:
                _atomic_write(root / filename, data)
                persisted.add((level, state))
                _update(database, lease, "splitting", completed=len(persisted))
            manifest_frames.append(
                {
                    "level": level,
                    "state": state,
                    "file": filename,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        manifest = {
            "version": 2,
            "source_sha256": digest,
            "frames": manifest_frames,
        }
        _atomic_write(
            root / "manifest.json", (json.dumps(manifest, indent=2) + "\n").encode()
        )
        _update(database, lease, "splitting", completed=30)
        _ensure_portrait(settings, lease.description, root / "portrait.png")
        _update(database, lease, "review", completed=30)
        logger.info("AVATAR_JOB_READY", extra={"job_id": lease.job_id})
    except Exception as error:
        if isinstance(error, AvatarError):
            code = error.code
        elif isinstance(error, httpx.HTTPStatusError):
            code = (
                "AVATAR_PROVIDER_AUTH_ERROR"
                if error.response.status_code in (401, 403)
                else "AVATAR_PROVIDER_REQUEST_FAILED"
            )
        elif isinstance(error, httpx.TimeoutException):
            code = "AVATAR_PROVIDER_TIMEOUT"
        else:
            code = "AVATAR_GENERATION_FAILED"
        logger.exception(
            "AVATAR_JOB_FAILED",
            extra={
                "job_id": lease.job_id,
                "error_code": code,
                "cell": error.cell if isinstance(error, AvatarError) else "",
            },
        )
        if code != "AVATAR_LEASE_LOST":
            try:
                _update(database, lease, "failed", error=code)
            except AvatarError as lost:
                if lost.code != "AVATAR_LEASE_LOST":
                    raise
                logger.warning("AVATAR_LEASE_LOST", extra={"job_id": lease.job_id})
    return True


def main() -> None:
    settings = Settings()
    configure_logging("debug" if settings.log_level == "trace" else settings.log_level)
    database = Database(settings)
    if not settings.openai_api_key.get_secret_value():
        logger.warning("AVATAR_GENERATION_UNCONFIGURED")
    logger.info("AVATAR_WORKER_STARTED")
    try:
        while True:
            try:
                process_one(database, settings)
            except Exception:
                logger.exception("AVATAR_WORKER_ERROR")
            time.sleep(settings.avatar_gen_poll_seconds)
    finally:
        database.close()


if __name__ == "__main__":
    main()
