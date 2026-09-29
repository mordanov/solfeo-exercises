import io
import json
import tarfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from release import build_release
from rollout import DeploymentError, Rollout, verify_bundle

SHA = "d" * 40


@pytest.fixture
def artifact(tmp_path: Path) -> Path:
    root = Path(__file__).resolve().parents[2]
    return build_release(
        root=root,
        destination=tmp_path / "artifact",
        repository="mordanov/solfeo-exercises",
        source_sha=SHA,
        ci_run_id=12,
        backend_image="ghcr.io/mordanov/solfeo-backend@sha256:" + "a" * 64,
        frontend_image="ghcr.io/mordanov/solfeo-frontend@sha256:" + "b" * 64,
    )


def test_valid_bundle_checks_exact_provenance(artifact: Path) -> None:
    manifest, files = verify_bundle(artifact, SHA, 12)
    assert manifest["source_sha"] == SHA
    assert "deploy/compose.prod.yaml" in files


@pytest.mark.parametrize("sha,run_id", [("e" * 40, 12), (SHA, 13)])
def test_wrong_provenance_fails(artifact: Path, sha: str, run_id: int) -> None:
    with pytest.raises(DeploymentError):
        verify_bundle(artifact, sha, run_id)


@pytest.mark.parametrize("kind", ["changed", "traversal", "duplicate", "symlink"])
def test_unsafe_archive_fails(artifact: Path, tmp_path: Path, kind: str) -> None:
    bad = tmp_path / "bad.tar.gz"
    with tarfile.open(artifact) as source, tarfile.open(bad, "w:gz") as target:
        for member in source.getmembers():
            content = source.extractfile(member)
            assert content is not None
            data = content.read()
            if member.name == "deploy/compose.prod.yaml" and kind == "changed":
                data = b"changed"
                member.size = len(data)
            target.addfile(member, io.BytesIO(data))
        if kind in {"traversal", "duplicate", "symlink"}:
            member = tarfile.TarInfo(
                "../.env.production" if kind == "traversal" else "release.json"
            )
            if kind == "symlink":
                member.type = tarfile.SYMTYPE
                member.linkname = "/etc/passwd"
            target.addfile(member)
    with pytest.raises(DeploymentError):
        verify_bundle(bad, SHA, 12)


class FakeRollout(Rollout):
    """Model Docker as an external system for rollback ordering tests."""

    def __init__(self, root: Path, fail: str | None = None) -> None:
        super().__init__(root, "solfeo-test", False, "http://127.0.0.1:18090")
        self.calls: list[str] = []
        self.fail = fail
        self.candidate = root / "releases" / ("a" * 64)

    def compose(self, release: Path, *args: str) -> str:
        label = "candidate" if release == self.candidate else "previous"
        operation = f"{label}:{' '.join(args)}"
        self.calls.append(operation)
        if self.fail and self.fail in operation:
            raise DeploymentError("SYNTHETIC_FAILURE")
        return ""

    def verify(self, release: Path) -> None:
        self.calls.append("verify:" + release.name)
        if release == self.candidate and self.fail == "health":
            raise DeploymentError("HEALTH_FAILED")

    def promote(self, release: Path) -> None:
        self.calls.append("promote:" + release.name)


@pytest.mark.parametrize("failure", ["candidate:run", "health"])
def test_failed_release_restores_previous_without_downgrade(
    tmp_path: Path, failure: str
) -> None:
    rollout = FakeRollout(tmp_path, failure)
    previous = tmp_path / "releases" / ("b" * 64)
    with pytest.raises(DeploymentError, match="ROLLED_BACK"):
        rollout.activate(rollout.candidate, previous)
    assert any(
        "previous:run" in call and "--check-heads" in call for call in rollout.calls
    )
    assert any("previous:up" in call for call in rollout.calls)
    assert not any("downgrade" in call or "promote:" in call for call in rollout.calls)


def test_incompatible_previous_schema_stays_stopped(tmp_path: Path) -> None:
    class Incompatible(FakeRollout):
        def compose(self, release: Path, *args: str) -> str:
            if release != self.candidate and "--check-heads" in args:
                raise DeploymentError("SCHEMA_INCOMPATIBLE")
            return super().compose(release, *args)

    rollout = Incompatible(tmp_path, "health")
    with pytest.raises(DeploymentError, match="ROLLBACK_FAILED"):
        rollout.activate(rollout.candidate, tmp_path / "previous")
    assert not any("previous:up" in call for call in rollout.calls)


def test_first_install_failure_preserves_database(tmp_path: Path) -> None:
    rollout = FakeRollout(tmp_path, "health")
    with pytest.raises(DeploymentError, match="FIRST_DEPLOY_FAILED"):
        rollout.activate(rollout.candidate, None)
    assert not any("down" in call or "--volumes" in call for call in rollout.calls)


def test_state_promotion_is_atomic_and_retains_previous(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    root.mkdir()
    rollout = Rollout(root, "solfeo-test", False, "http://127.0.0.1:18090")
    previous = root / "releases" / ("a" * 64)
    candidate = root / "releases" / ("b" * 64)
    rollout.promote(previous)
    rollout.promote(candidate)
    state = json.loads((root / "state.json").read_text())
    assert state == {"current": candidate.name, "previous": previous.name}


def test_non_json_health_is_a_recoverable_deployment_failure(tmp_path: Path) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"not json")

        def log_message(self, format: str, *args: object) -> None:
            pass

    class NoDocker(Rollout):
        def compose(self, release: Path, *args: str) -> str:
            return ""

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        rollout = NoDocker(
            tmp_path, "solfeo-test", False, f"http://127.0.0.1:{server.server_port}"
        )
        with pytest.raises(DeploymentError, match="INVALID_HEALTH_RESPONSE"):
            rollout.verify(tmp_path)
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
