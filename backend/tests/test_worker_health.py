import os
import time
from pathlib import Path

from pydantic import SecretStr

from app.settings import Settings
from worker.omr import healthy


def test_omr_health_rejects_missing_and_stale_markers(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_password=SecretStr("unused-test-password"),
        omr_health_file=tmp_path / "ready",
    )
    assert not healthy(settings)
    settings.omr_health_file.touch()
    assert healthy(settings)
    stale = time.time() - settings.omr_health_seconds
    os.utime(settings.omr_health_file, (stale, stale))
    assert not healthy(settings)
