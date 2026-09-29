"""Deploy a verified release on the host without touching unrelated services."""

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TypedDict

from release import RELEASE_FILES


class DeploymentError(RuntimeError):
    pass


class Manifest(TypedDict):
    source_sha: str
    backend_image: str
    frontend_image: str


def verify_bundle(
    artifact: Path, expected_sha: str, ci_run_id: int
) -> tuple[Manifest, dict[str, bytes]]:
    if artifact.stat().st_size > 1024 * 1024:
        raise DeploymentError("RELEASE_TOO_LARGE")
    files: dict[str, bytes] = {}
    with tarfile.open(artifact, "r:gz") as archive:
        for member in archive:
            if (
                member.name not in {*RELEASE_FILES, "release.json"}
                or member.name in files
                or not member.isfile()
                or member.size > 1024 * 1024
            ):
                raise DeploymentError("UNSAFE_RELEASE_ARCHIVE")
            stream = archive.extractfile(member)
            if stream is None:
                raise DeploymentError("MISSING_RELEASE_CONTENT")
            files[member.name] = stream.read()
    if set(files) != {*RELEASE_FILES, "release.json"}:
        raise DeploymentError("INCOMPLETE_RELEASE")
    data = json.loads(files["release.json"])
    if (
        not isinstance(data, dict)
        or data.get("format_version") != 1
        or data.get("repository") != "mordanov/solfeo-exercises"
        or data.get("source_sha") != expected_sha
        or not re.fullmatch(r"[a-f0-9]{40}", expected_sha)
        or data.get("ci_run_id") != ci_run_id
        or ci_run_id <= 0
    ):
        raise DeploymentError("INVALID_RELEASE_PROVENANCE")
    hashes = data.get("files")
    if not isinstance(hashes, dict) or set(hashes) != set(RELEASE_FILES):
        raise DeploymentError("INVALID_RELEASE_HASHES")
    for name in RELEASE_FILES:
        if hashes[name] != hashlib.sha256(files[name]).hexdigest():
            raise DeploymentError("RELEASE_HASH_MISMATCH")
    images: dict[str, str] = {}
    for service in ("backend", "frontend"):
        reference = data.get(f"{service}_image")
        if not isinstance(reference, str) or not re.fullmatch(
            rf"ghcr\.io/mordanov/solfeo-{service}@sha256:[a-f0-9]{{64}}", reference
        ):
            raise DeploymentError("INVALID_IMAGE_REFERENCE")
        images[service] = reference
    return {
        "source_sha": expected_sha,
        "backend_image": images["backend"],
        "frontend_image": images["frontend"],
    }, files


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    temporary = path.with_name(path.name + ".tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, mode)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class Rollout:
    def __init__(self, root: Path, project: str, proxy: bool, health_url: str) -> None:
        self.root = root.resolve()
        if not re.fullmatch(r"solfeo-[a-z0-9-]+", project):
            raise DeploymentError("INVALID_COMPOSE_PROJECT")
        self.project = project
        self.proxy = proxy
        self.health_url = health_url.rstrip("/")

    def state(self) -> dict[str, str | None]:
        path = self.root / "state.json"
        if not path.exists():
            return {"current": None, "previous": None}
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or set(data) != {"current", "previous"}:
            raise DeploymentError("INVALID_DEPLOYMENT_STATE")
        result: dict[str, str | None] = {}
        for key in ("current", "previous"):
            value = data[key]
            if value is not None and (
                not isinstance(value, str) or not re.fullmatch("[a-f0-9]{64}", value)
            ):
                raise DeploymentError("INVALID_DEPLOYMENT_STATE")
            result[key] = value
        return result

    def compose(self, release: Path, *args: str) -> str:
        compose = (
            ["docker-compose"]
            if shutil.which("docker-compose")
            else ["docker", "compose"]
        )
        command = [
            *compose,
            "--project-name",
            self.project,
            "--project-directory",
            str(self.root / "runtime" / "deploy"),
            "--env-file",
            str(self.root / ".env.production"),
            "--env-file",
            str(release / "images.env"),
            "-f",
            str(release / "deploy" / "compose.prod.yaml"),
        ]
        if self.proxy:
            command.extend(["-f", str(release / "deploy" / "compose.proxy.yaml")])
        environment = dict(os.environ)
        # The server configuration and verified manifest override caller variables.
        for key in list(environment):
            if (
                key.startswith(
                    (
                        "DATABASE_",
                        "MIGRATION_",
                        "POSTGRES_",
                        "PRODUCTION_",
                        "API_",
                        "AUTH_",
                        "SESSION_",
                        "PASSWORD_",
                        "LOGIN_",
                        "EMERGENCY_MANAGER_",
                    )
                )
                or key == "DEFAULT_LANGUAGE"
            ):
                environment.pop(key)
        environment.pop("BACKEND_IMAGE", None)
        environment.pop("FRONTEND_IMAGE", None)
        result = subprocess.run(
            [*command, *args],
            env=environment,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode:
            # Resolved credentials can appear in diagnostics; keep them off CI logs.
            atomic_write(
                self.root / "last-error.log",
                (result.stdout + result.stderr).encode(),
            )
            raise DeploymentError(
                f"COMPOSE_FAILED:{args[0]}:{result.returncode}:SEE_PRIVATE_LAST_ERROR_LOG"
            )
        return result.stdout

    def verify(self, release: Path) -> None:
        self.compose(
            release,
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "migrate",
            "alembic",
            "-c",
            "backend/alembic.ini",
            "current",
            "--check-heads",
        )
        for attempt in range(15):
            try:
                with urllib.request.urlopen(
                    self.health_url + "/api/health", timeout=5
                ) as response:
                    try:
                        payload = json.load(response)
                    except (ValueError, UnicodeError) as error:
                        raise DeploymentError("INVALID_HEALTH_RESPONSE") from error
                    if response.status != 200 or payload != {"status": "ok"}:
                        raise DeploymentError("INVALID_HEALTH_RESPONSE")
                with urllib.request.urlopen(
                    self.health_url + "/", timeout=5
                ) as response:
                    if response.status != 200 or b'id="root"' not in response.read():
                        raise DeploymentError("INVALID_FRONTEND_RESPONSE")
                return
            except (urllib.error.URLError, TimeoutError):
                if attempt == 14:
                    raise DeploymentError("HTTP_HEALTH_FAILED") from None
                time.sleep(2)

    def promote(self, release: Path) -> None:
        state = self.state()
        if state["current"] == release.name:
            return
        atomic_write(
            self.root / "state.json",
            json.dumps(
                {"current": release.name, "previous": state["current"]}
            ).encode(),
        )

    def activate(self, candidate: Path, previous: Path | None) -> None:
        self.compose(candidate, "config", "--quiet")
        self.compose(candidate, "pull")
        self.compose(candidate, "up", "-d", "--no-deps", "--wait", "postgres")
        self.compose(candidate, "stop", "frontend", "backend")
        try:
            self.compose(
                candidate,
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "migrate",
                "alembic",
                "-c",
                "backend/alembic.ini",
                "upgrade",
                "head",
            )
            self.compose(
                candidate, "up", "-d", "--no-deps", "--wait", "backend", "frontend"
            )
            self.verify(candidate)
        except (DeploymentError, subprocess.TimeoutExpired) as error:
            self.compose(candidate, "stop", "frontend", "backend")
            if previous is None:
                raise DeploymentError("FIRST_DEPLOY_FAILED_SERVICES_STOPPED") from error
            try:
                self.compose(
                    previous,
                    "run",
                    "--rm",
                    "--no-deps",
                    "-T",
                    "migrate",
                    "alembic",
                    "-c",
                    "backend/alembic.ini",
                    "current",
                    "--check-heads",
                )
                self.compose(
                    previous, "up", "-d", "--no-deps", "--wait", "backend", "frontend"
                )
                self.verify(previous)
            except (DeploymentError, subprocess.TimeoutExpired) as rollback_error:
                self.compose(previous, "stop", "frontend", "backend")
                raise DeploymentError(
                    "ROLLBACK_FAILED_MANUAL_RECOVERY_REQUIRED"
                ) from rollback_error
            raise DeploymentError("DEPLOY_FAILED_ROLLED_BACK") from error
        self.promote(candidate)

    def deploy(self, artifact: Path, expected_sha: str, ci_run_id: int) -> None:
        manifest, files = verify_bundle(artifact, expected_sha, ci_run_id)
        config = self.root / ".env.production"
        if not config.is_file() or config.stat().st_mode & 0o077:
            raise DeploymentError("PRIVATE_SERVER_CONFIGURATION_REQUIRED")
        release = (
            self.root / "releases" / hashlib.sha256(artifact.read_bytes()).hexdigest()
        )
        release.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            path = release / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.read_bytes() != content:
                raise DeploymentError("EXISTING_RELEASE_CHANGED")
            atomic_write(path, content, 0o755 if name.endswith(".sh") else 0o600)
        atomic_write(
            release / "images.env",
            (
                f"BACKEND_IMAGE={manifest['backend_image']}\n"
                f"FRONTEND_IMAGE={manifest['frontend_image']}\n"
            ).encode(),
        )
        bootstrap = self.root / "runtime" / "deploy" / "postgres-init.sh"
        bootstrap.parent.mkdir(parents=True, exist_ok=True)
        content = files["deploy/postgres-init.sh"]
        if bootstrap.exists() and bootstrap.read_bytes() != content:
            raise DeploymentError("BOOTSTRAP_CHANGE_REQUIRES_OPERATOR_REVIEW")
        if not bootstrap.exists():
            atomic_write(bootstrap, content, 0o755)
        current = self.state()["current"]
        previous = self.root / "releases" / current if current else None
        self.activate(release, previous)
        print(f"DEPLOYED:{expected_sha}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--ci-run-id", type=int, required=True)
    parser.add_argument("--project", default="solfeo-production")
    parser.add_argument("--proxy", action="store_true")
    parser.add_argument("--health-url", default="http://127.0.0.1:18090")
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (args.root / "deploy.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("DEPLOYMENT_ALREADY_RUNNING") from None
        try:
            Rollout(args.root, args.project, args.proxy, args.health_url).deploy(
                args.bundle, args.source_sha, args.ci_run_id
            )
        except (DeploymentError, subprocess.TimeoutExpired) as error:
            raise SystemExit(
                str(error)
                if isinstance(error, DeploymentError)
                else "DEPLOYMENT_TIMEOUT"
            ) from None


if __name__ == "__main__":
    main()
