import http.cookiejar
import io
import json
import os
import secrets
import shutil
import socket
import subprocess
import urllib.request
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def test_development_migration_uses_the_same_backend_image() -> None:
    compose = (
        ["docker-compose"] if shutil.which("docker-compose") else ["docker", "compose"]
    )
    result = subprocess.run(
        [
            *compose,
            "--env-file",
            str(ROOT / ".env.example"),
            "-f",
            str(ROOT / "deploy/compose.yaml"),
            "config",
            "--format",
            "json",
        ],
        env={"PATH": os.environ["PATH"], "DATABASE_PASSWORD": "synthetic-password"},
        capture_output=True,
        text=True,
        check=True,
    )
    services = json.loads(result.stdout)["services"]
    assert (
        services["migrate"]["image"]
        == services["backend"]["image"]
        == "solfeo-dev-backend"
    )


@dataclass
class Stand:
    command: list[str]
    passwords: list[str] = field(repr=False)

    def run(
        self, *arguments: str, script: str | None = None, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [*self.command, *arguments],
            input=script,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=ROOT,
        )
        if check and result.returncode:
            output = result.stdout + result.stderr
            for password in self.passwords:
                output = output.replace(password, "[redacted]")
            pytest.fail(f"Compose exits with {result.returncode}:\n{output}")
        return result

    def python(self, service: str, script: str) -> str:
        if service == "migrate":
            result = self.run(
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "migrate",
                "python",
                "-",
                script=script,
            )
        else:
            result = self.run("exec", "-T", service, "python", "-", script=script)
        return result.stdout

    def health(self) -> None:
        address = self.run("port", "frontend", "8080").stdout.strip()
        assert address.startswith("127.0.0.1:")
        with urllib.request.urlopen(
            f"http://{address}/api/health", timeout=10
        ) as response:
            assert response.status == 200
            assert json.load(response) == {"status": "ok"}


@pytest.fixture(scope="module")
def stand(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Stand]:
    directory = tmp_path_factory.mktemp("production")
    compose = (
        ["docker-compose"] if shutil.which("docker-compose") else ["docker", "compose"]
    )
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    passwords = [secrets.token_hex(24) + "%:@/#" for _ in range(4)]
    values = {
        "BACKEND_IMAGE": "solfeo-dev-backend",
        "FRONTEND_IMAGE": "solfeo-dev-frontend",
        "DATABASE_NAME": "solfeo_production_test",
        "DATABASE_USER": "solfeo_app",
        "DATABASE_PASSWORD": passwords[0],
        "MIGRATION_DATABASE_USER": "solfeo_owner",
        "MIGRATION_DATABASE_PASSWORD": passwords[1],
        "POSTGRES_ADMIN_PASSWORD": passwords[2],
        "PRODUCTION_MIGRATION_SCHEMA": "migrations",
        "PRODUCTION_WEB_PORT": str(port),
        "AUTH_ALLOWED_ORIGINS": json.dumps([f"http://127.0.0.1:{port}"]),
        "SESSION_COOKIE_SECURE": "false",
        "EMERGENCY_MANAGER_USERNAME": "release-check",
        "EMERGENCY_MANAGER_PASSWORD": passwords[3],
        "LOGIN_NGINX_RATE_PER_SECOND": "1000",
        "LOGIN_NGINX_BURST": "1000",
    }
    environment = directory / ".env"
    environment.touch(mode=0o600)
    environment.write_text(
        "".join(f"{key}='{value}'\n" for key, value in values.items())
    )
    project = f"solfeo-prod-check-{uuid.uuid4().hex[:12]}"
    command = [
        *compose,
        "--project-name",
        project,
        "--env-file",
        str(environment),
        "-f",
        str(ROOT / "deploy" / "compose.prod.yaml"),
    ]
    instance = Stand(command, passwords)
    with pytest.MonkeyPatch.context() as patch:
        for key in values:
            patch.delenv(key, raising=False)
        try:
            instance.run("up", "-d", "--wait", "--wait-timeout", "120")
            yield instance
        finally:
            # This unique project contains only disposable integration-test data.
            try:
                instance.run("down", "--volumes", "--remove-orphans")
            finally:
                environment.unlink()


