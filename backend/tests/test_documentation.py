import re
from pathlib import Path

from app.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


def test_environment_example_and_reference_cover_runtime_settings() -> None:
    example = set(
        re.findall(
            r"^([A-Z][A-Z0-9_]+)=", (ROOT / ".env.example").read_text(), re.MULTILINE
        )
    )
    reference = set(
        re.findall(
            r"`([A-Z][A-Z0-9_]+)`",
            (ROOT / "docs/developer/env-variables.md").read_text(),
        )
    )
    required = {
        field.validation_alias
        if isinstance(field.validation_alias, str)
        else "API_" + name.upper()
        for name, field in Settings.model_fields.items()
    }
    for path in (ROOT / "deploy").glob("compose*.yaml"):
        required.update(re.findall(r"\$\{([A-Z][A-Z0-9_]+)", path.read_text()))
    assert required <= example, sorted(required - example)
    assert example <= reference, sorted(example - reference)


def test_required_developer_guides_have_purpose_and_prerequisites() -> None:
    names = (
        "architecture",
        "data-model",
        "api",
        "env-variables",
        "deploy",
        "ci-cd",
        "omr-pipeline",
        "spoken-notes",
        "pwa-share",
        "adding-a-language",
        "troubleshooting",
        "glossary",
    )
    for name in names:
        path = ROOT / "docs/developer" / f"{name}.md"
        assert path.is_file(), str(path)
        content = path.read_text()
        assert "This document " in content, str(path)
        assert "Prerequisites:" in content, str(path)


def test_documentation_relative_links_exist() -> None:
    paths = [ROOT / "README.md", *(ROOT / "docs").rglob("*.md")]
    for path in paths:
        content = re.sub(r"```.*?```", "", path.read_text(), flags=re.DOTALL)
        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
            if "://" in link or link.startswith("#"):
                continue
            target = link.split("#", 1)[0]
            assert (path.parent / target).is_file(), f"{path}: {link}"


def test_user_and_developer_sentence_lengths() -> None:
    failures: list[str] = []
    for directory in ("docs/user", "docs/developer"):
        for path in (ROOT / directory).glob("*.md"):
            content = re.sub(r"```.*?```", "", path.read_text(), flags=re.DOTALL)
            content = re.sub(r"`[^`]+`", "CODE", content)
            content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)
            paragraphs: list[tuple[bool, str]] = []
            text: list[str] = []
            procedure = False
            for line in [*content.splitlines(), ""]:
                stripped = line.strip()
                item = re.match(r"^(?:\d+\.|[-*])\s+", stripped)
                if not stripped or stripped.startswith(("#", "|")) or item:
                    if text:
                        paragraphs.append((procedure, " ".join(text)))
                        text = []
                    procedure = bool(re.match(r"^\d+\.\s", stripped))
                if stripped and not stripped.startswith(("#", "|")):
                    text.append(re.sub(r"^(?:\d+\.|[-*])\s+", "", stripped))
            for procedure, paragraph in paragraphs:
                for index, sentence in enumerate(
                    re.split(r"[.!?](?:\s+|$)", paragraph)
                ):
                    words = re.findall(r"\b[\w-]+\b", sentence)
                    limit = 20 if procedure and index == 0 else 25
                    if len(words) > limit:
                        failures.append(
                            f"{path.relative_to(ROOT)}: {len(words)}/{limit}: "
                            f"{sentence}"
                        )
    assert not failures, "\n".join(failures)
