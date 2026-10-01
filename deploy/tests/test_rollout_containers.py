"""Exercise the rollout state machine with real Docker and disposable local images."""

import json
import secrets
import shutil
import socket
import subprocess
import tempfile
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from release import build_release
from rollout import DeploymentError, Rollout

ROOT = Path(__file__).resolve().parents[2]
SHA = "a" * 40


class LocalImagesRollout(Rollout):
    """Use CI-built images instead of publishing disposable test releases."""

    failure: str | None = None
    candidate: Path | None = None

    def disk_free(self) -> dict[str, int]:
        if shutil.which("colima") and not Path("/var/lib/docker").is_dir():
            result = subprocess.run(
                [
                    "colima",
                    "ssh",
                    "--",
                    "df",
                    "-B1",
                    "--output=avail",
                    "/var/lib/docker",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return {
                "docker": int(result.stdout.splitlines()[-1]),
                "release": shutil.disk_usage(self.root).free,
            }
        return super().disk_free()

    def activate(self, candidate: Path, previous: Path | None) -> None:
        self.candidate = candidate
        (candidate / "images.env").write_text(
            "BACKEND_IMAGE=solfeo-dev-backend\nFRONTEND_IMAGE=solfeo-dev-frontend\n"
        )
        super().activate(candidate, previous)

    def compose(self, release: Path, *args: str) -> str:
        if args == ("pull",):
            subprocess.run(
                [
                    "docker",
                    "image",
                    "inspect",
                    "solfeo-dev-backend",
                    "solfeo-dev-frontend",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            return ""
        if (
            release == self.candidate
            and self.failure == "migration"
            and "upgrade" in args
        ):
            return super().compose(
                release,
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "migrate",
                "python",
                "-c",
                "raise SystemExit(17)",
            )
        try:
            return super().compose(release, *args)
        except DeploymentError as error:
            output = (self.root / "last-error.log").read_text()
            for line in (self.root / ".env.production").read_text().splitlines():
                if "PASSWORD=" in line:
                    output = output.replace(line.split("=", 1)[1], "[redacted]")
            raise DeploymentError(f"{error}\n{output}") from error

    def verify(self, release: Path) -> None:
        super().verify(release)
        if release == self.candidate and self.failure == "health":
            raise DeploymentError("INJECTED_HEALTH_FAILURE")


@pytest.fixture
def rollout_root() -> Iterator[Path]:
    # Colima shares the repository, but not macOS's default pytest temp directory.
    (ROOT / ".pytest_cache").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="rollout-", dir=ROOT / ".pytest_cache"
    ) as path:
        yield Path(path)


@pytest.fixture
def rollout(rollout_root: Path) -> Iterator[LocalImagesRollout]:
    tmp_path = rollout_root
    project = "solfeo-rollout-check-" + uuid.uuid4().hex[:12]
    network = project + "-proxy"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    config = tmp_path / ".env.production"
    config.touch(mode=0o600)
    config.write_text(
        f"DATABASE_PASSWORD={secrets.token_hex(32)}\n"
        f"MIGRATION_DATABASE_PASSWORD={secrets.token_hex(32)}\n"
        f"POSTGRES_ADMIN_PASSWORD={secrets.token_hex(32)}\n"
        f"PRODUCTION_WEB_PORT={port}\nPRODUCTION_PROXY_NETWORK={network}\n"
        "OMR_ENABLED=false\n"
        "DEPLOY_IMAGE_BUDGET_MB=128\nDEPLOY_DISK_RESERVE_MB=64\n"
    )
    instance = LocalImagesRollout(tmp_path, project, True, f"http://127.0.0.1:{port}")
    subprocess.run(
        ["docker", "network", "create", network], check=True, capture_output=True
    )
    try:
        yield instance
    finally:
        try:
            if instance.candidate:
                instance.compose(
                    instance.candidate, "down", "--volumes", "--remove-orphans"
                )
        finally:
            subprocess.run(
                ["docker", "network", "rm", network], check=True, capture_output=True
            )
            config.unlink()


def publish(root: Path, run_id: int) -> Path:
    return build_release(
        root=ROOT,
        destination=root / f"artifact-{run_id}",
        repository="mordanov/solfeo-exercises",
        source_sha=SHA,
        ci_run_id=run_id,
        backend_image="ghcr.io/mordanov/solfeo-backend@sha256:" + "a" * 64,
        frontend_image="ghcr.io/mordanov/solfeo-frontend@sha256:" + "b" * 64,
    )


def test_real_deployment_and_failed_update_rollback(
    rollout: LocalImagesRollout,
) -> None:
    rollout.deploy(publish(rollout.root, 1), SHA, 1)
    first = rollout.state()["current"]
    assert first is not None
    initial = rollout.root / "releases" / first
    postgres = rollout.compose(initial, "ps", "-q", "postgres").strip()
    network = rollout.project + "-proxy"
    attached = subprocess.run(
        ["docker", "network", "inspect", network],
        check=True,
        capture_output=True,
        text=True,
    )
    members = json.loads(attached.stdout)[0]["Containers"]
    assert len(members) == 1
    assert next(iter(members.values()))["Name"].endswith("-frontend-1")

    class NoSpace(LocalImagesRollout):
        def disk_free(self) -> dict[str, int]:
            return {"docker": 0, "release": 0}

    before = rollout.compose(initial, "ps", "-q").splitlines()
    blocked = NoSpace(rollout.root, rollout.project, True, rollout.health_url)
    with pytest.raises(DeploymentError, match="DEPLOY_DISK_INSUFFICIENT"):
        blocked.deploy(publish(rollout.root, 5), SHA, 5)
    assert rollout.state()["current"] == first
    assert rollout.compose(initial, "ps", "-q").splitlines() == before
    rollout.verify(initial)

    for run_id, failure in ((2, "migration"), (3, "health")):
        rollout.failure = failure
        with pytest.raises(DeploymentError, match="DEPLOY_FAILED_ROLLED_BACK"):
            rollout.deploy(publish(rollout.root, run_id), SHA, run_id)
        assert rollout.state()["current"] == first
        assert rollout.compose(initial, "ps", "-q", "postgres").strip() == postgres
        rollout.verify(initial)
    rollout.failure = None
    rollout.deploy(publish(rollout.root, 4), SHA, 4)
    assert rollout.state()["previous"] == first
    assert rollout.state()["current"] != first