def test_runtime_roles_and_network_boundaries(stand: Stand) -> None:
    stand.health()
    assert not stand.run("port", "postgres", "5432", check=False).stdout.strip()
    assert not stand.run("port", "backend", "8000", check=False).stdout.strip()
    container = stand.run("ps", "-q", "backend").stdout.strip()
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            '{{range .Config.Env}}{{println (index (split . "=") 0)}}{{end}}',
            container,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    names = set(result.stdout.splitlines())
    assert "POSTGRES_PASSWORD" not in names
    assert "POSTGRES_ADMIN_PASSWORD" not in names
    assert "MIGRATION_DATABASE_PASSWORD" not in names

    stand.python(
        "migrate",
        """
from sqlalchemy import text
from app.database import Database
from app.settings import Settings
database = Database(Settings())
try:
    with database.engine.begin() as connection:
        version = connection.scalar(
            text("SELECT version_num FROM migrations.alembic_version")
        )
        assert version == "0004_listening"
        privileges = connection.execute(text(
            "SELECT rolsuper, rolcreatedb, rolcreaterole "
            "FROM pg_roles WHERE rolname=current_user"
        )).one()
        assert privileges == (False, False, False)
        connection.execute(text(
            "CREATE TABLE public._permission_probe "
            "(id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, "
            "value text NOT NULL)"
        ))
finally:
    database.close()
""",
    )
    try:
        stand.python(
            "backend",
            """
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from app.database import Database
from app.settings import Settings
database = Database(Settings())
try:
    with database.engine.begin() as connection:
        privileges = connection.execute(text(
            "SELECT rolsuper, rolcreatedb, rolcreaterole "
            "FROM pg_roles WHERE rolname=current_user"
        )).one()
        assert privileges == (False, False, False)
        assert not connection.scalar(text(
            "SELECT pg_has_role(current_user, 'solfeo_owner', 'MEMBER')"
        ))
        identifier = connection.scalar(text(
            "INSERT INTO public._permission_probe(value) "
            "VALUES ('synthetic') RETURNING id"
        ))
        assert identifier == 1
        connection.execute(text(
            "UPDATE public._permission_probe SET value='updated' WHERE id=1"
        ))
        value = connection.scalar(text(
            "SELECT value FROM public._permission_probe WHERE id=1"
        ))
        assert value == "updated"
        connection.execute(text("DELETE FROM public._permission_probe WHERE id=1"))
    for statement in [
        "CREATE TABLE public._forbidden (id int)",
        "ALTER TABLE public._permission_probe ADD COLUMN forbidden int",
        "DROP TABLE public._permission_probe",
        "SELECT * FROM migrations.alembic_version",
    ]:
        try:
            with database.engine.begin() as connection:
                connection.execute(text(statement))
        except ProgrammingError as error:
            assert error.orig.sqlstate == "42501"
        else:
            raise AssertionError("Runtime role unexpectedly has privileged access")
finally:
    database.close()
""",
        )
    finally:
        stand.python(
            "migrate",
            """
from sqlalchemy import text
from app.database import Database
from app.settings import Settings
database = Database(Settings())
try:
    with database.engine.begin() as connection:
        connection.execute(text("DROP TABLE public._permission_probe"))
finally:
    database.close()
""",
        )
    result = stand.run("logs", "--no-color")
    logs = result.stdout + result.stderr
    assert all(password not in logs for password in stand.passwords)


