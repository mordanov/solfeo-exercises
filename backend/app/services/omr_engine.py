import logging
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath
from typing import Protocol

from PIL import Image

from app.services.auth import ServiceError
from app.services.omr import validate_musicxml
from app.settings import Settings

logger = logging.getLogger(__name__)


class OmrEngine(Protocol):
    def recognize(self, image: Path) -> bytes: ...


def read_export(directory: Path, maximum: int) -> bytes:
    candidates = sorted(
        path
        for path in directory.rglob("*")
        if path.suffix.lower() in {".mxl", ".musicxml", ".xml"}
    )
    if not candidates:
        raise ServiceError("OMR_NO_SCORE", 422)
    if len(candidates) != 1:
        raise ServiceError("OMR_MULTIPLE_SCORES", 422)
    path = candidates[0]
    if path.is_symlink() or path.stat().st_size > maximum:
        raise ServiceError("OMR_INVALID_SCORE", 422)
    try:
        if path.suffix.lower() == ".mxl":
            with zipfile.ZipFile(path) as archive:
                entries = archive.infolist()
                if (
                    len(entries) > 32
                    or sum(item.file_size for item in entries) > maximum
                ):
                    raise ValueError("ARCHIVE_SIZE")
                for entry in entries:
                    name = PurePosixPath(entry.filename)
                    if (
                        name.is_absolute()
                        or ".." in name.parts
                        or "\\" in entry.filename
                    ):
                        raise ValueError("ARCHIVE_PATH")
                container = archive.read("META-INF/container.xml")
                if (
                    b"<!ENTITY" in container.upper()
                    or b"<!DOCTYPE" in container.upper()
                ):
                    raise ValueError("ENTITY")
                root = ET.fromstring(container)
                files = root.findall(".//{*}rootfile")
                if len(files) != 1:
                    raise ValueError("ROOTFILES")
                data = archive.read(files[0].attrib["full-path"])
        else:
            data = path.read_bytes()
    except (ValueError, KeyError, ET.ParseError, zipfile.BadZipFile, RuntimeError):
        raise ServiceError("OMR_INVALID_SCORE", 422) from None
    return validate_musicxml(data, maximum)


class AudiverisEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def recognize(self, image: Path) -> bytes:
        settings = self.settings
        if not image.is_file():
            raise ServiceError("FILE_NOT_FOUND", 404)
        with tempfile.TemporaryDirectory(prefix="omr-") as temporary:
            root = Path(temporary)
            source = root / "input.png"
            deadline = time.monotonic() + settings.omr_timeout_seconds
            try:
                with Image.open(image) as picture:
                    if picture.width * picture.height > settings.image_max_pixels:
                        raise ServiceError("IMAGE_TOO_LARGE", 422)
                    picture.convert("RGB").save(source, "PNG")
                # Do not pass database or bot credentials to Java.
                environment = {
                    "HOME": temporary,
                    "PATH": f"{settings.omr_java_home}/bin:/usr/bin:/bin",
                    "JAVA_HOME": str(settings.omr_java_home),
                    "TESSDATA_PREFIX": str(settings.omr_tessdata),
                    "JAVA_OPTS": (
                        f"-Xmx{settings.omr_java_heap_mb}m -XX:ActiveProcessorCount=1 "
                        f"-Djava.awt.headless=true -Duser.home={temporary} "
                        "-Dsun.java2d.uiScale=1"
                    ),
                }
                faint = False
                while True:
                    output = root / ("faint-output" if faint else "output")
                    output.mkdir()
                    command = [
                        settings.omr_binary,
                        "-batch",
                        "-transcribe",
                        "-export",
                        "-option",
                        "org.audiveris.omr.sheet.ProcessingSwitches.indentations="
                        + str(settings.omr_detect_movements).lower(),
                    ]
                    if faint:
                        command.extend(
                            [
                                "-option",
                                "org.audiveris.omr.image.AdaptiveDescriptor.meanCoeff="
                                + str(settings.omr_faint_mean_coeff),
                            ]
                        )
                    command.extend(["-output", str(output), "--", str(source)])
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ServiceError("OMR_TIMEOUT", 503)
                    with tempfile.TemporaryFile(dir=root) as diagnostics:
                        try:
                            subprocess.run(
                                command,
                                cwd=root,
                                env=environment,
                                check=True,
                                timeout=remaining,
                                stdout=diagnostics,
                                stderr=subprocess.STDOUT,
                            )
                        except subprocess.CalledProcessError:
                            diagnostics.seek(0, 2)
                            diagnostics.seek(max(0, diagnostics.tell() - 65536))
                            no_staff = b"No system found" in diagnostics.read(65536)
                            if no_staff and not faint:
                                logger.warning("OMR_FAINT_STAFF_RETRY")
                                faint = True
                                continue
                            code = "OMR_NO_STAFF" if no_staff else "OMR_ENGINE_FAILED"
                            raise ServiceError(code, 422) from None
                    return read_export(output, settings.omr_max_xml_bytes)
            except subprocess.TimeoutExpired:
                raise ServiceError("OMR_TIMEOUT", 503) from None
            except (OSError, Image.DecompressionBombError):
                raise ServiceError("OMR_ENGINE_UNAVAILABLE", 503) from None
