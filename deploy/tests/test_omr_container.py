import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def test_pinned_engine_recognizes_original_synthetic_scale_without_network() -> None:
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--memory",
            "1024m",
            "--memory-swap",
            "1024m",
            "--cpus",
            "1",
            "--pids-limit",
            "128",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--tmpfs",
            "/tmp:size=256m,mode=1777,exec",
            "--mount",
            f"type=bind,source={ROOT / 'backend/tests/fixtures/omr'},"
            "target=/fixtures,readonly",
            "--env",
            "DATABASE_PASSWORD=synthetic-unused-password",
            "solfeo-dev-backend",
            "python",
            "-c",
            "import sys; from pathlib import Path; from app.settings import Settings; "
            "from app.services.omr_engine import AudiverisEngine; "
            "sys.stdout.buffer.write(AudiverisEngine(Settings()).recognize(Path('/fixtures/scale.png')))",
        ],
        check=True,
        capture_output=True,
        timeout=330,
    )
    root = ET.fromstring(result.stdout)
    notes = root.findall("./part/measure/note")
    assert [note.findtext("pitch/step") for note in notes] == list("CDEFGABC")
    assert [note.findtext("pitch/octave") for note in notes] == ["4"] * 7 + ["5"]
    assert len(root.findall("./part/measure")) == 2
    divisions = int(root.findtext("./part/measure/attributes/divisions", "0"))
    assert divisions > 0
    assert all(int(note.findtext("duration", "0")) == divisions for note in notes)
