import hashlib
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LOGGER = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="OMR_", extra="forbid"
    )

    image: str = "solfeo-omr:5.11.0"
    samples_dir: Path = Path("samples")
    output_dir: Path = Path("output")
    timeout_seconds: int = Field(default=300, gt=0)
    cpus: float = Field(default=2, gt=0)
    memory_mb: int = Field(default=4096, gt=0)
    java_options: str = (
        "-Xmx2g -Djava.awt.headless=true -Duser.home=/tmp -Dsun.java2d.uiScale=1"
    )


@dataclass(frozen=True)
class Classification:
    label: Literal["fully", "partly", "failed"]
    percentage: float | None


def classify(
    expected: int,
    substitutions: int,
    omissions: int,
    extras: int,
    *,
    usable: bool = True,
) -> Classification:
    if expected <= 0 or min(substitutions, omissions, extras) < 0:
        raise ValueError(
            "Expected events must be positive and error counts nonnegative"
        )
    if substitutions + omissions > expected:
        raise ValueError("Substitutions and omissions exceed expected events")
    if not usable:
        return Classification("failed", None)
    percentage = max(
        Fraction(0),
        100 * Fraction(expected - substitutions - omissions - extras, expected),
    )
    label: Literal["fully", "partly", "failed"] = (
        "fully" if percentage >= 80 else "partly" if percentage >= 50 else "failed"
    )
    return Classification(label, float(percentage))


def samples(directory: Path) -> list[Path]:
    selected = [directory.resolve() / f"ejercicio_{n}.jpeg" for n in range(1, 11)]
    for path in selected:
        if not path.is_file():
            raise FileNotFoundError(path)
    return selected


def create_command(
    settings: Settings, image_id: str, sample: Path, output: Path
) -> list[str]:
    return [
        "docker",
        "create",
        "--network",
        "none",
        "--cpus",
        str(settings.cpus),
        "--memory",
        f"{settings.memory_mb}m",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--env",
        f"JAVA_OPTS={settings.java_options}",
        "--mount",
        f"type=bind,source={sample.resolve()},target=/input/sample.jpeg,readonly",
        "--mount",
        f"type=bind,source={output.resolve()},target=/output",
        image_id,
        "-batch",
        "-transcribe",
        "-export",
        "-save",
        "-output",
        "/output",
        "--",
        "/input/sample.jpeg",
    ]


def run_sample(
    settings: Settings, image_id: str, sample: Path, output: Path
) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=False)
    command = create_command(settings, image_id, sample, output)
    result: dict[str, object] = {
        "sample": sample.name,
        "sha256": hashlib.sha256(sample.read_bytes()).hexdigest(),
        "command": command,
        "started_at": datetime.now(UTC).isoformat(),
        "timeout_seconds": settings.timeout_seconds,
    }
    created = subprocess.run(
        command, check=True, capture_output=True, text=True, timeout=30
    )
    container_id = created.stdout.strip()
    started = time.monotonic()
    try:
        with (output / "console.log").open("w") as log:
            subprocess.run(
                ["docker", "start", "--attach", container_id],
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=settings.timeout_seconds,
                check=False,
            )
        inspected = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.ExitCode}}", container_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        exit_code = int(inspected.stdout.strip())
        exports = sorted(
            str(path.relative_to(output))
            for path in output.rglob("*")
            if path.suffix.lower() in {".mxl", ".musicxml"}
        )
        result.update(
            exit_code=exit_code,
            exports=exports,
            outcome="exported" if exit_code == 0 and exports else "failed",
        )
    except subprocess.TimeoutExpired:
        LOGGER.error("Audiveris timed out for %s", sample.name)
        result.update(exit_code=None, exports=[], outcome="timed_out")
    finally:
        subprocess.run(
            ["docker", "rm", "--force", container_id],
            check=True,
            capture_output=True,
            timeout=30,
        )
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    (output / "run.json").write_text(json.dumps(result, indent=2) + "\n")
    if result["outcome"] != "exported":
        LOGGER.error("Recognition run failed: %s; see %s", sample.name, output)
    return result


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = Settings()
    selected = samples(settings.samples_dir)
    image = subprocess.run(
        ["docker", "image", "inspect", settings.image],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    image_id: str = json.loads(image.stdout)[0]["Id"]
    run_dir = settings.output_dir.resolve() / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "image.json").write_text(image.stdout)
    (run_dir / "settings.json").write_text(settings.model_dump_json(indent=2) + "\n")
    version = subprocess.run(
        ["docker", "version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    (run_dir / "docker-version.txt").write_text(version.stdout)
    audiveris = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--env",
            f"JAVA_OPTS={settings.java_options}",
            image_id,
            "-version",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    (run_dir / "audiveris-version.txt").write_text(audiveris.stdout)
    results = []
    for sample in selected:
        LOGGER.info("Processing %s", sample.name)
        results.append(run_sample(settings, image_id, sample, run_dir / sample.stem))
    (run_dir / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    LOGGER.info("Run artifacts: %s", run_dir)
    return 0 if all(result["outcome"] == "exported" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
