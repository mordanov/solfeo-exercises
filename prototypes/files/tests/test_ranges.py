import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app import Settings

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope="module")
def evidence(settings: Settings) -> Path:
    path = settings.output_dir / (
        "curl-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    )
    path.mkdir(parents=True, exist_ok=False)
    print(f"\nCurl evidence: {path.resolve()}")
    return path


@pytest.mark.parametrize(
    ("name", "path", "authenticated", "range_header", "head", "expected_status"),
    [
        ("full", "/api/audio", True, None, False, 200),
        ("head", "/api/audio", True, None, True, 200),
        ("first-two", "/api/audio", True, "bytes=0-1", False, 206),
        ("middle", "/api/audio", True, "bytes=100-199", False, 206),
        ("suffix", "/api/audio", True, "bytes=-128", False, 206),
        ("open-end", "/api/audio", True, "open-end", False, 206),
        ("head-range", "/api/audio", True, "bytes=0-1", True, 206),
        ("unsatisfiable", "/api/audio", True, "unsatisfiable", False, 416),
        ("anonymous", "/api/audio", False, None, False, 401),
        ("anonymous-range", "/api/audio", False, "bytes=0-1", False, 401),
        ("wrong-password", "/api/audio", True, "bytes=0-1", False, 401),
        ("direct", "/_protected/sample.m4a", True, None, False, 404),
        ("direct-anonymous", "/_protected/sample.m4a", False, None, False, 404),
    ],
)
def test_actual_nginx_response(
    settings: Settings,
    evidence: Path,
    name: str,
    path: str,
    authenticated: bool,
    range_header: str | None,
    head: bool,
    expected_status: int,
) -> None:
    sample = (settings.media_dir / "sample.m4a").read_bytes()
    size = len(sample)
    assert size > 1024
    if range_header == "open-end":
        range_header = f"bytes={size - 128}-"
    elif range_header == "unsatisfiable":
        range_header = f"bytes={size}-"
    headers_path = evidence / f"{name}.headers"
    body_path = evidence / f"{name}.body"
    command = [
        "curl",
        "--silent",
        "--show-error",
        "--max-time",
        "15",
        "--dump-header",
        str(headers_path),
        "--output",
        str(body_path),
        "--write-out",
        "%{http_code} %{size_download}",
    ]
    if head:
        command.append("--head")
    if range_header:
        command += ["--header", f"Range: {range_header}"]
    auth_config = ""
    if authenticated:
        password = (
            "deliberately-wrong"
            if name == "wrong-password"
            else settings.password.get_secret_value()
        )
        auth_config = f"user = {json.dumps(settings.username + ':' + password)}\n"
        command += ["--basic", "--config", "-"]
    command.append(f"http://127.0.0.1:{settings.port}{path}")
    response = subprocess.run(
        command,
        input=auth_config,
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    status_text, downloaded_text = response.stdout.split()
    status = int(status_text)
    downloaded_bytes = int(float(downloaded_text))
    raw_headers = headers_path.read_text()
    headers = {
        key.lower(): value.strip()
        for line in raw_headers.splitlines()
        if ": " in line
        for key, value in [line.split(": ", 1)]
    }
    body = body_path.read_bytes()
    record = {
        "command": command,
        "credentials": "stdin only; not recorded",
        "status": status,
        "expected_status": expected_status,
        "headers": headers,
        "downloaded_bytes": downloaded_bytes,
    }
    (evidence / f"{name}.json").write_text(json.dumps(record, indent=2) + "\n")
    assert status == expected_status
    assert "x-accel-redirect" not in headers
    assert downloaded_bytes == (0 if head else len(body))
    if status in {200, 206}:
        assert headers["content-type"] == "audio/mp4"
        assert "no-store" in headers["cache-control"]
        if status == 200:
            assert headers["content-length"] == str(size)
            assert headers["accept-ranges"] == "bytes"
            if not head:
                assert body == sample
        else:
            start, end = (
                (0, 1)
                if name in {"first-two", "head-range"}
                else (100, 199)
                if name == "middle"
                else (size - 128, size - 1)
            )
            assert headers["content-range"] == f"bytes {start}-{end}/{size}"
            assert headers["content-length"] == str(end - start + 1)
            if not head:
                assert body == sample[start : end + 1]
    elif status == 416:
        assert headers["content-range"] == f"bytes */{size}"
    elif status == 401:
        assert headers["www-authenticate"].startswith("Basic ")
        assert json.loads(body) == {"error": "AUTH_REQUIRED"}