def test_revision_survives_restart(stand: Stand) -> None:
    stand.run("restart", "postgres")
    stand.run("up", "-d", "--wait", "postgres")
    stand.run(
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
    stand.run(
        "run",
        "--rm",
        "--no-deps",
        "-T",
        "migrate",
        "alembic",
        "-c",
        "backend/alembic.ini",
        "check",
    )
    stand.health()


def test_protected_media_ranges_persistence_and_soft_delete(stand: Stand) -> None:
    origin = "http://" + stand.run("port", "frontend", "8080").stdout.strip()
    image = io.BytesIO()
    Image.new("RGB", (24, 24), "white").save(image, "PNG")
    # Generate the fixture using the same installed ffmpeg, without host prerequisites.
    encoded = stand.python(
        "backend",
        """
import base64, subprocess, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "tone.opus"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                    "sine=duration=3", "-c:a", "libopus", str(path)],
                   check=True, timeout=15)
    print(base64.b64encode(path.read_bytes()).decode())
""",
    )
    import base64

    with httpx.Client(
        base_url=origin, headers={"Origin": origin}, timeout=30
    ) as client:
        signed_in = client.post(
            "/api/auth/login",
            json={
                "username": "release-check",
                "password": stand.passwords[3],
            },
        )
        assert signed_in.status_code == 200
        client.headers["X-CSRF-Token"] = signed_in.json()["csrf_token"]
        result = client.post(
            "/api/exercises",
            data={"title": "Container media check"},
            files={
                "image": ("score.txt", image.getvalue(), "text/plain"),
                "audio": ("sound.opus", base64.b64decode(encoded), "audio/ogg"),
            },
        )
        assert result.status_code == 201, result.text
        identifier = result.json()["id"]
        path = f"/api/exercises/{identifier}/files/audio"
        response = client.get(path)
        assert (
            response.status_code == 200
            and response.headers["content-type"] == "audio/mp4"
        )
        assert set(response.headers.get_list("cache-control", split_commas=True)) == {
            "no-store"
        }
        assert "x-accel-redirect" not in response.headers
        full = response.content
        partial = client.get(path, headers={"Range": "bytes=10-99"})
        assert partial.status_code == 206
        assert partial.content == full[10:100]
        assert partial.headers["content-range"] == f"bytes 10-99/{len(full)}"
        suffix = client.get(path, headers={"Range": "bytes=-32"})
        assert suffix.status_code == 206 and suffix.content == full[-32:]
        assert (
            client.get(path, headers={"Range": f"bytes={len(full) + 10}-"}).status_code
            == 416
        )
        assert client.head(path).headers["content-length"] == str(len(full))
        assert (
            client.get(f"/api/exercises/{identifier}/files/image").content
            == image.getvalue()
        )
        filename = response.headers["content-disposition"].split('"')[1]
        assert client.get("/_protected_media/" + filename).status_code == 404
        with httpx.Client(base_url=origin) as anonymous:
            assert (
                anonymous.get(path, headers={"Range": "bytes=0-9"}).status_code == 401
            )
        stand.run("restart", "backend", "frontend")
        stand.run("up", "-d", "--no-deps", "--wait", "backend", "frontend")
        signed_in = client.post(
            "/api/auth/login",
            json={
                "username": "release-check",
                "password": stand.passwords[3],
            },
        )
        client.headers["X-CSRF-Token"] = signed_in.json()["csrf_token"]
        assert client.get(path).content == full
        assert client.delete(f"/api/exercises/{identifier}").status_code == 200
        assert client.get(path).status_code == 404
    stand.python(
        "backend",
        f"""
from pathlib import Path
assert (Path("/app/media") / {filename!r}).is_file()
""",
    )


def test_authentication_through_real_nginx(stand: Stand) -> None:
    address = stand.run("port", "frontend", "8080").stdout.strip()
    origin = f"http://{address}"
    cookies = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))

    def request(
        path: str,
        body: dict[str, object] | None = None,
        csrf: str = "",
        method: str = "POST",
    ) -> dict[str, object]:
        data = json.dumps(body).encode() if body is not None else None
        with client.open(
            urllib.request.Request(
                origin + path,
                data=data,
                method=method,
                headers={
                    "Origin": origin,
                    "Content-Type": "application/json",
                    "X-CSRF-Token": csrf,
                },
            ),
            timeout=15,
        ) as response:
            result: object = json.load(response)
            assert isinstance(result, dict)
            return result

    signed_in = request(
        "/api/auth/login", {"username": "release-check", "password": stand.passwords[3]}
    )
    csrf = signed_in["csrf_token"]
    assert isinstance(csrf, str)
    me = request("/api/auth/me", method="GET")
    assert isinstance(me["user"], dict) and me["user"]["is_emergency"] is True
    user = request(
        "/api/users",
        {
            "username": "release-student",
            "password": stand.passwords[3],
            "first_name": "Release",
            "last_name": "Student",
            "role": "student",
            "must_change_password": False,
        },
        csrf,
    )
    assert user["role"] == "student"
    request("/api/auth/logout", {}, csrf)
    signed_in = request(
        "/api/auth/login",
        {"username": "release-student", "password": stand.passwords[3]},
    )
    csrf = signed_in["csrf_token"]
    assert isinstance(csrf, str)
    settings = request(
        "/api/settings", {"ui_language": "es", "note_naming": "solfege"}, csrf, "PATCH"
    )
    assert settings["ui_language"] == "es"
    try:
        request("/api/users", method="GET")
    except urllib.error.HTTPError as error:
        assert error.code == 403
    else:
        pytest.fail("Student accessed manager API")
    for route in (
        "/login",
        "/settings",
        "/manager/users",
        "/manager/journal",
        "/student",
    ):
        with client.open(origin + route) as response:
            assert b'id="root"' in response.read()
    stand.run("restart", "backend")
    stand.run("up", "-d", "--no-deps", "--wait", "backend")
    restored = request("/api/auth/me", method="GET")
    assert isinstance(restored["user"], dict)
    assert restored["user"]["ui_language"] == "es"
    assert restored["user"]["note_naming"] == "solfege"
    request("/api/auth/logout", {}, csrf)


