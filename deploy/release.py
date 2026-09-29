"""Package the deployment files for a CI-approved pair of images."""

import argparse
import hashlib
import io
import json
import re
import tarfile
import tempfile
from pathlib import Path

RELEASE_FILES = ("deploy/compose.prod.yaml", "deploy/postgres-init.sh", ".env.example")


def build_release(
    *,
    root: Path,
    destination: Path,
    repository: str,
    source_sha: str,
    ci_run_id: int,
    backend_image: str,
    frontend_image: str,
) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9._-]*", repository):
        raise ValueError("INVALID_REPOSITORY")
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha) or ci_run_id <= 0:
        raise ValueError("INVALID_CI_PROVENANCE")
    owner = repository.split("/")[0]
    for name, reference in (("backend", backend_image), ("frontend", frontend_image)):
        prefix = re.escape(f"ghcr.io/{owner}/solfeo-{name}@sha256:")
        if not re.fullmatch(prefix + r"[0-9a-f]{64}", reference):
            raise ValueError("IMMUTABLE_PRODUCT_IMAGE_REQUIRED")

    root = root.resolve()
    files: dict[str, bytes] = {}
    for name in RELEASE_FILES:
        path = root / name
        if path.is_symlink() or path.resolve() != path:
            raise ValueError("UNSAFE_RELEASE_FILE")
        files[name] = path.read_bytes()
    if not (root / "deploy/postgres-init.sh").stat().st_mode & 0o111:
        raise ValueError("BOOTSTRAP_NOT_EXECUTABLE")

    manifest: dict[str, object] = {
        "format_version": 1,
        "repository": repository,
        "source_sha": source_sha,
        "ci_run_id": ci_run_id,
        "backend_image": backend_image,
        "frontend_image": frontend_image,
        "files": {
            name: hashlib.sha256(content).hexdigest() for name, content in files.items()
        },
    }
    files["release.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode()
    destination.mkdir(parents=True, exist_ok=True)
    artifact = destination / "solfeo-release.tar.gz"
    with tempfile.NamedTemporaryFile(dir=destination, delete=False) as staged:
        temporary = Path(staged.name)
        try:
            with tarfile.open(fileobj=staged, mode="w:gz") as archive:
                for name, content in files.items():
                    member = tarfile.TarInfo(name)
                    member.size = len(content)
                    member.mode = 0o755 if name.endswith(".sh") else 0o644
                    archive.addfile(member, io.BytesIO(content))
            staged.flush()
            artifact.hardlink_to(temporary)
        finally:
            temporary.unlink()
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--ci-run-id", type=int, required=True)
    parser.add_argument("--backend-image", required=True)
    parser.add_argument("--frontend-image", required=True)
    arguments = parser.parse_args()
    artifact = build_release(
        root=arguments.root,
        destination=arguments.destination,
        repository=arguments.repository,
        source_sha=arguments.source_sha,
        ci_run_id=arguments.ci_run_id,
        backend_image=arguments.backend_image,
        frontend_image=arguments.frontend_image,
    )
    print(artifact)


if __name__ == "__main__":
    main()
