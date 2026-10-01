import io
import json
import math
import struct
import wave
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from app.settings import Settings
from worker.generate_spoken import GenerationError, generate, verify, vocabulary


def test_committed_speech_assets() -> None:
    root = Path(__file__).resolve().parents[2]
    output = root / "frontend/public/solfege"
    settings = Settings(
        _env_file=root / ".env.example",
        database_password=SecretStr("unused"),
        spoken_output=output,
    )
    verify(settings)


def test_vocabulary_has_every_language_naming_and_accidental() -> None:
    entries = vocabulary()
    assert len(entries) == 66
    assert len({entry.path for entry in entries}) == 66
    assert {entry.language for entry in entries} == {"en", "ru", "es"}
    assert all(".." not in entry.path for entry in entries)


def test_missing_key_does_not_create_fake_clips(tmp_path: Path) -> None:
    settings = Settings(
        database_password=SecretStr("unused"),
        openai_api_key=SecretStr(""),
        spoken_output=tmp_path,
    )
    with (
        httpx.Client() as client,
        pytest.raises(GenerationError, match="OPENAI_KEY_REQUIRED"),
    ):
        generate(settings, client)
    assert list(tmp_path.iterdir()) == []


def test_provider_error_is_explicit_and_leaves_no_manifest(tmp_path: Path) -> None:
    settings = Settings(
        database_password=SecretStr("unused"),
        openai_api_key=SecretStr("synthetic"),
        spoken_output=tmp_path,
    )
    transport = httpx.MockTransport(
        lambda request: httpx.Response(401, json={"error": "denied"})
    )
    with (
        httpx.Client(transport=transport) as client,
        pytest.raises(GenerationError, match="TTS_HTTP_401"),
    ):
        generate(settings, client)
    assert not (tmp_path / "manifest.json").exists()


def wav() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24000)
        output.writeframes(
            b"".join(
                struct.pack(
                    "<h", int(10000 * math.sin(2 * math.pi * 440 * sample / 24000))
                )
                for sample in range(7200)
            )
        )
    return buffer.getvalue()


def test_real_aac_conversion_resumes_and_verifies_all_clips(tmp_path: Path) -> None:
    settings = Settings(
        database_password=SecretStr("unused"),
        openai_api_key=SecretStr("synthetic"),
        spoken_output=tmp_path,
    )
    requests: list[httpx.Request] = []
    audio = wav()

    def speech(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url == "https://api.openai.com/v1/audio/speech"
        assert json.loads(request.content)["response_format"] == "wav"
        return httpx.Response(200, content=audio)

    with httpx.Client(transport=httpx.MockTransport(speech)) as client:
        generate(settings, client)
        count = len(requests)
        assert 0 < count < 66
        generate(settings, client)
        assert len(requests) == count
    assert len(list(tmp_path.rglob("*.m4a"))) == 66
    verify(settings)
    with pytest.raises(GenerationError):
        verify(settings.model_copy(update={"spoken_voice": "other"}))
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["version"] = 999
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(GenerationError):
        verify(settings)


@pytest.mark.parametrize(
    ("content", "code"),
    [(b"not audio", "TTS_INVALID_AUDIO"), (b"x" * 2048, "TTS_RESPONSE_TOO_LARGE")],
)
def test_invalid_or_oversized_provider_output(
    tmp_path: Path, content: bytes, code: str
) -> None:
    settings = Settings(
        database_password=SecretStr("unused"),
        openai_api_key=SecretStr("synthetic"),
        spoken_output=tmp_path,
        spoken_max_clip_bytes=1024,
    )
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=content)
        )
    ) as client:
        with pytest.raises(GenerationError, match=code):
            generate(settings, client)
    assert not list(tmp_path.rglob("*.m4a"))
    assert not (tmp_path / "manifest.json").exists()


def test_partial_generation_resumes_without_rebuying_completed_clips(
    tmp_path: Path,
) -> None:
    settings = Settings(
        database_password=SecretStr("unused"),
        openai_api_key=SecretStr("synthetic"),
        spoken_output=tmp_path,
    )
    audio = wav()
    calls = 0

    def interrupted(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=audio) if calls == 1 else httpx.Response(503)

    with httpx.Client(transport=httpx.MockTransport(interrupted)) as client:
        with pytest.raises(GenerationError, match="TTS_HTTP_503"):
            generate(settings, client)
    assert len(list(tmp_path.rglob("*.m4a"))) == 1
    assert not (tmp_path / "manifest.json").exists()

    def resumed(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["input"] != "C"
        return httpx.Response(200, content=audio)

    with httpx.Client(transport=httpx.MockTransport(resumed)) as client:
        generate(settings, client)
        with pytest.raises(GenerationError, match="SPOKEN_ASSET_CONFIGURATION_CHANGED"):
            generate(settings.model_copy(update={"spoken_voice": "other"}), client)
    verify(settings)
    (tmp_path / vocabulary()[0].path).write_bytes(b"corrupt")
    with pytest.raises(GenerationError):
        verify(settings)


def test_network_failure_does_not_expose_provider_diagnostics(tmp_path: Path) -> None:
    settings = Settings(
        database_password=SecretStr("unused"),
        openai_api_key=SecretStr("synthetic"),
        spoken_output=tmp_path,
    )

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("private-provider-diagnostic", request=request)

    with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(GenerationError) as failure:
            generate(settings, client)
    assert str(failure.value) == "TTS_NETWORK_ERROR"