def test_listening_journal_through_nginx_and_restart(stand: Stand) -> None:
    import wave

    audio = io.BytesIO()
    with wave.open(audio, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(bytes(8000 * 2 * 10))
    origin = "http://" + stand.run("port", "frontend", "8080").stdout.strip()
    with httpx.Client(
        base_url=origin, headers={"Origin": origin}, timeout=30
    ) as client:

        def login_as(username: str) -> str:
            response = client.post(
                "/api/auth/login",
                json={"username": username, "password": stand.passwords[3]},
            )
            assert response.status_code == 200
            return str(response.json()["csrf_token"])

        csrf = login_as("release-check")
        exercises = []
        for title in ("Complete audio", "Interrupted audio"):
            response = client.post(
                "/api/exercises",
                data={"title": title},
                files={"audio": ("tone.wav", audio.getvalue(), "audio/wav")},
                headers={"X-CSRF-Token": csrf},
            )
            assert response.status_code == 201
            exercises.append(response.json())
        created = client.post(
            "/api/users",
            json={
                "username": "journal-student",
                "password": stand.passwords[3],
                "first_name": "Journal",
                "last_name": "Student",
                "role": "student",
                "must_change_password": False,
            },
            headers={"X-CSRF-Token": csrf},
        )
        assert created.status_code == 201
        student_id = created.json()["id"]
        csrf = login_as("journal-student")
        assert client.get("/api/journal").status_code == 403
        for index, exercise in enumerate(exercises):
            payload = {
                "session_id": str(uuid.uuid4()),
                "exercise_id": exercise["id"],
                "audio_id": exercise["audio"]["id"],
                "event": "start",
                "position_seconds": 0,
                "csrf_token": csrf,
            }
            assert client.post("/api/listening/events", json=payload).status_code == 200
            payload.update(
                event="heartbeat",
                position_seconds=exercise["audio"]["duration_seconds"]
                * (0.9 if index == 0 else 0.1),
            )
            assert client.post("/api/listening/events", json=payload).status_code == 200
            if index == 0:
                payload["event"] = "end"
                assert (
                    client.post("/api/listening/events", json=payload).status_code
                    == 200
                )
        stand.run("restart", "backend")
        stand.run("up", "-d", "--no-deps", "--wait", "backend")
        assert client.get("/api/auth/me").status_code == 200
        assert (
            client.get("/api/listening/current").json()["exercise"]["id"]
            == exercises[1]["id"]
        )
        csrf = login_as("release-check")
        assert (
            client.delete(
                f"/api/exercises/{exercises[1]['id']}", headers={"X-CSRF-Token": csrf}
            ).status_code
            == 200
        )
        result = client.get(f"/api/journal?student_id={student_id}").json()
        assert result["total"] == 2
        complete = next(
            row
            for row in result["sessions"]
            if row["exercise_id"] == exercises[0]["id"]
        )
        interrupted = next(
            row
            for row in result["sessions"]
            if row["exercise_id"] == exercises[1]["id"]
        )
        assert complete["completed"] and complete["ended_at"]
        assert not interrupted["completed"] and interrupted["ended_at"] is None
        assert interrupted["exercise_deleted"]
        assert (
            client.get(f"/api/journal?student_id={student_id}&offset=1&limit=1").json()[
                "total"
            ]
            == 2
        )


def test_nginx_login_limit_ignores_client_forwarded_for(
    stand: Stand, tmp_path: Path
) -> None:
    override = tmp_path / "login-limit.yaml"
    override.write_text(
        "services:\n  frontend:\n    environment:\n"
        '      LOGIN_NGINX_RATE_PER_SECOND: "1"\n      LOGIN_NGINX_BURST: "1"\n'
    )
    limited = Stand([*stand.command, "-f", str(override)], stand.passwords)
    try:
        limited.run("up", "-d", "--no-deps", "--wait", "frontend")
        origin = "http://" + limited.run("port", "frontend", "8080").stdout.strip()
        statuses: list[int] = []
        for index in range(8):
            request = urllib.request.Request(
                origin + "/api/auth/login",
                data=json.dumps(
                    {"username": f"throttle-{index}", "password": "incorrect"}
                ).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Origin": origin,
                    "X-Forwarded-For": f"192.0.2.{index}",
                },
            )
            try:
                urllib.request.urlopen(request, timeout=10).close()
            except urllib.error.HTTPError as error:
                statuses.append(error.code)
                if error.code == 429:
                    assert error.headers.get("Retry-After") is None
                    assert json.load(error) == {"error": "RATE_LIMITED"}
        assert 401 in statuses and 429 in statuses
    finally:
        stand.run("up", "-d", "--no-deps", "--wait", "frontend")


def test_failed_migration_blocks_backend_start(stand: Stand, tmp_path: Path) -> None:
    override = tmp_path / "failure.yaml"
    override.write_text(
        'services:\n  migrate:\n    command: ["python", "-c", "raise SystemExit(17)"]\n'
    )
    stand.run("stop", "backend")
    failed = Stand([*stand.command, "-f", str(override)], stand.passwords)
    try:
        result = failed.run("up", "-d", "backend", check=False)
        assert result.returncode != 0
        assert not stand.run(
            "ps", "--status", "running", "-q", "backend"
        ).stdout.strip()
    finally:
        stand.run("up", "-d", "--wait")
    stand.health()
