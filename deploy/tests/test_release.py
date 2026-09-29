import hashlib
import json
import tarfile
from pathlib import Path

import pytest
from release import build_release

SHA = "a" * 40
BACKEND = "ghcr.io/mordanov/solfeo-backend@sha256:" + "b" * 64
FRONTEND = "ghcr.io/mordanov/solfeo-frontend@sha256:" + "c" * 64
FILES = ("deploy/compose.prod.yaml", "deploy/postgres-init.sh", ".env.example")


@pytest.fixture
def source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    (root / "deploy").mkdir(parents=True)
    for name in FILES:
        (root / name).write_text(f"synthetic content for {name}\n")
    (root / "deploy/postgres-init.sh").chmod(0o755)
    (root / ".env").write_text("PRIVATE_CONTENT_NOT_FOR_RELEASE")
    (root / "unrelated.txt").write_text("not part of a deployment")
    return root


def bundle(
    source: Path,
    destination: Path,
    *,
    ci_run_id: int = 123,
    overrides: dict[str, str] | None = None,
) -> Path:
    arguments = {
        "repository": "mordanov/solfeo-exercises",
        "source_sha": SHA,
        "backend_image": BACKEND,
        "frontend_image": FRONTEND,
    }
    arguments.update(overrides or {})
    return build_release(
        root=source,
        destination=destination,
        ci_run_id=ci_run_id,
        repository=arguments["repository"],
        source_sha=arguments["source_sha"],
        backend_image=arguments["backend_image"],
        frontend_image=arguments["frontend_image"],
    )


def test_bundle_contains_only_hashed_deployment_files(
    source: Path, tmp_path: Path
) -> None:
    artifact = bundle(source, tmp_path / "output")
    with tarfile.open(artifact) as archive:
        assert set(archive.getnames()) == {*FILES, "release.json"}
        manifest_file = archive.extractfile("release.json")
        assert manifest_file is not None
        manifest = json.load(manifest_file)
        assert manifest == {
            "format_version": 1,
            "repository": "mordanov/solfeo-exercises",
            "source_sha": SHA,
            "ci_run_id": 123,
            "backend_image": BACKEND,
            "frontend_image": FRONTEND,
            "files": {
                name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                for name in FILES
            },
        }
        assert archive.getmember("deploy/postgres-init.sh").mode == 0o755
        assert all(
            member.uid == 0 and member.gid == 0 for member in archive.getmembers()
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"source_sha": "main"},
        {"source_sha": "a" * 39},
        {"repository": "../untrusted"},
        {"backend_image": "ghcr.io/mordanov/solfeo-backend:latest"},
        {"backend_image": "ghcr.io/another-owner/solfeo-backend@sha256:" + "b" * 64},
        {"frontend_image": BACKEND},
    ],
)
def test_invalid_provenance_is_rejected(
    source: Path, tmp_path: Path, overrides: dict[str, str]
) -> None:
    with pytest.raises(ValueError):
        bundle(source, tmp_path / "output", overrides=overrides)


def test_symlink_cannot_include_an_external_file(source: Path, tmp_path: Path) -> None:
    file = source / "deploy/compose.prod.yaml"
    file.unlink()
    file.symlink_to(source / ".env")
    with pytest.raises(ValueError, match="UNSAFE_RELEASE_FILE"):
        bundle(source, tmp_path / "output")


def test_missing_file_does_not_create_a_release(source: Path, tmp_path: Path) -> None:
    (source / "deploy/postgres-init.sh").unlink()
    destination = tmp_path / "output"
    with pytest.raises(FileNotFoundError):
        bundle(source, destination)
    assert not (destination / "solfeo-release.tar.gz").exists()


def test_an_existing_artifact_is_not_overwritten(source: Path, tmp_path: Path) -> None:
    destination = tmp_path / "output"
    artifact = bundle(source, destination)
    original = artifact.read_bytes()
    with pytest.raises(FileExistsError):
        bundle(source, destination)
    assert artifact.read_bytes() == original


def test_bootstrap_must_remain_executable(source: Path, tmp_path: Path) -> None:
    (source / "deploy/postgres-init.sh").chmod(0o644)
    with pytest.raises(ValueError, match="BOOTSTRAP_NOT_EXECUTABLE"):
        bundle(source, tmp_path / "output")


@pytest.mark.parametrize("run_id", [0, -1])
def test_ci_run_must_be_positive(source: Path, tmp_path: Path, run_id: int) -> None:
    with pytest.raises(ValueError, match="INVALID_CI_PROVENANCE"):
        bundle(source, tmp_path / "output", ci_run_id=run_id)
